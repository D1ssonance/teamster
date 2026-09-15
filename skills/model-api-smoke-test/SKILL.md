---
name: model-api-smoke-test
description: Runs a fast, bounded API smoke test against any model reachable through the current agent adapter or an compatible gateway. Use when checking a newly added provider/model, verifying basic chat availability, comparing a small set of models, or deciding whether to start a deeper router-role evaluation.
---

# Model API Smoke Test

Use this skill for a cheap route-availability and basic response check. It is provider-neutral. The model may be corporate, local, hosted, or another provider exposed by the current agent runtime.

Read [references/protocol.md](references/protocol.md) before running a live request.

## Contract

- Ask for or infer exact provider/model identifiers from the agent registry. Never guess aliases.
- Use the agent's existing adapter and credentials. Never print, persist, or send API keys, bearer headers, endpoint URLs, raw exceptions, or full responses to reports.
- Require explicit user approval before live inference unless the user has already authorized this exact bounded run.
- Use a hard request cap, serial requests by default, one bounded transient retry at most, and no local retry for 401/403/404/429 or request incompatibility.
- Keep API availability separate from tool support, vision support, role quality, and native-agent suitability.
- Store only redacted artifacts in a uniquely named run directory. Never modify production router/config/state or automatically promote a model.

## Default run

Use 1-3 deterministic cases, temperature 0 when supported, a short timeout, and a cap no larger than 6 attempts unless the user sets a different approved bound. Report per-case status, HTTP/error category, first-attempt success, retry count, and latency. Do not create a composite quality score from a tiny sample.

## Result classes

Classify separately:

- healthy response;
- empty or truncated response;
- incompatible request/model route;
- authentication/permission failure;
- rate limited;
- transient server/network/timeout failure;
- unknown or malformed response.

A passing smoke test means only that the selected request path responded correctly at that moment. It does not qualify the model for a router role.

## Handoff

For a new model, save the exact model ID, adapter/protocol, run cap, timestamp, redacted per-case results, and input/config hashes. Recommend a role-fit evaluation when the user needs routing or quality evidence. Do not edit the router.
