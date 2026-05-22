# `caff`

Caffeinate a named process by finding its PID and running macOS `caffeinate`
against that process.

Public invocation is exposed by the launcher at `bin/caff`; the implementation
lives here so command code, documentation, and future tests stay together.
