# Task 1 fix round 2 — scoped re-review

Date: 2026-10-26. Scoped re-review of the Task 1 fix round only. Inputs read:
`review/task-1-brief.md`, `review/preflight-resolutions.md`, the N-01 finding in
`review/task-1-fix-1-review.md`, the Fix round 2 section of
`review/task-1-report.md`, and the complete
`review/.tools/reviews/task-1-fix-2.diff` for `56b33db..3993220`. Scope is N-01
plus new breakage in this fix diff. F-01..F-07 were accepted in round 1 and
were not re-reviewed; N-02 and the residual/minor items were not reopened.
Runner behavior was not reviewed.

No implementation edit, test edit, commit, index change, subagent, model load,
model inference, download, or GUI action was performed. This review wrote only
this report. Coordinator evidence is accepted: a fresh backend suite PASS
(1.300 s) on this tree, 204 integrated tests PASS (2.441 s), the four-changed-
file privacy scan PASS, and pin/dylib verification preserved (`8facde6`,
native `0.4.1`, dylib SHA-256 prefix `d3fe0516…`). I did not repeat those
suites. I confirmed the review diff is byte-identical to
`git diff 56b33db..3993220` and that the range changes only four paths.

## Finding verdicts

### N-01 — non-final `snapshot()`/text-view errors bypass the failure synchronizer — ADDRESSED

- `backend.py:1411-1427`: the non-final branch now uses one staged `try`
  covering `stream.feed(pcm)`, `stream.snapshot()`, and
  `_result_payload(..., stream=stream)`. `_result_payload` reads
  `stream.text()` through `_stream_text_view` at `backend.py:1193`
  (helper at `470-475`), so snapshot and text-view reads are both inside the
  guarded block. Every exception calls `_mark_stream_failure(stream)` and
  re-raises `EngineError` naming the stage and the synchronized native state.
- `backend.py:1467-1490`: `_mark_stream_failure` is the same synchronizer the
  final path and feed path use. A terminal `finished` state clears
  `_stream_active` and sets `_stream_finalized`; any other terminal state
  clears `_stream_active` and sets `_stream_failed`; an `active`/`unknown`
  state with no `last_status` preserves the stream for retry. This satisfies
  the terminal and genuinely-retryable halves of N-01.
- Restart/batch/close after a terminal non-final snapshot/text-view error:
  `start_stream` gates only on `_stream_active` (`backend.py:1220-1223`) and
  then calls `_discard_finished_stream()` (`1312`), which releases/resets the
  old stream and clears all flags (`1376-1389`); `transcribe` gates only on
  `_stream_active` (`1108-1112`); `close` releases the stream and clears
  active (`994-1000`, `970-975`). All three paths are reachable once the
  synchronizer clears active.
- Tests (`tests/test_backend.py:786-833`) exercise the production
  `Engine.feed` path with the real synchronizer: failed snapshot → next feed
  rejected → restart resets stream 0 and starts stream 1; failed text view →
  restart; snapshot failure with native state still `active` → next feed
  succeeds; failed snapshot → close resets and closes the model. The fake
  mutates `state` to `failed` before raising, so the terminal branch is
  genuinely entered rather than simulated by an adapter-side flag.

## New breakage in the fix diff

None Critical/Important.

Non-blocking notes (not breakage): the new tests cover the `failed` terminal
variant; the `finished` variant and batch-after-snapshot-failure are
code-verified through the same synchronizer/active-clear path but are not
separately asserted. Also, the previous
`test_close_after_feed_error_resets_failed_stream` was replaced by the
snapshot-failure close test rather than supplemented; close behavior is
failure-source-agnostic, so no meaningful coverage is lost. The only other
behavior change is that non-final `_result_payload` construction errors,
including text-view errors already wrapped by `_stream_text_view`, are now
re-wrapped as `EngineError` with a stage/state prefix — the intended fix. The
successful non-final path performs the same feed → snapshot → payload sequence
as before, and the final path is untouched.

## Verdicts

- **Spec compliance (scoped): PASS.** N-01's binding behavior is met:
  non-final `snapshot()`/text-view terminal errors invoke the same failure
  synchronizer; `failed`/`finished` clear active so restart, batch, and close
  proceed; retryable active failures preserve the stream. Pin/library/normal-
  path behavior is unchanged.
- **Quality: PASS.** Minimal change using the existing synchronizer, clear
  staged error messages, and regression tests that assert observable lifecycle
  outcomes. No new Critical/Important breakage.
- **Fix round:** All findings addressed, no new Critical/Important breakage.

## Evidence and limitations

- `diff <(git diff 56b33db..3993220) .tools/reviews/task-1-fix-2.diff` is
  empty; `git diff --name-only` lists only `backend.py`,
  `tests/test_backend.py`, `review/task-1-report.md`, and the round-1 review
  file.
- `git diff 56b33db..3993220 -- engine.lock.json tools fixtures` is empty:
  pin, build helper, and fixtures are untouched.
- Ran the full issue test module myself:
  `python3 -m unittest discover -s spikes/001-transcription/tests \
    -p test_backend.py -v` → `Ran 59 tests in 1.288s` OK, including all four
  N-01 regression tests and every sibling stream/lifecycle test. I did not
  repeat the package-wide integrated suite or the pin/privacy scans; those
  coordinator PASSes are accepted unchanged.
- Consistency sweep: every native stream call site in `backend.py` was
  enumerated. `stream.feed`/`snapshot`/text-view reads occur only inside the
  non-final and final synchronized `try` blocks; final-path text views run
  only after active is cleared; `session.stream` errors precede the
  `_stream_active` assignment; `_result_payload` touches the stream only via
  `_stream_text_view`; `run.py` uses only the `Engine` API (`start_stream`/
  `feed`) and no native stream objects. No second call site or duplicate copy
  needs the same change.
- Scope check: the backend diff is the minimal staged `try`; the success path
  performs the identical feed → snapshot → payload sequence. The only other
  changes are tests and review/report prose.
- No real model was loaded or inferred.
