# Task 1 fix round 1 — scoped re-review

Date: 2026-10-26. Independent re-review of the Task 1 fix round only. I read
`review/task-1-brief.md`, `review/preflight-resolutions.md`, the original
`review/task-1-review.md` (F-01..F-07), `review/task-1-report.md`, and the
complete `review/.tools/reviews/task-1-fix-1.diff` for
`0b69d2c..5e6b950`. Scope is F-01..F-07 plus breakage in the fix. Runner
consumption was checked only as an interface consumer; I did not review the
runner and defer to its own scoped review.

No implementation edit, commit, index change, subagent, model load, model
inference, download, or GUI action was performed. Coordinator evidence is
accepted: 201 integrated tests passed on this tree and
`build_engine.py --verify-only` preserved pin `8facde6`/native `0.4.1` and
dylib SHA-256 `d3fe0516d1a0d8bcf80775857c29813ddbd787ebbe10d2bb507c2f0d0733d195`.
I did not rerun the unchanged suite. I used only
targeted probes for the changed paths.

## Verdicts

- **Spec compliance: PASS WITH CONCERNS (conditional).** All seven original
  findings are closed at the code/test level. The one remaining
  SPEC/binding gap is the non-final `snapshot()`/text-view error path
  (N-01), which can still leave the adapter reporting an active stream after
  a terminal native error. Actual native model acceptance of R=3 remains the
  explicitly deferred coordinator real-model check; the adapter now fails
  closed if the extension or value is rejected.
- **Quality: PASS WITH CONCERNS (narrow).** No regression was found in the
  changed normal paths and no Critical defect was introduced. N-01 is a
  narrow but real lifecycle edge that should be fixed or explicitly accepted;
  N-02 is a low-severity loader cache-cleanup nit.

## Finding verdicts

### F-01 — ADDRESSED

`start_stream` now fails closed with `UnsupportedCapability` when the binding
lacks `ParakeetStreamOptions` or `model.accepts(...)` is false; it never
calls `session.stream()` without the requested family extension. The requested
options are passed as `family` and the C side validates the requested value
against the model's training menu (`resolve_cache_aware_stream_geom` rejects an
out-of-menu value), so a native-begin rejection becomes a clear `EngineError`
and therefore an explicit error trial rather than an unlabelled default.
`att_context_right_frames_applied` is set to the requested value only after
`session.stream()` succeeds; `-1` model-default requests and all failures stay
null with an explicit source/reason.

The public metadata is present in `info.native_stream`, `info.stream_contract`,
top-level `info`, and every native feed/final result (flat plus nested
`native_stream`): requested, applied, accepted, exposed model default,
`applied_context_source`, evidence, and reason. The adapter API default 3 is
explicitly labelled `att_context_right_frames_default_is_model_default=false`
with "Engine API default; not model-default evidence"; the documented model
default 13 remains separate runner metadata and is never labelled runtime
evidence. A targeted fake probe with requested 13 produced
`requested=13`, `applied=13`, `accepted=null`, `model_default=null`,
`source="native"`, `reason="applied_native_begin_accepted"` consistently in
info, `stream_contract`, and the feed result, and the payloads remained strict
JSON-serializable.

Residual note R-01 below: the construction-time
`parakeet_stream_extension_accepted` probe is extension-kind acceptance using
the default 3 only, not value acceptance. This is documented and
`start_stream` probes the actual requested value, so it is not a defect.

### F-02 — ADDRESSED (reported feed/finalize defect)

Both non-final and final `stream.feed()` calls are wrapped. On a terminal
native state the adapter clears `_stream_active`, sets `_stream_failed` or
`_stream_finalized`, and re-raises `EngineError` carrying the state. A
pre-native error with the stream still active and no terminal status leaves the
adapter active for retry. `start_stream()` resets the failed stream and
proceeds; batch is available again; `close()` resets the failed stream. Tests
cover non-final feed failure, final-feed failure, finalize failure, restart,
batch recovery, and close-after-failure. The fake now models `failed` and
`finished` rather than the old synthetic label.

The original F-02 defect is closed. N-01 below is a separate admission gap on
the non-final `snapshot()`/text-view path; it is not a failure of the reported
feed/finalize fix.

### F-03 — ADDRESSED

`validate_samples` checks the packed float32 value after the required
`array('f')` copy and raises `AudioValidationError` for finite float64 values
that overflow to float32 infinity. The new test covers `1e300`, `-1e300`,
`3.5e38`, and `-3.5e38`, and asserts no native batch call was made. The
existing `array('f')` no-clamping behavior is retained.

### F-04 — ADDRESSED

The `_build_info` call is now inside constructor cleanup: a post-model-load
failure calls `_close_resources()` and marks the engine closed before the
exception propagates. The added test keeps the caught exception/traceback
alive while asserting `model_closed`, so `__del__` cannot mask the leak. The
earlier constructor cleanup paths remain in place.

### F-05 — ADDRESSED

`_load_binding` now verifies the Python source origin against the pinned
checkout (`<binding_src>/transcribe_cpp/__init__.py`) both for a pre-imported
module and after import; a different source is rejected even if it reports the
same native dylib. Environment and `sys.path` are saved/restored, import
failure drops partial `transcribe_cpp` modules, and a reported-library mismatch
is rejected. Fake-package tests cover origin acceptance, pre-imported
alternate-source rejection, env/path restoration, reported-library mismatch,
and import-failure cleanup.

I independently ran the real pinned loader (library load and backend
enumeration only; no model): origin resolved to the pinned
`.tools/transcribe.cpp/bindings/python/src/transcribe_cpp/__init__.py`, the
loaded native library was `.tools/build/src/libtranscribe.0.4.1.dylib` with
SHA-256 `d3fe0516d1a0d8bcf80775857c29813ddbd787ebbe10d2bb507c2f0d0733d195`,
version `0.4.1`, `TRANSCRIBE_LIBRARY` was restored, the
caller's `sys.path` was unchanged, and `backends()` enumerated `MTL0` and
`CPU`. This confirms the F-05/F-06 loader claims without model inference.

Residual note N-02 below: a reported-library mismatch leaves the mismatched
module in `sys.modules`, so a same-process retry with a different library path
still fails. Fail-closed is preserved; this is a recoverability/cache-cleanup
nit, not a silent reuse.

### F-06 — ADDRESSED

The report now says the import check is runtime **device-registry** evidence
from `transcribe_cpp.backends()` (Metal registered/loadable), not proof of
model placement, and explicitly leaves `Model.backend`/`Model.device` to the
coordinator's real run via `Engine.info`. The separate real loader smoke is
correctly described as source-origin evidence. No overstatement found in the
rewritten section or the F-06 disposition.

### F-07 — ADDRESSED

`FakeStream.finalize()` now uses the official terminal label `finished` and
increments a single `finalize_calls` counter on the stream; the duplicate
owner counter is gone. Tests assert the real `finished` label and exactly one
finalize call. The fake is no longer a source of misleading terminal-state
coverage.

## New / remaining important issue

### N-01 — Medium: non-final `snapshot()`/text-view errors bypass the failure synchronizer

- **Location:** `spikes/001-transcription/backend.py:1418-1426` (non-final
  `stream.snapshot()` and payload construction) versus the final path at
  `1433-1444` (snapshot inside the `try` with `_mark_stream_failure`);
  `_stream_text_view` at `470-475`; `_mark_stream_failure` at `1466-1489`;
  `start_stream`'s active guard at `1220-1223`.
- **What happens:** In the non-final branch, `stream.feed()` is guarded, but
  the following `stream.snapshot()` is only wrapped by `_wrap_native`, and
  `_result_payload` subsequently calls `stream.text()` through
  `_stream_text_view`. If either native read raises while the stream is
  terminal (`failed`/`finished`), the adapter never calls
  `_mark_stream_failure`. `_stream_active` stays `True`, `_stream_failed`
  stays `False`, and a later `start_stream()` refuses with "a native stream is
  already active". A targeted fake probe reproduced this: a snapshot failure
  with native state `failed` left `(_stream_active, _stream_failed,
  _stream_finalized) == (True, False, False)`, and restart raised
  `EngineStateError`.
- **Why it matters:** The binding for this review says terminal
  feed/finalize/snapshot native errors must not leave the adapter ACTIVE. The
  fix satisfies this for feed, finalize, and the final-path snapshot, but not
  for the non-final snapshot/text views. This is the same stale-active failure
  mode as F-02 in a narrower path. It is not a regression introduced by the
  fix; it is the remaining acceptance gap in the changed code.
- **Minimal fix:** Put the non-final `snapshot()` plus `_result_payload`/
  text-view construction inside a `try/except` that calls
  `_mark_stream_failure(stream)` and re-raises a clear `EngineError`, as the
  final branch already does (or at minimum guard the snapshot and text-view
  reads). Add a fake test whose `snapshot()` (and optionally `text()`) raises
  with native state `failed`, asserting `start_stream()` can reset and
  proceed. This requires no pin/ABI/model change.

## Residual minors

- **R-01 — extension-kind probe is not value acceptance.** The construction
  probe at `backend.py:704-713` uses `model.accepts(ParakeetStreamOptions(
  att_context_right=3))`. The official `Model.accepts` checks only the
  extension kind (`transcribe_cpp/__init__.py:1282-1285`), not the value.
  `start_stream` separately probes the requested value and native begin
  validates the menu, so fail-closed behavior is correct; the info field is
  documented as extension-kind evidence, not value acceptance. No fix needed,
  but consumers must not read it as "R=3 accepted by the model".
- **R-02 — documented model default 13 is not in `Engine.info`.** The adapter
  correctly leaves exposed model default null and labels the API default 3 as
  not model-default evidence. The documented 13 lives in runner
  `context_metadata`/`_native_stream_exposure` (`run.py:65`, `1463-1464`) and
  is never presented as runtime evidence. This is an intentional division,
  not a mismatch.
- **N-02 — reported-library mismatch does not drop the cached module.** At
  `backend.py:383-403`, a module imported from the correct source but reporting
  a different native library sets `_BINDING_MODULE`/`_BINDING_LIBRARY` to
  `None` and raises, but does not `_drop_transcribe_modules()`. A later
  same-process call with the correct library still finds the cached module and
  fails again. Fail-closed is preserved and a fresh process recovers; this is
  a low-severity cleanup/recoverability gap, and the fake test covers rejection
  but not same-process recovery.
- **R-03 — key shape, not values, differs in the nested result metadata.**
  `info.native_stream` carries `att_context_right_frames` and
  `default_att_context_right_frames` aliases; the feed/final nested
  `native_stream` context does not. The flat result and info carry the same
  requested/applied/accepted/model-default/source/reason values, and the runner
  does not read the missing nested aliases. No behavioral defect; worth
  normalizing if a future consumer requires identical nested shapes.
- **R-04 — narrow coverage for two fail-closed branches.** There is no fake
  test for a binding that lacks `ParakeetStreamOptions`, and no explicit test
  that a pre-native `Busy`-style feed error keeps the stream retryable. Both
  paths are implemented and code-inspected; the main fail-closed and terminal
  paths are tested. Low priority.

## Runner interface check

The committed runner at `81aa9e4` reads `att_context_right_frames_requested`,
`..._applied`, `..._accepted`, `model_default_att_context_right_frames`,
`applied_context_source`, `att_context_reason`, the adapter default and its
model-default flag/evidence, and `stream_contract` from `info`. Those keys are
published by this fix in `info.native_stream`, `info.stream_contract`, and the
top-level aliases; feed/final results additionally expose the flat fields.
`_native_stream_exposure` treats `applied` as engine-reported only, null
otherwise, and keeps documented 13 separate. I found no key-name mismatch. I
did not review runner logic or behavior; its own scoped review remains
authoritative.

## Evidence and limitations

- Read the complete fix diff 0b69d2c..5e6b950 and the current changed code,
  tests, and report.
- Did not rerun the 201-test suite; accepted coordinator's green run on this
  tree and `--verify-only` PASS.
- Ran the real pinned loader smoke described under F-05 (no model, no
  inference). Its environment/path restoration and origin/library hash checks
  passed.
- Ran targeted fake probes for (a) info/stream_contract/result context
  consistency and JSON serialization, (b) non-final snapshot failure
  synchronization (reproduced N-01), and (c) reported-library mismatch
  recoverability (reproduced N-02).
- No real model was loaded; actual R=3/R=13 acceptance, native accepted
  `(left,right)`, and model-default readback remain coordinator real-run
  measurements. The adapter's `applied` value is supported-API evidence
  (successful native begin after menu validation), not a native accepted-context
  readback.

## Assessment

The fix round correctly closes F-01, F-02's reported feed/finalize defect, and
F-03 through F-07 without changing the pin, ABI, or normal-path contract. The
one remaining important edge is N-01: the non-final post-feed `snapshot()`/
text-view native error path does not invoke the new failure synchronizer and
can therefore leave the adapter ACTIVE, contrary to the review binding. That
should be fixed (small, testable change) before the adapter lifecycle is
considered fully closed; the loader cache nit N-02 and the notes above are
non-blocking.
