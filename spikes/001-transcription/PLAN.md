# Spike 001 implementation plan

Spec: [SPEC.md](SPEC.md). Status: preflight reviewed; implementation authorized under the updated spec and [resolutions](review/preflight-resolutions.md). Owner approved this bounded probe on 2026-10-26; the full app design remains open.

Use Subagent-Driven Development, adapting scratch-work deletion to the owner's explicit retention requirement. Independent file-owned slices run in one batch; workers never commit or spawn subagents. Main integrates and commits serially. Work on `spike/transcription` in this newly initialized repository; there is no pre-existing main branch or implementation requiring a second worktree.

## Task 1 — pinned persistent engine adapter

Files owned: `backend.py`, `engine.lock.json`, `native/**`, `tools/build_engine.py`, `tests/test_backend.py`, `review/task-1-report.md` (all relative to this spike).

Read SPEC.md first, including the backend contract. Inspect pinned engine README/model docs/help and, where needed, authorized headers/implementation. Build under `.tools/` and cache downloads under `.cache/`; pin all source/submodule revisions and source hashes. No host installs or model downloads. A persistent C++ helper with a line-oriented protocol is acceptable and avoids hand-written unsafe ABI guesses. Establish actual native streaming support and cumulative result semantics.

TDD: first cover validation, lifecycle/close, serialization, persistent process/model reuse, stream reset and final flush, unsupported capability errors and source-pin verification. Demonstrate guard failure on a tampered pin if adding a pin guard. Build and test the adapter, but leave timed real-model experiments to the coordinator after all workers are idle. Unit fakes do not count as inference evidence. Report exact test commands/results, build command, artifact paths and unresolved backend limitations.

## Task 2 — replay runner, policies and metrics

Files owned: `run.py`, `policy.py`, `metrics.py`, `tests/test_policy.py`, `tests/test_metrics.py`, `tests/test_runner.py`, `review/task-2-report.md`.

Implement SPEC.md's backend and manifest consumer contracts without changing files owned by other tasks. Keep import of the heavy backend lazy so pure tests run without a compiled engine. Expose endpoint, LocalAgreement-2 hybrid and genuine native-stream arms. Preserve stable history and final corrections; reject unsupported rolling-window lengths explicitly. Record paced-clock arrivals, decode/queue time, coalescing/backlog and model/source fingerprints. Record metric definitions and unsupported word-end latency, not invented ground truth. Normalized WER includes operation counts and text.

TDD: no future samples, stable prefix disagreement/revisions/final correction, bounded stale-job coalescing/finalization, stream reset/chunk/final handling, malformed manifest/output paths, normalization/empty-reference WER and metric accounting. Use fake engine/clock for deterministic tests, then coordinator runs the real adapter. Prefer Python standard library and `unittest`. Report exact red/green tests and concrete CLI commands for both models/arms.

## Task 3 — licensed bilingual fixture slice

Files owned: `fixtures/**`, `tools/fetch_fixtures.py`, `tests/test_fixtures.py`, `review/task-3-report.md`.

Follow SPEC.md's manifest schema. Verify a small public English/Spanish dataset license and pin its revision/rows before downloading a few clips. Do not download whole datasets, model assets or private audio. Preserve provenance, references, hashes, conversion details, licensing and oracle endpoint labels in `fixtures/README.md`. Include short clips plus a longer explicitly derived fixture if useful without making the default experiment expensive. No synthesized voices or unapproved host install. Use existing tools or standard library conversion where possible.

TDD: manifest path confinement, fixture/reference hashes, WAV type/rate/channels/duration, verified IDs and oracle bounds; corrupt a fixture in a temporary test directory to prove verification fails. Tests must not depend on network. Fetch downloads are project-contained and must not silently overwrite tracked modifications. Report byte size, license/source evidence, tests, and exact regeneration command.

## Task 4 — repository and spike documentation

Files owned: root `AGENTS.md`, `.gitignore`, `README.md`, `spikes/README.md`, this spike's `README.md`, `docs/requirements.md`, `docs/README.md`, `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md`, `review/task-4-report.md`.

Create concise agent guidance tailored to this project: approved native/RPC direction, retained spikes and reproducible findings, docs before dependency source, actual test commands, evidence/claim labels, no public private data or weights, no silent product-policy decisions. Root README describes purpose and current research status, not a finished app. Ignore `.omp/`, local build/source/model caches, worktrees and generated throwaway outputs; keep curated fixture/result artifacts trackable. Do not choose a license on the owner's behalf.

Amend approved requirements without renumbering IDs: both installed models will be tested; Firefox retained as candidate; invisible where possible/disguised otherwise; tests/spikes and findings retained. Mark the previous probe/download/throwaway recommendations as superseded, preserving historical observations. Do not claim any inference/capture success. Verify links and commands that are already available; pending links to owned sibling files can be checked after integration. Never edit SPEC.md, PLAN.md or progress ledger.

## Task 5 — Natively/HackerRank claim trace

Files owned: `spikes/002-hackerrank-claims/**`, `review/task-5-report.md` under Spike 001.

Bounded public-document/authorized-source research, no GUI or interview access. Reuse the existing 15-row inventory and pinned Natively main/release revisions rather than redoing the whole audit. Ask what HackerRank-specific marketing claims are actually supported by source paths, generic focus/nonactivation/window/identity mechanisms, or independent evidence. Distinguish invisibility from disguise; version drift and inactive modules matter. Map to representative ST IDs, cite exact revisions/line evidence where practical, and propose a synthetic capture/focus test matrix. Firefox remains conditional. No claim to defeat undisclosed server-side integrity mechanisms. Report findings and documentation/source checks; no runtime test is implied.

## Integration and task reviews (coordinator)

- Settle contracts/preflight ledger; dispatch contrarian review before implementation and fix important issues. Initialize Git on a work branch, personal local identity.
- After preflight, dispatch Tasks 1–5 together with disjoint paths and retained brief/report paths. Main owns SPEC/PLAN/progress, review packages, findings/results and Git/GitHub actions.
- Run `python3 -m unittest discover -s spikes/001-transcription/tests -v`. Check fixture license, privacy, relative links and CLI help. Read worker reports before review.
- Commit each completed slice serially. Give reviewers the task brief/report and a generated task-specific diff package, requiring explicit spec-compliance and quality verdicts. Fix via workers with covering tests and scoped re-review.
- Once builders/workers are idle, run arms sequentially with both cached models and real paced replay. Prefer two measured repeats after warmup; record evidence and limitations if runtime behavior prevents a planned arm. Do not replace a failing native stream with batch and label it streaming.
- Retain `FINDINGS.md` and selected `results/` JSON with reproducible commands and source/model/fixture fingerprints. Verify tested code is committed or byte-identical to the committed artifact.
- Final broad review, covering re-tests, privacy/identity audit, public GitHub creation/push and remote SHA/visibility readback. No force push, version bump, release or automatic license choice.

## Finish criteria

Repository contains necessary guidance, reproducible tests, pinned engine/build instructions, licensed bilingual fixtures, actual results for both models (or precise measured blockers), independently reviewed findings and a verified public remote. No full-app capability, live capture behavior or product latency/accuracy threshold is inferred from this spike.

## Preflight amendments

- The updated SPEC and retained task briefs/resolutions supersede older interface examples here: prefer official ctypes binding, library_path, per-call language, explicit native commit fields/context units, frozen-tick replay and strict/atomic metrics.
- Git was initialized on the work branch; baseline planning commit is recorded in the ledger. `.gitignore` exists before build/fixture workers start.
- Fixture acquisition uses bounded HTTP Range prefixes and filename-mapped TSV references instead of the currently failing FLEURS rows API.
- Task 4 additionally owns the small public-artifact audit script/tests and privacy-only generalization of sensitive quoted prose in the raw preflight report.
- Owner approved additional parallel native shell/UI and synthetic window/capture/focus spikes. They have independent plans/ownership under 003 and 004, not shared ASR implementation.
