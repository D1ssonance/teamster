# Production safety

## Separation

Keep three layers separate:

1. immutable reference router;
2. generated session router;
3. production router and shared state.

Availability refresh writes only a new private session artifact and a redacted report. It never replaces production files automatically.

## Fail-closed rules

- every role must be explicit and non-empty;
- missing any role coverage means no loadable session router;
- corrupt cache/state means no silent reset;
- cache budget is not admission quota;
- cooldown is never bypassed by force;
- provider exclusions are absolute;
- cache/output paths must not collide with protected files or artifact directories;
- final router is published only after report and cache writes succeed.

## Delegation

Use semantic roles, not guessed model names. One writer owns a workspace at a time. Read-only review has an empty write scope. Pass small evidence packages, not confidential source dumps. Terminate the writer through the native lifecycle and verify roster absence before handing off writes.

## Activation gate

Before activation, require loader roundtrip, complete role coverage, settings equality, exclusion scan, privacy scan, source fingerprints, independent review and explicit approval. Manual reviewer-family independence remains a workflow check; static chains do not enforce it.

Known limitation: a non-locking path preflight cannot completely eliminate a symlink TOCTOU race. Document the residual risk or use an OS-level trusted sandbox for higher assurance.
