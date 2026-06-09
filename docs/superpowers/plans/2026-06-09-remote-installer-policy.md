# Remote Installer Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define and enforce Base's current remote installer trust policy for setup and prerequisite profiles.

**Architecture:** Keep first-mile Homebrew trust documented in docs and shell dry-run output, while enforcing AI profile installer policy in `cli/python/base_dev/engine.py`. AI installer commands will be derived from structured metadata and an allowlist instead of being stored as opaque shell strings.

**Tech Stack:** Bash setup/bootstrap scripts, Python `dataclasses`, existing `base_dev` profile layer, `unittest`, BATS, Markdown docs.

---

## File Structure

- Modify `cli/python/base_dev/engine.py`: add structured AI remote installer metadata, allowlist helpers, policy logging, and command derivation.
- Modify `cli/python/base_dev/tests/test_engine.py`: add failing tests for allowlist enforcement, dry-run policy output, non-interactive explicit opt-in, and default profile exclusion.
- Add `docs/remote-installer-policy.md`: canonical user-facing policy.
- Modify `docs/README.md`: add the policy page to the documentation map.
- Modify `README.md`: replace the inline trust-policy paragraphs with a concise pointer to the policy page.
- Modify `docs/bootstrap.md`: link contributor setup and first-mile notes to the policy.
- Add `docs/superpowers/specs/2026-06-09-remote-installer-policy-design.md`: design record.
- Add `docs/superpowers/plans/2026-06-09-remote-installer-policy.md`: this implementation plan.

## Task 1: Failing AI Policy Tests

**Files:**
- Modify: `cli/python/base_dev/tests/test_engine.py`

- [ ] **Step 1: Add a test for central AI installer policy metadata**

Add to `DevManifestTests`:

```python
    def test_ai_remote_installer_urls_are_allowlisted(self) -> None:
        self.assertEqual(
            engine.ai_remote_installer_urls(),
            (
                "https://chatgpt.com/codex/install.sh",
                "https://claude.ai/install.sh",
            ),
        )
        self.assertEqual(
            [engine.ai_tool_installer_command(tool) for tool in engine.AI_TOOLS],
            [
                ("sh", "-c", "curl -fsSL https://chatgpt.com/codex/install.sh | sh"),
                ("sh", "-c", "curl -fsSL https://claude.ai/install.sh | bash"),
            ],
        )
```

- [ ] **Step 2: Add dry-run policy output and default-profile exclusion tests**

Update `test_setup_profile_ai_dry_run_prints_official_installers` so it also
asserts policy context:

```python
        self.assertIn(
            "Remote installer policy: Codex CLI uses allowlisted installer "
            "https://chatgpt.com/codex/install.sh; execution requires explicit --profile ai.",
            stderr,
        )
        self.assertIn(
            "Remote installer policy: Claude Code uses allowlisted installer "
            "https://claude.ai/install.sh; execution requires explicit --profile ai.",
            stderr,
        )
```

Add:

```python
    @unittest.skipUnless(importlib.util.find_spec("click"), "Click is not installed")
    def test_setup_default_dry_run_does_not_include_ai_remote_installers(self) -> None:
        status, _stdout, stderr = run_engine(["setup", "--dry-run"])

        self.assertEqual(status, 0)
        self.assertNotIn("chatgpt.com/codex/install.sh", stderr)
        self.assertNotIn("claude.ai/install.sh", stderr)
```

- [ ] **Step 3: Add allowlist rejection and non-interactive explicit opt-in tests**

Add:

```python
    def test_setup_ai_tools_rejects_unallowlisted_remote_installer(self) -> None:
        tool = engine.AITool(
            name="bad-ai",
            display_name="Bad AI",
            version_args=("--version",),
            installer_url="https://example.invalid/install.sh",
            installer_shell="sh",
        )
        ctx = mock.Mock()

        with (
            mock.patch("base_dev.engine.AI_TOOLS", (tool,)),
            mock.patch("base_dev.engine.check_ai_tool", return_value=engine.DevCheck("bad-ai", False, "missing", "")),
            mock.patch("base_dev.engine.run_command") as run_command,
        ):
            status = engine.setup_ai_tools(ctx, dry_run=False)

        self.assertEqual(status, 1)
        self.assertIn("Remote installer URL is not allowlisted", ctx.log.error.call_args.args[0])
        run_command.assert_not_called()

    def test_setup_ai_tools_noninteractive_explicit_profile_runs_allowlisted_installers(self) -> None:
        ctx = mock.Mock()

        with (
            mock.patch.dict(os.environ, {"CI": "true"}),
            mock.patch("base_dev.engine.check_ai_tool", return_value=engine.DevCheck("tool", False, "missing", "")),
            mock.patch("base_dev.engine.run_command") as run_command,
        ):
            status = engine.setup_ai_tools(ctx, dry_run=False)

        self.assertEqual(status, 0)
        self.assertEqual(
            [call.args[1] for call in run_command.call_args_list],
            [
                ["sh", "-c", "curl -fsSL https://chatgpt.com/codex/install.sh | sh"],
                ["sh", "-c", "curl -fsSL https://claude.ai/install.sh | bash"],
            ],
        )
```

- [ ] **Step 4: Run focused tests and verify RED**

Run:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_dev/tests/test_engine.py
```

Expected: FAIL because `AITool` has no `installer_url`, `ai_remote_installer_urls()`
does not exist, and dry-run policy context is not emitted.

## Task 2: AI Remote Installer Policy Implementation

**Files:**
- Modify: `cli/python/base_dev/engine.py`

- [ ] **Step 1: Replace opaque AI installer commands with structured metadata**

Change `AITool` to:

```python
@dataclass(frozen=True)
class AITool:
    name: str
    display_name: str
    version_args: tuple[str, ...]
    installer_url: str
    installer_shell: str
```

Update `AI_TOOLS` so Codex uses `installer_url="https://chatgpt.com/codex/install.sh"` and
`installer_shell="sh"`, and Claude uses `installer_url="https://claude.ai/install.sh"` and
`installer_shell="bash"`.

- [ ] **Step 2: Add allowlist and command helpers**

Add:

```python
AI_REMOTE_INSTALLER_ALLOWLIST = tuple(tool.installer_url for tool in AI_TOOLS)


def ai_remote_installer_urls() -> tuple[str, ...]:
    return AI_REMOTE_INSTALLER_ALLOWLIST


def validate_ai_remote_installer(tool: AITool) -> None:
    if tool.installer_url not in AI_REMOTE_INSTALLER_ALLOWLIST:
        raise ArtifactError(
            "Remote installer URL is not allowlisted for Base 'ai' profile: "
            f"{tool.installer_url}"
        )


def ai_tool_installer_command(tool: AITool) -> tuple[str, ...]:
    validate_ai_remote_installer(tool)
    return ("sh", "-c", f"curl -fsSL {tool.installer_url} | {tool.installer_shell}")
```

- [ ] **Step 3: Log policy context before installer execution**

Add:

```python
def log_ai_remote_installer_policy(ctx: base_cli.Context, tool: AITool) -> None:
    ctx.log.info(
        "Remote installer policy: %s uses allowlisted installer %s; execution requires explicit --profile ai.",
        tool.display_name,
        tool.installer_url,
    )
```

Update `setup_ai_tools()` so it computes `installer_command = ai_tool_installer_command(tool)`,
logs policy context, and then calls `dry_run_command()` or `run_command()` with
`list(installer_command)`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_dev/tests/test_engine.py
```

Expected: all tests in the file pass.

## Task 3: Remote Installer Policy Documentation

**Files:**
- Add: `docs/remote-installer-policy.md`
- Modify: `docs/README.md`
- Modify: `README.md`
- Modify: `docs/bootstrap.md`

- [ ] **Step 1: Add the canonical policy page**

Create `docs/remote-installer-policy.md` with:

```markdown
# Remote Installer Policy

Base may run remote shell installers only when they are defined by Base itself,
documented here, and reached through the setup surface that owns that trust
decision.

## Allowed Remote Installers

| Installer | URL | Where Base may use it | Opt-in |
| --- | --- | --- | --- |
| Homebrew | `https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh` | `bootstrap.sh`, `install.sh`, and `basectl setup` when Homebrew is missing on macOS | First-mile setup path; `bootstrap.sh --no-homebrew-install` can refuse this path |
| Codex CLI | `https://chatgpt.com/codex/install.sh` | `basectl setup --profile ai` | Explicit `--profile ai` |
| Claude Code | `https://claude.ai/install.sh` | `basectl setup --profile ai` | Explicit `--profile ai` |

Project manifests cannot declare arbitrary remote shell installers.

## Dry-Run And Non-Interactive Behavior

`--dry-run` prints planned remote installer commands without downloading or
executing installer content.

The `ai` profile does not prompt separately after `--profile ai` is selected.
That explicit profile flag is the opt-in boundary, so scripted and
non-interactive setup stays deterministic.

## Managed Workstations And Pinned Installers

Base intentionally follows Homebrew's official mutable installer entry point
instead of pinning a reviewed commit. Teams that require pinned, mirrored, or
managed installer content should install Homebrew and optional AI tools through
their workstation management system before running Base.

Base does not yet provide a manifest field for pinned remote installers.

## Logging And Redaction

AI profile installers run through Base's Python command runner, which preserves
live output and writes redacted stdout/stderr tails to persistent logs and
failure summaries.

Homebrew first-mile installers run before the Python setup layer may exist.
Their output is shown live by the shell installer path and is not rewritten by
Base.
```

- [ ] **Step 2: Link the policy from docs map, README, and bootstrap docs**

In `docs/README.md`, add Remote Installer Policy to Feature And Boundary
Documents.

In `README.md`, replace the inline AI/Homebrew trust paragraphs with a short
summary and link to `docs/remote-installer-policy.md`.

In `docs/bootstrap.md`, link the AI profile and first-mile Homebrew discussion
to `remote-installer-policy.md`.

- [ ] **Step 3: Run documentation whitespace check**

Run:

```bash
git diff --check
```

Expected: no output.

## Task 4: Full Validation And Commit

**Files:**
- All changed files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
PYTHONPATH=lib/python:cli/python /Users/rameshhp/.base.d/base/.venv/bin/python -m unittest cli/python/base_dev/tests/test_engine.py
```

Expected: OK.

- [ ] **Step 2: Run full Base validation**

Run:

```bash
env -u BASE_HOME ./bin/base-test
```

Expected: Python tests pass, BATS tests pass.

- [ ] **Step 3: Run final diff check**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Commit implementation**

Run:

```bash
git add cli/python/base_dev/engine.py cli/python/base_dev/tests/test_engine.py docs/remote-installer-policy.md docs/README.md README.md docs/bootstrap.md
git commit -m "Define remote installer setup policy"
```

Expected: commit succeeds.
