# Task 2 — replay runner, policies and metrics

Read this first; it is your task requirements. Shared binding contract and scope: [SPEC.md](../SPEC.md), especially Global constraints, backend/fixture contracts and Policies. Do not read the whole plan or other workers' reports. No subagents or commits. Author files with write/edit, not shell string surgery.

## File ownership

Only `spikes/001-transcription/run.py`, `policy.py`, `metrics.py`, `tests/test_policy.py`, `tests/test_metrics.py`, `tests/test_runner.py` and your report. Another worker implements backend.py; consume SPEC's interface. Another produces fixtures/manifest.json; consume SPEC's schema. Keep heavy backend import lazy so pure tests run without a built helper.

## Implementation

- CLI documents model/helper path, manifest, arm, output, repeats and timing settings. Arms: endpoint at oracle fixture boundary; growing-prefix hybrid with LocalAgreement-2; genuine native streaming using Engine.start_stream/feed. Exact shared contract is SPEC.md; do not invent another API.
- Use real paced replay (or explicitly label simulation); measure monotonic arrivals, decode call start/end, queue lag, available audio horizon and coalescing/backlog. Only feed arrived audio, never future samples. Blocking decode wall time changes which samples have arrived: coalesce stale partial updates rather than enqueue every missed tick. Finalization is prioritized at oracle end. Reset stream state between trials.
- Preserve confirmed stable-prefix history. Conflicting later hypotheses/final corrections are explicit events, not silent evidence rewrites. Retain raw text and tokens/timings. Explicitly reject unsupported long rolling-window behavior rather than silently truncate evidence.
- Normalized WER records normalized reference/hypothesis and substitutions/deletions/insertions; define empty-reference behavior. No gold word timing exists: word-end display latency is unsupported/null. Report first partial/stable/final replay-relative time with honest definitions, load and warmup distinct from decode.
- Results include source fingerprints, engine/model/fixture identity/hash, host/Python metadata without private absolute paths, replay mode/config, model load/warmup and per-trial events/metrics. Reject malformed manifests, path escape, missing/mismatched fixture hashes and unsupported capabilities. No new dependencies/models/system installs.

## TDD

Red then green deterministic tests for common-prefix disagreement/stability/final correction, no-future-audio, blocking decode/coalescing/finalization, native stream chunk/reset/final flush, normalization/WER accounting including empty references, manifest validation/path confinement and metadata/metric integrity. Use fake clocks and fake engines, not tautological tests. Offline standard-library unittest. Tests run under root discover command in SPEC.md.

## Report

Write `spikes/001-transcription/review/task-2-report.md`: status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED; changed files; exact red/green commands/results; CLI examples for both models/arms; metric definitions and self-review. No timed model experiments or commits. Return brief status/tests/concerns only.
