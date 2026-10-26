# Task 1 review — pinned persistent engine adapter

Date: 2026-10-26. Independent task-scoped spec/quality review. Read-only on the
checkout; the only write is this review. Scope: diff
`a27ec6d4e2ecd0c59742bc880e33ce20e4555f7a..7dfcfd6628d0660c606bbb7914fa31e053365d22`
for `backend.py`, `engine.lock.json`, `tools/build_engine.py`,
`tests/test_backend.py`, and `review/task-1-report.md`, against the Task 1
brief, SPEC.md's global constraints and Python backend contract, and the
preflight resolutions. No implementation edits, commits, index changes,
subagents, model inference, or downloads were performed.

Coordinator evidence accepted: 119 backend/policy/metrics/runner tests passed
in 1.523 s, and `build_engine.py --verify-only` exited 0 with the locked
artifact verified. I did not rerun the suite. I did run one targeted stdlib
probe for F-03 (`array('f')` packing), and I read the diff once as required.

## Verdicts

- **Spec compliance: PASS WITH CONCERNS (conditional).** The required
  `Engine` surface, one-load model reuse, separate batch/stream sessions,
  lifecycle/final-flush rules, raw-final-text and null-timing semantics,
  project-local no-build discovery, and source/lock/artifact provenance are
  implemented and match the pinned official binding. The one substantive
  contract/experiment-validity gap is F-01: when a streaming model does not
  accept the Parakeet cache-aware extension, `start_stream` silently runs
  without applying `att_context_right_frames` instead of failing clearly, and
  the applied/reason state is only private. The pinned multilingual Nemotron
  3.5 should accept it (family/cache-aware docs); that must be verified on the
  real model, or F-01 fixed, before an R=3 trial is trusted.
- **Quality: PASS WITH CONCERNS (conditional on F-01/F-02).** No Critical
  defects were found. The adapter correctly leans on the official binding's
  materialized results and cleanly separates batch/stream state. F-02 is a
  real but recoverable error-state bug; F-03–F-07 are low-severity
  robustness, coverage, and report-accuracy follow-ups.

## What was independently verified

- **Official binding surface.** Against
  `.tools/transcribe.cpp/bindings/python/src/transcribe_cpp/__init__.py` and
  the pinned C headers: `Model` constructor/`session()`/`roles`/`capabilities`/
  `device`/`backend`/`accepts`, `Session.run`/`stream`, `Stream.feed`/
  `finalize`/`snapshot`/`text`/`reset`/`state`, `ParakeetStreamOptions`,
  `Timings`, `Capabilities`, and `Role.ASR` are used with the documented
  signatures. No undocumented C ABI is guessed.
- **Pointer ownership.** `Result` is explicitly fully materialized ("holds no
  native pointers", binding lines 673–690); `Stream.text()` returns owned
  `StreamText` copies (707–720); `Stream.snapshot()` returns `Result`
  materialized via `_materialize` (1909–1911). The adapter stores only decoded
  strings/ints/dicts, so a later native call cannot invalidate a returned
  dict. This meets SPEC's pointer-copy requirement.
- **Lifecycle.** `Stream.snapshot()` remains callable after `finalize` (the
  binding keeps the stream active until reset; `Stream._h` lines 1866–1872),
  `Stream.reset()` releases the model stream lease (1934–1944), and
  `Session`/`Model.close()` free sessions before the model (1373–1393,
  1471–1478). The adapter resets before closing sessions/model (backend.py:
  791–826), and reuses separate batch/stream sessions.
- **Timings and language.** `transcribe_get_timings` is documented safe
  before any run and `load_ms` is model-scoped (`include/transcribe.h:
  2455–2498`); the probe is valid. `decode_ms == 0` is "unknown" and is
  nulled by `_sanitize_decode_ms` (backend.py:413–420). Explicit language
  hints do not echo through `transcribe_detected_language`
  (`include/transcribe.h:2535–2553`), matching the adapter's
  detected-note logic. `auto` maps to the C NULL/empty hint, not the literal
  string; per-call hints do not reload the model.
- **Provenance.** The actual checkout is at the pinned
  `8facde6fcd8fb9caa585a5788ab450df6e8ec7db`, clean, with no submodules;
  `HEAD:ggml` and `HEAD:patches` match the lock (`417a…`, `ed99…`); the
  three patch-file SHA-256 values, ABI hash (`f99ad…`) and ABI-file SHA-256,
  and artifact SHA-256 (`d3fe…`, 1,966,072 bytes) match `engine.lock.json`.
  `verify_checkout` / `verify_lock_source_pin` fail on revision, dirty-tree,
  ggml tree/SHA, patch tree/file, and lock drift per the test suite
  (`tests/test_backend.py:986–1068`); the runtime artifact-hash guard is
  tested (`tests/test_backend.py:851–870`), and the equivalent build check was
  exercised by the coordinator's `--verify-only` run.
- **Native capability/reset/final semantics.** `stable_prefix_agreement_n=2`
  maps to the C STABLE_PREFIX policy (C 2066–2087; binding 1681–1729), empty
  `feed(final=True)` flushes without a zero-sample native feed (C requires
  `n_samples > 0`; 2310–2332), non-final empty feed is rejected, final
  `final_text` is the raw final `full_text`, and committed/tentative are
  preserved separately. No batch fallback exists for a model without
  `supports_streaming`.
- **Backend evidence.** `Model.backend`/`Model.device` are actual runtime
  values, not a build flag; `backend_available("auto")` is true whenever any
  device exists (`include/transcribe.h:990–1005`). A device-query failure is
  recorded as unavailable with a reason rather than guessed.
- **Tests/build evidence.** 44 backend tests (fakes, lifecycle, serialization,
  stream reset/flush, unsupported capability, discovery, lock/artifact, and
  temporary-git tamper tests) are present; coordinator ran the integrated
  suite green and the locked build verified. The report's no-model limitation
  is honest and matches the task instruction that timed inference is the
  coordinator's job.

## Strengths

- Exact SPEC `Engine` interface and signatures; no import-time native load,
  no implicit build/download, and project-local discovery that never consults
  PATH/site-packages.
- Correct choice to use the official stdlib-only ctypes binding instead of a
  custom helper; the adapter adds only thin validation, lifecycle, language,
  and provenance logic.
- Careful honesty about uncertain native facts: null `load_ms` with a source/
  reason, null `decode_ms` for zero/unknown, null accepted/default context
  instead of guessed values, null token times when the returned timestamp
  kind is none, and `"unknown"` for an empty backend string.
- Strong lock/build design: exact revision, clean-tree enforcement, no
  submodule assumption, vendored ggml tree/patch-tree/ABI/artifact pinning,
  project-relative public paths, tamper tests, and a build command that can
  verify without model inference.
- Tests exercise real adapter state transitions with a faithful fake binding
  plus a real temporary git repository for the pin guard; they are offline and
  importable by the required root discover command.

## Findings

### F-01 — High (conditional): unsupported Parakeet context is silently ignored, and the applied state is not public

- **Location:** `spikes/001-transcription/backend.py:1054-1085` (probe and
  `context_record`), `1095-1108` (stream starts without `family` when not
  accepted), `1114-1122` (`_stream_meta` private), `652-664`
  (`info.native_stream` hardcodes `att_context_right_frames=None`);
  `tests/test_backend.py:735-743` pins the silent behavior; runner records
  only the requested value (`run.py:619-639`, `1244-1270`).
- **What happens:** If `self._model.accepts(ParakeetStreamOptions(...))` is
  false, the adapter sets `context_record["applied"] = False` and a reason,
  but still calls `session.stream()` without `family`. The native stream then
  runs with the model/family default. The only place that knows the context
  was not applied is the private `_stream_meta`; `info.native_stream` always
  says "not exposed", and the runner records `att_context_right_frames=3`
  from the CLI without an applied/accepted field.
- **Why it matters:** The spike's native-stream comparison is explicitly R=3
  versus the offline R=13 path. The multilingual Nemotron 3.5 documents a
  cache-aware menu `{0,3,6,13}` and defaults to the max-accuracy entry (13).
  If the real model does not accept the Parakeet extension (or the probe
  fails), the native arm would silently run at the default R=13 while the
  trial metadata records requested R=3 — an unlabelled confound. The cached
  Nemotron 3.5 is family `parakeet` and the docs say it is cache-aware, so
  acceptance is likely, but no real model was loaded in this slice
  (`task-1-report.md:261`), so it is unverified here. This is distinct from
  the tested no-batch-fallback behavior; it is a no-context fallback.
- **Minimal fix:** Fail closed when `native_stream` is true but the model does
  not accept the Parakeet stream extension (or the binding lacks it), at least
  when a non-default `att_context_right_frames` was requested; or expose
  `applied`, `reason`, `requested_frames`, and `accepted_frames` in every feed/
  final result (and/or `info`) and make the runner mark the trial invalid when
  not applied. Add a fake test asserting the chosen behavior instead of only
  the silent one. Before the R=3 arm, run
  `model.accepts(ParakeetStreamOptions(att_context_right=3))` and one real
  `start_stream` on the cached Nemotron 3.5 (no feed/inference required).

### F-02 — Medium: a terminal native feed error leaves the adapter state "active", preventing restart

- **Location:** `spikes/001-transcription/backend.py:1159-1164` (non-final
  feed) and `1175-1178` (final feed call, outside the `except` at
  `1181-1192`); `start_stream`'s active-stream guard at `1011-1014`.
- **What happens:** The binding's `Stream.feed()` releases the model stream
  lease and re-raises when the native call transitions the stream to FAILED
  (`transcribe_cpp/__init__.py:1874-1884`). If that happens, `_stream.feed`
  raises before the adapter's finalize `try`; the adapter leaves
  `_stream_active=True` and `_stream_failed=False`. A later `feed()` retries
  a failed native stream; `start_stream()` refuses with "a native stream is
  already active"; batch calls stay blocked by `_stream_active`. Recovery
  requires a further surfaced failure: an empty `feed(final=True)` on the
  FAILED stream reaches the finalize `except`, marks the flags, and then a
  later `start_stream()` can reset; `close()` also recovers by ending the
  engine. The adapter does not fail fast or reset on the original feed error.
- **Why it matters:** The brief requires safe idempotent close/error behavior.
  `close()` is safe, and the runner aborts a failed trial, but the adapter
  cannot start a new stream or resume batch immediately after a feed failure,
  unlike the failed-finalize path that is explicitly tested
  (`tests/test_backend.py:652-661`). The state reported by the adapter is
  stale relative to the binding.
- **Minimal fix:** Wrap the `stream.feed()` call(s) in the same error handler
  used for finalize; on exception inspect `stream.state`/`last_status` and set
  `_stream_active=False`, `_stream_failed=True` when the native stream is no
  longer active (leave ACTIVE unchanged for a pre-model Busy/validation
  error). Add a fake `fail_feed` test that asserts `start_stream()` can reset
  and proceed.

### F-03 — Low: finite float64 values can pack to float32 infinity after validation

- **Location:** `spikes/001-transcription/backend.py:397-407`
  (`validate_samples`).
- **What happens:** `math.isfinite(number)` checks the Python float, then
  `copied.append(number)` packs into `array('f')`. A finite `1e300` or
  `3.5e38` becomes `inf` in float32 (targeted probe confirmed:
  `array('f',[1e300]) -> inf`). The adapter therefore passes a non-finite
  sample to native, contrary to its "finite" validation/docstring. Native
  feed rejects `Inf` and (per the C header) keeps a stream ACTIVE, so the
  failure is still surfaced, but not as the adapter's `AudioValidationError`.
- **Why it matters:** The runner's WAV PCM is in `[-1,1]`, so this is an edge;
  the validation claim should still hold after the required float32 copy.
- **Minimal fix:** After appending, check `math.isfinite(copied[-1])` (or
  range-check against float32 max) and raise `AudioValidationError`; add a
  test with `1e300`/`3.5e38`.

### F-04 — Low: `_build_info` failure after model load does not close the model

- **Location:** `spikes/001-transcription/backend.py:526-550`; `_build_info`
  is called outside the constructor's cleanup `try` and itself calls
  `.stat()` at `690` and `_model.arch`/`_model.variant` at `691-692`.
- **What happens:** If any of those reads/raises after `binding.Model(...)`
  succeeded, the constructor propagates without `_close_resources()`. The
  native model is then freed only when the failed `Engine` object is finalized
  by `__del__`, not at the point of failure.
- **Why it matters:** This is a narrow error-cleanup gap in a constructor that
  otherwise closes on capability/backend/probe failures; model memory/GPU
  resources can linger after a failed construction.
- **Minimal fix:** Include the `_build_info` call in the existing cleanup
  `try` (or `try/except: self._close_resources(); raise`). Add a fake model
  whose `arch` property raises and assert `model.closed` is true.

### F-05 — Low: the real official-binding import path is untested, and a pre-imported module can bypass pinning

- **Location:** `spikes/001-transcription/backend.py:293-362`
  (`_load_binding`); every `Engine` test patches it
  (`tests/test_backend.py:360`, `410`), while the build `import_check`
  (`tools/build_engine.py:448-475`) imports the binding directly, not through
  `Engine._load_binding`.
- **What happens:** The environment save/restore, `sys.path` insertion/removal,
  import-failure cleanup, and `library_path()` verification are only exercised
  by a real model/engine run. Also, `import transcribe_cpp` returns an already
  imported module if one exists; `library_path()` verifies the native dylib,
  not the Python source origin, so a globally installed/alternate
  `transcribe_cpp` that loads the same dylib would be accepted even though it
  did not come from the pinned checkout.
- **Why it matters:** In a clean coordinator process the sys.path insertion
  wins; the risk is an environment mismatch or a regression in the only real
  load path before the first real run. The report claims the official binding
  is loaded from the pinned checkout; the loader does not enforce the Python
  source path.
- **Minimal fix:** Check `sys.modules.get("transcribe_cpp")`/its `__file__`
  against `binding_src` before import, and add a fake-package `_load_binding`
  test for env/path restore and a library-path mismatch. A coordinator
  `Engine(...)` smoke test (which loads the Model) can close the integration
  gap later.

### F-06 — Low: report overstates the import-check backend evidence

- **Location:** `spikes/001-transcription/review/task-1-report.md:145-155`;
  the check at `tools/build_engine.py:448-475` only loads the library and calls
  `transcribe_cpp.backends()`, not `Model.backend`/`Model.device`.
- **What happens:** The report says "This is runtime backend evidence from
  `Model.backend`/`Model.device` and the device registry". No `Model` is
  constructed by the import check (and the same report at line 261 says no
  real model was loaded). The device registry IS runtime evidence that a
  Metal device is registered; the actual model placement (`Model.backend`/
  `device`) remains a coordinator measurement.
- **Why it matters:** Global constraint 20 explicitly distinguishes actual
  runtime backend evidence from a build flag; the code's `info` path is
  honest, but the report's sentence overstates what the import check proved.
- **Minimal fix:** Reword to "runtime device-registry evidence; actual model
  backend/device to be recorded by the coordinator's real run."

### F-07 — Low: test fake's stream state/count diverge from the official binding

- **Location:** `spikes/001-transcription/tests/test_backend.py:141-147`.
- **What happens:** `FakeStream.finalize()` increments both
  `self.owner.finalize_calls` and `self.finalize_calls`, and sets state
  `"finalized"`. The official binding reports `idle/active/finished/failed`
  (`transcribe_cpp/__init__.py:1913-1916`) and a finalize is one native call.
  `_stream_state` is a passthrough, so production is unaffected, but the fake
  means the tests never pin the real terminal label and the duplicate count is
  confusing dead state.
- **Minimal fix:** Set state `"finished"` and increment one count; optionally
  assert the real label in the final-feed test.

## Notes, not defects

- **No real-model evidence (expected).** `supports_streaming`,
  `accepts(ParakeetStreamOptions)`, `Model.backend`/`device`, the native
  `load_ms` probe, stream snapshot `decode_ms`, and detected-language behavior
  are not exercised by this slice. The report labels this DONE_WITH_CONCERNS
  and defers it to the coordinator; that is consistent with the task
  instruction. It is the reason F-01 is conditional rather than proven.
- **Timing capability wording.** `info.capabilities.timestamps` records the
  model's max native kind (`backend.py:567`), while every `transcribe` and
  `start_stream` call requests `timestamps="none"` (`backend.py:945-950`,
  `1091`) and results therefore carry null token times. The capability claim
  is true (model capability) but could be read as "timestamps are used"; a
  `requested_timestamps: "none"` field or limitation sentence would remove the
  ambiguity. Not a correctness defect.
- **Lock fail-closed, normal path.** `_load_lock`, `verify_native_identity`,
  and `verify_library_artifact` reject a missing/malformed lock, native
  version/commit mismatch, and locked-artifact hash mismatch; an explicit
  custom library path is not rejected but is recorded as unverified. The
  build script rejects source/patch/ggml/artifact drift. The
  individual `patches[].sha256` and `abi_hash_file_sha256` lock fields are
  metadata not re-compared by `verify_lock_source_pin`, but the whole
  `patches` git tree and ABI hash are checked, so content tampering is still
  caught. Two defense-in-depth notes: `--verify-only` still calls
  `ensure_checkout()` (it can fetch/checkout a wrong HEAD before verifying),
  and default discovery prefers `native/libtranscribe.dylib` over the locked
  `.tools/build` artifact; if a `native/` file is ever added, the artifact-hash
  guard will report `verified=False` rather than fail and the native
  version/commit strings are the only remaining identity check. These do not
  affect the current checkout, which has no `native/` file.
- **`agreement_n=0` rejected.** The C API treats 0 as "library default
  (currently 3)", but SPEC's contract default is 2 and the task never needs
  0. Rejecting it is a safe API choice, not a defect.
- **`info.resolved_language` shape.** Top-level is a string/None, while the
  nested `language.resolved` is a dict; the runner reads the top-level and
  per-result values, so the compatibility alias is correct. Worth keeping in
  mind if another consumer assumes the nested shape.

## Assessment

**Task quality: Needs fixes (narrow).** The adapter is a careful, well-tested
implementation of the SPEC surface and correctly avoids the major ASR hazards
(batch masquerading as streaming, borrowed native pointers, fabricated
timings, private paths). Close F-01 (fail closed or expose/record the applied
context) and verify the cached Nemotron 3.5 accepts the Parakeet extension
before trusting the R=3 arm; fix F-02's failed-feed state so restart matches
the finalize path. F-03–F-07 can follow without blocking the planned model
path. No Critical defect was found.
