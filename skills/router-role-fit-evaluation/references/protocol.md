# Evaluation Protocol

## Role matrix

Report each requested role as one of:

- `validated`: required stage passed with exact identity and observable checks;
- `partially_validated`: some required stages passed, with named gaps;
- `unvalidated`: no sufficient evidence;
- `unavailable`: adapter/model did not provide a usable route;
- `incompatible`: request or protocol rejected;
- `failed`: route worked but the role task failed.

Keep raw counts and receipts next to the interpretation. Do not collapse unavailable, incompatible, timeout, empty, and wrong-answer outcomes into one zero.

## Minimum role evidence

- `scout`: correct files/symbols/edges on a bounded fixture and no invented references.
- `requirements`: identifies material ambiguity, preserves constraints, and asks focused questions.
- `coder`/`heavy-coder`: production-path implementation passes targeted tests and required checks; generated code runs only in approved Docker when applicable.
- `test-writer`: tests exercise production behavior and detect the seeded defect.
- `debugger`: diagnosis matches the injected defect and observable trace/state.
- `fixer`: minimal fix passes correct and buggy/partial-fix fixtures without unrelated edits.
- `reviewer`: catches seeded defects and distinguishes severity; reviewer identity must be independent by policy.
- `corporate-architect`: options and trade-offs match supplied architecture evidence; no unsupported external claims.
- `vision`: actual image/diagram task, not a text-only proxy. Text probe may establish API route only.

## Sampling

Use deterministic synthetic fixtures and small bounded samples first. Repeat only when a result is ambiguous or a failure is plausibly transient. Never rerun completed model cases merely to improve a score. Preserve exact identity, attempts, retries, elapsed time, and failure category.

## Provider-neutral adapter

If the model is not in the configured providers, use the current agent's native provider adapter. Record adapter/protocol and whether the test exercised API, tools, native agent, or visual input. Do not assume an compatible endpoint has the same tool, vision, timeout, or error semantics.

## Acceptance

A role recommendation may be used as reference evidence only. To update a reference router, first compare role chains, exclusions, non-model settings, and loader roundtrip. To activate or modify production routing, stop and request explicit approval. For a session refresh, use the separate generate-only session-router command and its fail-closed all-role policy.

## Suggested report fields

`model`, `provider`, `adapter`, `roles`, `stage`, `case_id`, `attempts`, `status`, `error_category`, `latency_ms`, `identity_verified`, `fixture_hash`, `source_hash`, `recommendation`, `limitations`, `approval_required`.

## Native admission and privacy

For corporate repository tasks use `the native delegation API` with the semantic role;
its spawn API has no model override. Verify the documented evaluation admission
path before testing a specific identity. Never claim an exact-model test when
routing fallback changed the actual model. For external models use only public
or synthetic fixtures with the documented native admission interface and an
exact discovered selector. Never send confidential corporate repository bodies,
traces, or hidden corporate test data to an external provider. A requested
external model is not permission to transfer corporate data.

Freeze per-stage caps, concurrency, wall deadlines and identity checks before
admission. Save handles and receipts; finish a turn while independent work runs.
On interruption reconcile saved starts/results before admission, never replay a
completed case. A final child message is required; explicitly terminate writers
and verify roster absence before transferring write ownership. After repeated
handoff/implementation failure, root finishes narrow review/fixes directly where
privacy permits; do not create an endless chain of replacement workers.

Existing native fixtures under
`<EVALUATION_ROOT>/native-fixtures` cover only a subset
of roles and are historical baselines, not a universal runner. Verify fixture
and executor hashes and documented invocation before reuse. New architecture
or visual tasks need their own observable acceptance fixtures. Missing adapters
or fixtures are explicit blockers, not evidence that a model failed. These
skills do not install new dependencies or implement new provider integrations.
