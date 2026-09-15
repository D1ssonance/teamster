# Protocol

## Preflight

1. Resolve the exact model ID from the current runtime registry or the user-provided exact ID.
2. Verify the adapter protocol and required runtime environment reference without revealing its value.
3. Check whether the model is explicitly excluded by project/user policy. Exclusion is not lifted by a successful probe.
4. Freeze a run manifest containing model IDs, case IDs, cap, timeout, retry policy, adapter name, and hashes. Do not include endpoints or secrets.

## Cases

Use stable cases that exercise ordinary chat and one structured-output sanity check only when the adapter supports it. Do not use hidden chain-of-thought requests, model judges, or generated-code execution. Expected answers must be deterministic and stored outside prompts.

## Retry and budget

Count every HTTP attempt, including retries. Retry at most once for timeout, network failure, and transient 5xx when budget remains. Do not locally retry 401/403, 404, 429, or 400 request incompatibility. If the budget or state file is corrupt, fail closed; never reset it automatically.

## Evidence

A useful smoke report includes:

- exact provider/model and adapter protocol;
- case count and attempt count;
- first-attempt passes and retry recoveries;
- latency distribution stated descriptively, not as a universal rank;
- separate error/unavailable/incompatible/empty/truncated counts;
- run timestamp and input hashes;
- explicit limitations and whether tools, vision, and native execution were not tested.

Never serialize auth headers, endpoint URLs, raw response bodies, prompt secrets, or raw exception text. Keep the run output private with restrictive permissions.

## Existing harnesses

For the configured providers, reuse `<EVALUATION_ROOT>` and its `runner.mjs` after reading `your runtime integration documentation`. For other adapters, use their native agent interface or a small local adapter harness with the same contract. Do not force an external model into the configured evaluation harness merely because its API is compatible.

## Adapter capability gate

These are workflow instructions, not a new universal API client. Model selection
in the agent does not imply a separately callable HTTP endpoint or exportable
credentials. Inspect the documented adapter API first. If direct API calls are
unavailable (for example an agent-only authenticated adapter), report API testing
as unsupported and offer native-agent testing as a distinct stage. Do not label
native latency as HTTP latency. Never extract login tokens or invent an endpoint.
Freeze the total campaign cap across all models; the default six attempts is per
model, and the total must be stated before dispatch. Disable hidden SDK retries
or account for every underlying attempt; otherwise do not claim an HTTP cap.
