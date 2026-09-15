# Optional navigation and feedback pilots

Use a scoped, local, read-only code graph first for broad navigation when available.
Confirm candidates in source; fall back for dynamic/generated/unsupported code.
Use only tracked files in explicit read scopes. Do not widen narrow scope, enable
remote indexing, or send raw source/graph output outside the trusted environment.

For Go tasks, a pinned compiler-aware language tool can confirm symbols, references,
implementations and diagnostics. Use no write/daemon/remote modes and disable
implicit dependency downloads. Missing dependencies or incomplete views require
scoped search fallback, not silent trust/network changes.

Affected tests accelerate feedback; include intended new files explicitly because
tracked-only discovery misses them. Final acceptance still uses the repository's
exact native commands. A feedback compressor can be enabled only for intermediate
noisy Go tests for coder, test-writer and fixer roles, not heavy-coder, review or
root checks. Never rewrite final verification, lint, source inspection or Git writes.
Keep raw logs/receipts; incomplete compressed evidence cannot establish acceptance.
No outbound telemetry. These are optional policies, not bundled tool integrations.

Evaluate orchestration improvements after three substantive completed tasks, not
three agents or cases. Track elapsed time, correction rounds, user interventions
and root effort when available. Do not optimize model selection using token cost.
