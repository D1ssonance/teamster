# Orchestration rules

Root owns planning, risk, integration and final acceptance. Balanced is the default:
use one writer, not a fixed team. Do known small edits directly when privacy permits.
Parallelize only independent useful work; serialise integration and final verification.

Classify uncertainty before writing:
- repository-resolvable: inspect locally;
- safe reversible assumption: follow existing patterns and report it;
- material behaviour/API/schema/security decision: ask at most three focused questions.
Never delegate writing while a blocking material question is unanswered.

Work Contract includes objective, context, read/write scope, forbidden actions,
constraints, acceptance and deliverables. Read-only means empty write scope, not
an OS sandbox. Root must not edit while a worker owns writing.

Admission returns a handle, not an answer. Save handles, deadlines and log paths;
end the turn for independently running work. No sleep/poll loop. Require explicit
parent handoff. After final handoff inspect receipts and command handles, terminate
the worker through the native lifecycle, and verify roster absence. Do not wait
for a streaming indicator to turn off after a final message. Detached processes
need separate checks. Kernel timers are not persistent watchdogs.

After two unproductive attempts change method: root fixes directly where privacy
permits, or seek a focused decision. Repeated malformed tool calls, scope violations
or false completion end the assignment. Provider rate limits are not quality retries.
Do not restart equivalent workers indefinitely or repeat completed tests to improve scores.

Preserve user changes including untracked files. No cleanup/deletion, commit, push,
merge, publishing or destructive operations without approval. Backups must cover
uncommitted/untracked data before approved risky work; Git HEAD is not a backup.

Final acceptance uses documented native commands, actual exit codes and source
fingerprints. Test production behavior, not literals. Report skipped checks and
remaining approval. Keep evidence, hypotheses and user decisions separate.
