---
name: router-role-fit-evaluation
description: Evaluates whether an exact model is suitable for one or more router roles using staged API, tool-protocol, native-agent, and role-specific tests. Use when assessing a new provider/model for scout, coder, reviewer, debugger, fixer, requirements, test-writer, heavy-coder, architect, or vision routing.
---

# Router Role Fit Evaluation

Use this skill when the question is suitability for routing, not merely API availability. Read [references/protocol.md](references/protocol.md) before planning or running tests.

## Required decisions

Clarify exact model ID, provider/adapter, candidate roles, allowed execution surface, request/time budget, and whether live inference is approved. A role recommendation is not permission to change a production router.

## Staged workflow

1. **Preflight:** inspect the adapter, exact registry entry, exclusions, credentials policy, and existing test fixtures. Freeze a manifest. Preserve user changes and shared quota/cooldown state.
2. **API smoke:** run the bounded model API smoke skill first. Separate unavailable/incompatible/auth/rate-limit failures from quality failures.
3. **Tool protocol:** only if the role or adapter needs tools. Test actual tool schema, argument correctness, multi-turn sequencing, malformed calls, retries, and refusal cases. Tool API incompatibility does not prove native-agent inability.
4. **Native agent:** for native agents, run hidden deterministic fixtures in the approved hardened executor. Do not execute generated code on the host. Verify exact model identity and no fallback/substitution.
5. **Role tasks:** use role-specific fixtures. Examples: scout graph/navigation, requirements contradiction handling, coder/heavy-coder implementation, test-writer tests, debugger diagnosis, fixer edit+tests, reviewer defect detection, architect decisions, vision actual visual input. Score observable outcomes, not style or token count.
6. **Review:** use an independent reviewer after checks pass. Keep reviewer-family independence explicit and manual; do not claim static routing enforces it.
7. **Report:** publish raw evidence, caveats, and a conservative role recommendation. Do not silently update reference or production routing.

## Safety and evidence

- User/provider exclusions are absolute.
- Never persist secrets, endpoints, auth headers, raw prompts/responses, or raw exception bodies.
- Do not use LLM judges for deterministic fixtures unless explicitly approved as a separate exploratory signal.
- Do not rank on token cost. Prefer quality and reliability; report speed separately with small-sample caveats.
- A model can be API-healthy but role-unqualified. A tool-incompatible API can still succeed as a native agent.
- Preserve shared admission quotas, cooldowns, and state. Never reset state to make a run pass.
- If a required role has no evidence, mark it unvalidated; do not assign it a production priority.
- Production router changes, schema changes, dependency additions, live launches, and activation require explicit user approval.

## Deliverable

Create a uniquely named private run directory containing a manifest, per-stage receipts, raw sanitized facts, role matrix, limitations, and recommendation. Include source/input hashes and exact commands. Never call a model “universally best” from a small synthetic sample.
