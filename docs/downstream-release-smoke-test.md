# Downstream release smoke test

This is the smallest consumer-side check to run before updating a downstream
Base pin. It verifies the immutable release identity, the tagged installer, its
checksum, and one read-only Base command. It complements the full
[release process](release-process.md), the hosted release gates, and the
[release BOM policy](release-bom.md); it does not replace any of them.

The example below uses the public Base `v1.9.0` release. For a later release,
replace both expected values with the full commit and reviewed `install.sh`
SHA-256 recorded for that release.

## Verify the release identity

Use a full commit, never a moving branch or a short SHA:

```bash
release_tag=v1.9.0
expected_commit=ac8d294421e1bfc14afa8c6a2a12f1affb5268ee
expected_install_sha256=f0522bf20b13e2f487767324f4688f1b1ed33b1c1bc1158a404f0e428ea3e993
release_repo=https://github.com/basefoundry/base.git
release_root="$(mktemp -d)"
trap 'rm -rf "$release_root"' EXIT

test "$(git ls-remote "$release_repo" "refs/tags/${release_tag}^{}" | awk '{print $1}')" = "$expected_commit"
```

The peeled tag check prevents a downstream pin from silently following a tag
object that resolves to a different commit.

## Verify the installer before using it

Retrieve the versioned installer and compare its bytes with the reviewed
checksum. This example only syntax-checks the installer; it does not execute
it:

```bash
curl -fsSL "https://raw.githubusercontent.com/basefoundry/base/${release_tag}/install.sh" \
  -o "$release_root/install.sh"
test "$(shasum -a 256 "$release_root/install.sh" | awk '{print $1}')" = "$expected_install_sha256"
bash -n "$release_root/install.sh"
```

If the checksum does not match, stop. Do not replace the expected value from a
moving branch or rerun the installer until the release owner has recorded the
correct reviewed digest.

## Run one read-only command from the exact release

Use the exact release commit for the consumer smoke test. A source checkout
needs the normal supported prerequisites; the command below does not install
anything or alter the checkout:

```bash
git clone --quiet "$release_repo" "$release_root/base"
git -C "$release_root/base" checkout --quiet --detach "$expected_commit"
env -u BASE_HOME -u BASE_PROJECT \
  "$release_root/base/bin/basectl" check --format json > "$release_root/check.json"
jq -e '.status == "ok" or .status == "warn" or .status == "error"' \
  "$release_root/check.json" >/dev/null
```

The JSON status is the command's readiness result; preserve the complete
document and exit status in the downstream validation record. A prerequisite
or environment error is an actionable failure to escalate, not a reason to
switch to `main` or weaken the immutable pin.

## Escalate identity mismatches

Stop and record which identity disagreed: tag-to-commit, installer checksum,
version, command readiness, or release-BOM asset. Include the release tag, full
commit, operating system, command, exit status, and redacted output. Link the
record to the release issue or open a support request. Never publish secrets or
private paths in a public issue; use [SECURITY.md](../SECURITY.md) for a
security-sensitive report.
