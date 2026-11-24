# UWPlasma development standards

Start with the [contribution handbook](skills/uwplasma-development/SKILL.md). It covers work on any UWPlasma code, from investigating a failing test to proposing a new solver. The [scientific evidence guide](skills/uwplasma-development/references/science.md) covers literature, independent codes, profiling and derivatives. The [interface and CI guide](skills/uwplasma-development/references/interfaces-and-ci.md) covers examples, Python and TOML inputs, packaging and coverage.

Human contributors open PRs from their own accounts. Prepare a topic branch and hand its comparison link to the contributor. The owner reviews the evidence and merges. Use the [PR template](.github/pull_request_template.md) when preparing the description. A template in this repository is automatically offered here. Contributors in other repositories can copy the same three prompts.

## Using the skill

Install the complete [uwplasma-development directory](skills/uwplasma-development) from a reviewed revision. The same Markdown serves humans and tools. Codex can read it from `~/.agents/skills/`, Claude Code from `~/.claude/skills/`, and Gemini CLI supports `gemini skills install ./skills/uwplasma-development` from this checkout. In clients without skill installation, open the handbook and its references directly. A code repository needs only a README link to the approved revision. Keep repository-specific instructions close to the code they describe.

## DKX pilot

DKX is the first pilot. A job in its existing CI calls the central action pinned to a full commit SHA. The action reads Git objects and PR metadata on hosted Linux with read-only access. It does not run the submitted Python files. Run the same checks locally before pushing, since opening a PR already uploads its contents.

| Finding | Pilot result |
|---|---|
| Bot opens the PR, model attribution footer, recognized equilibrium file or VMEC input deck, newly introduced notebook or simulation-output path | Fail |
| New archive or LFS pointer whose contents cannot be inspected, or blob over 5 MiB | Fail and report the path for owner review |
| A standalone Python example defines a main wrapper or constructs an argument parser | Fail |
| More than 400 added lines, more than 15 affected files, blob over 1 MiB, or a changed CSV/JSON needing provenance | Report for review |

The size limits are pilot values. An owner can propose a narrow change here by PR. The checker cannot identify arbitrary renamed scientific data, establish that a contributor read a paper, or verify a physical result. Human reviewers classify unfamiliar binaries and fixtures, inspect license and credit, and judge whether the comparison supports the claim. PR descriptions should state the baseline, candidate result and limits. The action checks the description supplied with its triggering event. A text-only edit in DKX requires fresh verification of the description before merge.

Existing scientific CI owns accuracy, performance, derivative and coverage gates. Report actual coverage against the 95% standard and retain any stricter threshold. An unmet threshold remains visible. Changing prose cannot turn an unmeasured quantity into a passing result.

For local review, run `python3 check.py BASE HEAD` in a checkout containing both revisions, supplying the path to this repository's script if necessary. The command reports structural findings and inspects introduced commits. The Actions job additionally checks the PR opener and description. Run the regression cases from this repository with `python3 -m unittest discover -s tests`.

**Promotion.** Merge the standards PR first. Review the DKX caller and its policy pin, observe the check on a real DKX PR, then add **UWPlasma policy** to the existing required checks. Preserve DKX's current scientific checks, independent approval and restricted main updates. The pilot owner verifies the approving human owns the affected code. If enforceable path ownership is needed, use a repository CODEOWNERS file with named human owners and require their review. Designate a second owner for changes authored by the first. A contributor cannot independently approve their own PR. No other code is enrolled during this pilot.
