# Evidence and privacy

## Evidence package

For every model/run record:

- problem and requested roles;
- exact confirmed adapter/model identity;
- commands, cwd, caps and environment policy;
- input/fixture/source hashes;
- per-case attempts, status, error category and latency;
- rejected hypotheses and open questions;
- recommendation and confidence;
- approval still required.

Keep raw artifacts private. Use redacted reports for sharing.

## Never share

- credentials, API keys, cookies or authorization headers;
- endpoint URLs or internal hostnames;
- raw prompts/responses containing private data;
- repository bodies, proprietary fixtures or hidden tests;
- session transcripts, user names, local paths or personal identifiers;
- exact internal model/provider/project/repository names when publishing the anonymized package.

## External models

Do not send confidential corporate material to an external model. Use synthetic fixtures and public-safe examples. API availability and native-agent identity must be recorded separately.

## Metrics

Quality and reliability come first; speed is a separate descriptive metric. Token count and cost are excluded from selection. Small samples support reversible pilots, not universal ranking claims.
