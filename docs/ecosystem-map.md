# Base Foundry Ecosystem Map

Base Foundry is a small family of independent open-source repositories. Each
repository owns a distinct contract; the family is coordinated through release,
documentation, and contribution links rather than a monorepo.

## Which project should I start with?

| If you want to... | Start here | What you should expect |
| --- | --- | --- |
| Make setup, readiness, trust, onboarding, and handoff explicit across one or more repositories | [Base](https://github.com/basefoundry/base) | The primary workspace operating contract and GitHub workflow helpers |
| Build a production Python CLI with Click or Typer | [base-cli](https://github.com/basefoundry/base-cli) | An independently released Python lifecycle framework |
| Build reliable Bash automation | [base-bash-libs](https://github.com/basefoundry/base-bash-libs) | Independently released, sourceable Bash libraries and launcher support |
| See Base in a compact working consumer | [base-demo](https://github.com/basefoundry/base-demo) | A reference consumer and reproducible workflow fixture, not independent adoption evidence |
| See base-cli in an offline consumer | [base-cli-demo](https://github.com/basefoundry/base-cli-demo) | A reference Python application for the framework |
| See base-bash-libs in an offline consumer | [base-bash-libs-demo](https://github.com/basefoundry/base-bash-libs-demo) | A reference support-bundle collector |
| Install Base through Homebrew | [homebrew-base](https://github.com/basefoundry/homebrew-base) | The packaging tap; its formula follows the Base release and license policy |
| Add optional platform or operations utilities | [base-platform-tools](https://github.com/basefoundry/base-platform-tools) | Supporting utilities that Base can expose, but does not require |
| Inspect an example multi-repository manifest | [base-workspace](https://github.com/basefoundry/base-workspace) | An example workspace description, not a second Base implementation |

The organization [profile](https://github.com/basefoundry) is the public
orientation layer. This page is the canonical product and support map; release
versions and compatibility claims remain owned by the relevant repository and
the [ecosystem release policy](ecosystem-policy.md).

## How the pieces fit

```text
Base (workspace operating contract)
├── base-cli             Python CLI foundation
├── base-bash-libs       Bash automation foundation
├── reference consumers  base-demo, base-cli-demo, base-bash-libs-demo
└── supporting projects  homebrew-base, base-platform-tools, base-workspace
```

Base consumes the reusable libraries and coordinates a tested release
combination. The libraries remain usable outside Base. The demos exercise
released APIs and document consumer setup, but a first-party demo is not proof
of independent adoption. The Homebrew tap packages published Base artifacts;
it is not the source repository for Base behavior.

## Personas, use cases, and non-goals

Base is for developers, platform engineers, SREs, and maintainers who need an
inspectable local operating contract in one repository or across independent
peer repositories. The strongest use cases are repeatable setup and readiness,
explicit command trust, repository/workspace onboarding, and evidence-rich
handoff.

Base is deliberately not a monorepo, general package manager, language-version
manager, dotfile manager, generic task runner, or hosted agent runtime. Choose
the companion library when the Python or Bash lifecycle is the problem by
itself. Choose an environment or task tool such as mise, direnv, Dev Containers,
or Nix when convergence or hermeticity is the primary requirement.

## Support matrix

The matrix distinguishes shipped runtime support from CI coverage, reference
behavior, and future work:

| Environment or surface | Base shipped support | CI or evidence | Boundary |
| --- | --- | --- | --- |
| macOS 14+ | Full coordinated Base runtime, setup, shell integration, diagnostics, and project workflow | macOS 14 hosted smoke path and release BOM | Older macOS versions are outside the tested floor |
| Ubuntu/Debian | Runtime checks, diagnostics, source-checkout validation, and apt-backed setup | Ubuntu 24.04 source-checkout path and release BOM | Interactive macOS-style setup and demo parity are not implied |
| Ubuntu/Debian under WSL2 | Linux development/read-only guidance | Linux behavior may be exercised in a user environment | This is not native Windows support or a coordinated WSL2 release tier |
| Native Windows | Not shipped; Phase 1 is planned for the v1.11.0 Windows milestone | Phase 0 contract workflow only; no native launcher claim | Git Bash and WSL2 are not substitutes for the native contract |
| base-cli alone | Its own documented Python framework support, including its separate Windows boundary | Its repository's tests and releases | Component support does not expand Base support |
| base-bash-libs alone | Bash 4.2+ on its documented Unix-like environments | Its repository's tests and releases | A Bash library is not a native Windows runtime |
| Reference consumers | Reference-only behavior for the documented consumer path | Their own CI and release evidence | They do not constitute independent-adoption evidence |

Read the [Native Windows Support Contract](windows-support.md) for the staged
PowerShell-first boundary and current deferrals. Do not copy a component's
support statement into Base's matrix without checking the coordinated release
evidence.

## Compatibility and release truth

Base's current published release is v1.9.0. Companion repositories publish on
their own schedules. A coordinated Base release records exact component tags,
full commits, platform evidence, and BOM results; a moving sibling checkout is
useful development input but is not release evidence. Homebrew promotes a
published Base tag after the Base release exists and must keep its version,
checksum, and license metadata aligned with that release.

When a release or support claim changes, update this map, the affected README,
the organization profile, and the focused validation in the same reviewed
change. Link to the canonical page instead of copying a version number into
several unrelated documents.
