"""Review a branch using Git objects, without importing code from the branch."""
import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

MIB = 1024 * 1024
ATTRIBUTION = re.compile(
    r"^\s*(?:[-*>]\s*)?(?:co-authored-by\s*:|generated (?:by|with)|written (?:by|with))"
    r"[^\n]*(?:\bAI\b|\bClaude\b|\bCodex\b|ChatGPT|Copilot|Anthropic|OpenAI|Gemini)",
    re.IGNORECASE | re.MULTILINE,
)
EQUILIBRIUM = re.compile(r"^(?:wout[_.]|boozmn[_.]|(?:equilibrium|equilibria)[_.].*\.(?:nc|h5)|.*\.(?:geqdsk|eqdsk)$)", re.I)
ARCHIVE = ('.zip', '.gz', '.xz', '.tgz', '.tar', '.bz2', '.7z', '.zst', '.rar')


def git(*args):
    return subprocess.check_output(['git', *args])


def delta(start, end):
    raw = git('diff', '--raw', '--no-abbrev', '--no-renames', '-z',
              '--diff-filter=AMT', start, end, '--').split(b'\0')
    for header, path in zip(raw[::2], raw[1::2]):
        _, mode, _, blob, _ = header.split()
        if mode != b'160000':
            yield path.decode('utf-8', 'surrogateescape'), blob.decode(), mode


def inspect_file(name, blob, mode, history):
    path = PurePosixPath(name)
    size = int(git('cat-file', '-s', blob))
    if EQUILIBRIUM.match(path.name) or any(p.lower() in ('equilibria', 'equilibrium-files') for p in path.parts):
        return 'FAIL', 'equilibrium file belongs on the originating machine'
    if size > 5 * MIB:
        return 'FAIL', f'{size:,} bytes exceeds the 5 MiB pilot limit'
    data = git('cat-file', 'blob', blob)
    if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
        return 'FAIL', 'LFS payload requires owner classification'
    if path.name.lower().endswith(ARCHIVE) or data.startswith((b'PK\x03\x04', b'\x1f\x8b', b'\xfd7zXZ\x00', b'BZh')):
        return 'FAIL', 'archive requires owner classification'
    if re.search(rb'(?im)^\s*&indata\b', data):
        return 'FAIL', 'VMEC equilibrium input deck'
    if history:
        return None
    if path.suffix.lower() == '.ipynb' or any(p in ('outputs','simulation_outputs') for p in path.parts[:-1]):
        return 'FAIL', 'keep simulation outputs and notebooks outside the source tree'
    if mode.startswith(b'100') and path.parts[0] == 'examples' and path.suffix == '.py':
        try:
            nodes = list(ast.walk(ast.parse(data)))
        except (ValueError, SyntaxError) as exc:
            return 'FAIL', f'cannot parse example ({exc.msg if isinstance(exc, SyntaxError) else "invalid input"})'
        if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'main' for n in nodes):
            return 'FAIL', 'use a flat pedagogical example'
        aliases = {'ArgumentParser'} | {a.asname for n in nodes if isinstance(n, ast.ImportFrom)
                                        and n.module == 'argparse' for a in n.names if a.name == 'ArgumentParser'}
        if any(isinstance(n, ast.Call) and (getattr(n.func, 'id', '') in aliases or
                                           getattr(n.func, 'attr', '') == 'ArgumentParser') for n in nodes):
            return 'FAIL', 'keep argument parsing in the CLI'
    if size > MIB or path.suffix.lower() in ('.csv','.json'):
        return 'REVIEW', f'check purpose and provenance ({size:,} bytes)'
    return None


def review(base_ref, head_ref, event=None):
    base, head = [git('rev-parse', '--verify', '--end-of-options', r+'^{commit}').decode().strip()
                  for r in (base_ref, head_ref)]
    start = git('merge-base', base, head).decode().strip()
    findings = set()
    def record(result, label):
        if result:
            severity, reason = result
            findings.add((severity, label, reason))
    if event is not None:
        pr = event['pull_request']
        if pr['user']['type'] != 'User':
            record(('FAIL','a human contributor opens the PR'), 'PR author')
        if ATTRIBUTION.search(pr.get('body') or ''):
            record(('FAIL','remove tool attribution footer'), 'PR description')
    final = set(delta(start, head))
    for name, blob, mode in final:
        record(inspect_file(name, blob, mode, False), name)
    seen = set(final)
    for commit in git('rev-list', head, '^'+base).decode().splitlines():
        message = git('show', '-s', '--format=%B', commit).decode(errors='replace')
        if ATTRIBUTION.search(message):
            record(('FAIL','tool attribution trailer'), commit[:12])
        parents = git('show', '-s', '--format=%P', commit).decode().split()
        parent = parents[0] if parents else git('hash-object','-w','-t','tree','/dev/null').decode().strip()
        for item in delta(parent, commit):
            if item in seen:
                continue
            name, blob, mode = item
            # A merge from the target can bring in an existing target file.
            if len(parents) > 1 and any(git('ls-tree', p, '--', ':(literal)'+name).split(b'\t',1)[0].endswith(blob.encode()) for p in parents[1:]):
                continue
            seen.add(item)
            record(inspect_file(name, blob, mode, True), name)
    stats = git('diff','--numstat','-z','--no-renames',start,head,'--').split(b'\0')[:-1]
    additions = sum(int(x.split(b'\t',1)[0]) for x in stats if not x.startswith(b'-\t'))
    if len(stats) > 15 or additions > 400:
        record(('REVIEW',f'{len(stats)} paths, {additions} added lines'), 'PR size')
    return sorted(findings)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base')
    parser.add_argument('head')
    parser.add_argument('--event', type=Path)
    args = parser.parse_args()
    findings = review(args.base, args.head, json.loads(args.event.read_text()) if args.event else None)
    for severity, label, reason in findings:
        print(f'{severity} {ascii(label)}: {reason}')
    print(f'{sum(s == "FAIL" for s, _, _ in findings)} policy failures')
    sys.exit(any(s == 'FAIL' for s, _, _ in findings))
