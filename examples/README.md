# Illustrative templates, NOT executable configuration

The JSON files in this directory illustrate concepts only. They are not a tested
loader schema. Do not load them into production. Placeholder provider/model
strings identify no real service. Map fields to your installed loader contract,
remove unsupported fields, and verify exact roundtrip equality before use.

`metadata`, `workflow` and `maxConcurrentPerProvider` do not implement enforcement.
Keep validation status, model family and evaluation provenance in a sidecar catalog
if the loader does not support them. All examples start disabled.

Use a separate catalog with exact IDs, eligibility by role, family, exclusions,
evidence hashes and qualification status. An availability probe cannot change
eligibility, exclusions or family independence policy.
