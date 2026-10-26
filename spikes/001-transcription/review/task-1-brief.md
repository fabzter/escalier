# Task 1 — pinned persistent engine adapter

Read this first; it is your task requirements. Shared binding contract and scope: [SPEC.md](../SPEC.md), especially Global constraints and Python backend contract. Do not read the whole plan or other workers' reports. No subagents and no commits. Use write/edit tools for authored files; shell is for execution/build/download only.

## File ownership

Only `spikes/001-transcription/backend.py`, `engine.lock.json`, `native/**`, `tools/build_engine.py`, `tests/test_backend.py`, and this task's report. Other workers own runner/policy/metrics, fixtures/fetcher, and repository docs. Do not edit those.

## Implementation

- Inspect pinned engine README/model docs/help first; relevant public headers/implementation are expressly authorized if necessary. Engine revision is in SPEC.md. Pin source/submodules and hashes; build under this spike's `.tools/`, download/cache under `.cache/`. No system installs or model downloads.
- Implement the exact `Engine` Python interface in SPEC.md using a persistent model process or safe native bindings. Constructor loads once, calls reuse the model, `info` is serializable and honest about actual backend evidence. Native helper is acceptable; do not guess an undocumented C ABI.
- Establish actual native streaming capabilities/reset/final flush and cumulative transcript semantics. No batch masquerading as streaming; unsupported capabilities fail clearly. Null timestamps are preferable to fabricated times. Validate finite mono samples and 16000 Hz; safe idempotent close/error behavior.
- Keep unit testing/build independent of real model inference. Leave timed cached-model measurements to the coordinator when CPU/GPU work is idle. Report exact helper executable/build command and any required runtime resource paths.

## TDD and evidence

Start with failing validation, lifecycle/close, serialization, persistent process/model reuse, stream reset/final flush, unsupported capability and source-pin tests. If a pin/integrity guard is added, show it fails on a tampered pin in a temporary directory. Test helpers/fakes are fine for unit tests, not inference findings. Use Python stdlib unittest, keeping tests offline and importable by `python3 -m unittest discover -s spikes/001-transcription/tests -v`.

## Report

Write `spikes/001-transcription/review/task-1-report.md`: DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED; files changed; red/green commands and exact results; build command/result/artifact paths; source/submodule pins; backend/runtime limitations and self-review. No commits, no subagents, no timed model benchmarks. Return only status, test/build summary and concerns.
