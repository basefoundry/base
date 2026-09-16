# First-run troubleshooting

Use this page when the first `basectl` command does not produce the expected
result. Start with the symptom, collect only the requested non-secret evidence,
and follow the linked reference for the detailed contract.

## Decision tree

### The command is not available

1. Confirm that you are in a supported source checkout or have completed the
   [first-mile bootstrap](bootstrap.md).
2. From a source checkout, run the repository launcher:

   ```bash
   ./bin/basectl check
   ```

3. If you installed Base through Homebrew or another supported path, confirm
   that the launcher directory is on `PATH` and review the
   [installation validation guide](macos-install-validation.md).

If the command is found but reports an unsupported shell, Python, or operating
system, continue with the matching branch below. Do not work around a support
guard by substituting an untested interpreter or shell.

### Bootstrap or installer reports unsupported macOS

Base currently supports macOS 14 Sonoma or newer. `bootstrap.sh` and `install.sh`
check the macOS version before probing or changing Homebrew, Git, Bash, or Base
state. For `bootstrap.sh`, this includes `--ensure-bash` and `--dry-run`.
Confirm the detected version with:

```bash
/usr/bin/sw_vers -productVersion
```

Upgrade to macOS 14 or newer if the hardware supports it, then rerun the
installer. Older macOS versions may work from a manually prepared source
checkout, but they are outside Base's tested support contract and cannot use
either first-mile installer.

### `basectl check` reports an error

Run the read-only diagnostic command and preserve its finding IDs and suggested
fixes:

```bash
./bin/basectl doctor
```

Use [Doctor Finding IDs](doctor-findings.md) to interpret a `BASE-*` finding.
Follow the finding's documented fix, then rerun `check` and `doctor`. If the
finding concerns a project-owned command or dependency, record the project,
version, operating system, exact command, exit status, and redacted output
before asking for help.

### Setup is needed or setup failed

Preview the changes before allowing setup to apply them:

```bash
./bin/basectl setup --dry-run
```

Review the planned package, profile, and project actions. Then rerun the
appropriate setup command only after confirming that the changes are wanted.
Use [First-Mile Bootstrap](bootstrap.md), [Python Manifest](python-manifest.md),
or [Project Installers](project-installers.md) for the owning contract. If setup
fails, keep the error output and run `doctor`; do not repeatedly retry a
mutating command without checking the plan.

### Bash or Python is missing or unsupported

Use [Linux Support](linux-support.md) for Ubuntu/Debian prerequisites and
[Clean macOS Install Validation](macos-install-validation.md) for the macOS
source-checkout and Homebrew paths. The [Runtime Environment](runtime-environment.md)
page documents provider selection and the variables that Base derives or accepts.

Native Windows is not part of the current Base runtime support contract; see
[Native Windows Support](windows-support.md) for the staged future boundary.

### A provider cannot be resolved

Check the effective provider and source mode reported by `check` or `doctor`,
then compare the result with [Runtime Environment](runtime-environment.md) and
[Ecosystem Platform, License, and Release Policy](ecosystem-policy.md). Base's
development checkout may intentionally use an explicit or sibling provider;
that moving-source mode is not release evidence. For a release or downstream
compatibility question, use the immutable component references recorded by the
[release BOM](release-bom.md).

### Cache, path, or permission errors occur

Do not delete a cache or change ownership blindly. First record the failing
path, command, user, operating system, and redacted diagnostic. Review
[Cache Ownership and Layout](cache-ownership-and-layout.md) and the
[Runtime Environment](runtime-environment.md), including the documented
`BASE_CACHE_DIR` override. If a project path, symlink, or permission boundary
is involved, include a minimal reproduction that uses a temporary directory.

### The report may contain sensitive information

Never paste credentials, tokens, private paths, or unredacted logs into a public
issue or discussion. Use the private [security reporting path](../SECURITY.md)
for vulnerabilities or sensitive conduct concerns. For ordinary adoption or
compatibility help, use the public [support path](../SUPPORT.md) with redacted
commands and output.

## What to include when asking for help

Include:

- the Base version or full source-checkout commit;
- the operating system and shell versions;
- the exact read-only command and exit status;
- the `BASE-*` finding ID, if one was emitted; and
- a short, redacted output excerpt plus the next command you expected to run.

Do not include secrets or assume that a third-party project failure is a Base
defect until the project-owned command and dependency boundary has been checked.
