# Doctor Finding IDs

`basectl doctor` emits stable finding identifiers in both text and JSON output.
Automation, runbooks, and suppression policies should match on `id` instead of
human-readable messages. Findings that intentionally emit multiple instances
of the same rule should match on the tuple of `id` and `name`.

Finding IDs are never reused after they ship. A finding may change its message,
fix text, or severity over time, but its ID keeps the same meaning.
Every doctor finding implementation must provide an explicit ID; placeholder
IDs such as `BASE-P000` are invalid because they cannot support automation or
suppression policies.

## Principles

Doctor findings should be specific, actionable, and non-alarming. Text output
is for humans who need a safe next step; JSON output is for automation that
needs stable IDs, statuses, names, messages, and fix guidance.

`basectl doctor` should not mutate local state. A future fix path must be
explicit, reviewable, and paired with dry-run behavior before Base offers it as
part of the doctor workflow.

## Namespaces

| Prefix | Scope |
| --- | --- |
| `BASE-D` | Base runtime and developer-prerequisite findings |
| `BASE-P` | Project manifest, artifact, IDE, and command-delegation findings |
| `BASE-H` | Project health declaration findings |

## Base Runtime Findings

| ID | Finding |
| --- | --- |
| `BASE-D001` | Homebrew availability and PATH refresh |
| `BASE-D002` | Xcode Command Line Tools availability |
| `BASE-D003` | Homebrew Python formula availability |
| `BASE-D004` | Base virtual environment integrity |
| `BASE-D005` | Base `PyYAML` package availability |
| `BASE-D006` | Base `click` package availability |
| `BASE-D101` | Unsupported prerequisite profile manager |
| `BASE-D102` | Unsupported prerequisite profile version |
| `BASE-D103` | Homebrew unavailable for prerequisite profile checks |
| `BASE-D104` | Prerequisite profile Homebrew package status |
| `BASE-D105` | GitHub CLI availability |
| `BASE-D106` | GitHub CLI authentication status |

## Project Findings

| ID | Finding |
| --- | --- |
| `BASE-P001` | Empty project manifest artifact set |
| `BASE-P002` | Project manifest validity |
| `BASE-P010` | Brewfile path validity |
| `BASE-P011` | Homebrew unavailable for Brewfile checks |
| `BASE-P012` | Brewfile dependency status |
| `BASE-P020` | mise config path validity |
| `BASE-P021` | mise CLI availability |
| `BASE-P022` | mise tool verification status |
| `BASE-P030` | Unsupported artifact manager |
| `BASE-P031` | Unsupported Homebrew artifact version |
| `BASE-P032` | Homebrew unavailable for artifact checks |
| `BASE-P033` | Homebrew artifact package status |
| `BASE-P040` | Python package artifact status in the project virtual environment |
| `BASE-P050` | Project virtual environment integrity |
| `BASE-P060` | Project demo declaration |
| `BASE-P061` | Project demo script path and executable status |
| `BASE-P100` | User config disables all IDE setup and checks |
| `BASE-P101` | User config disables setup and checks for one IDE |
| `BASE-P102` | User IDE setting conflicts with a project manifest setting |
| `BASE-P110` | IDE CLI unavailable for extension checks |
| `BASE-P111` | IDE extension listing failure |
| `BASE-P112` | IDE extension install status |
| `BASE-P120` | IDE settings file validity |
| `BASE-P121` | IDE setting presence |
| `BASE-P122` | IDE setting expected-value match |
| `BASE-P123` | IDE setting value differs from the Base manifest |
| `BASE-P130` | Homebrew unavailable for IDE app checks |
| `BASE-P131` | IDE app install status |
| `BASE-P132` | IDE CLI PATH status |

## Health Findings

| ID | Finding |
| --- | --- |
| `BASE-H001` | Required environment variable presence; each variable is keyed by `(id, name)`. |
| `BASE-H002` | Required TCP port listening/free state |
