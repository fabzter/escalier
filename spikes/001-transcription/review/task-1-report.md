# Task 1 report — pinned persistent engine adapter

**Status: DONE_WITH_CONCERNS**

The adapter, build/pin helper, lock file, and unit tests are complete and the
full spike test suite is green. The remaining concerns are honest boundaries of
this slice: no real model was loaded or inferred (by instruction), so the
coordinator must exercise the real model/capabilities path; and the embedded
native binding does not expose an accepted `att_context_right` or model-default
context, so those fields are recorded as null rather than guessed.

## Files changed

- `spikes/001-transcription/backend.py` — `Engine` implementation against the
  official stdlib-only `transcribe_cpp` ctypes binding.
- `spikes/001-transcription/engine.lock.json` — reviewed engine/source/ggml/
  patch/ABI/build/artifact pin and runtime discovery contract.
- `spikes/001-transcription/tools/build_engine.py` — clone/fetch exact pin,
  clean-tree and tamper guards, out-of-tree CMake build, artifact hash, optional
  import/backend check, lock cross-check, ignored build metadata.
- `spikes/001-transcription/tests/test_backend.py` — 59 stdlib `unittest` tests
  with fakes plus temporary-git-repo tamper tests.
- `spikes/001-transcription/review/task-1-report.md` — this report.

No commits, staging, subagents, model inference, model downloads, microphone,
live calls, or system installs were performed.

## Red/green evidence

First executed draft (before fixes) was red:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 102 tests ... FAILED (failures=4, errors=2)
```

The four backend failures were test-harness/expectation defects rather than
silent adapter successes; each is fixed and re-covered:

1. `test_backend_unknown_is_reported_honestly` — fake model fell back from an
   empty backend string to `"auto"`; the adapter itself correctly reports
   `"unknown"`. Fake corrected.
2. `test_lock_validation_and_native_identity` — the test called a mocked
   `_load_lock`; the test now uses the real loader for its temp lock.
3. `test_nonempty_final_feeds_then_finalizes` — raw float32 precision compared
   exactly to Python doubles; changed to `assertAlmostEqual`.
4. `test_stream_lifecycle_errors_and_empty_final_flush` — the test wrongly
   expected `display_text` to become `final_text`; the pinned native contract
   keeps `display_text = committed + tentative` (tentative empty after
   finalize), while `final_text` is authoritative. Implementation was already
   correct; test/documentation fixed.

The two `ERROR`s were sibling test modules (`test_policy`, `test_runner`) that
could not import their modules at that moment; those workers fixed them, and
they are green now.

Green after fixes:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 204 tests in 2.441s
OK
```

Backend-only command/result:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -p test_backend.py -v
Ran 59 tests in 1.334s
OK
```

Tamper tests are part of the green suite and fail closed on deliberately
tampered temporary inputs:

- `test_dirty_tamper_fails`
- `test_wrong_revision_fails`
- `test_tampered_ggml_tree_or_sha_fails`
- `test_tampered_patch_file_fails_even_if_committed`
- `test_lock_source_drift_fails`
- `test_library_artifact_hash_guard`

Python compile check:

```text
python3 -m py_compile spikes/001-transcription/backend.py \
  spikes/001-transcription/tools/build_engine.py \
  spikes/001-transcription/tests/test_backend.py
exit 0
```

## Build and pin evidence

Source is a clean checkout of the exact SPEC revision, cloned into the ignored
project-local tools tree. The wrapper command was:

```text
python3 spikes/001-transcription/tools/build_engine.py --import-check
```

Equivalent CMake configure/build (wrapper records and verifies it):

```text
cmake -S .tools/transcribe.cpp -B .tools/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DTRANSCRIBE_BUILD_SHARED=ON \
  -DTRANSCRIBE_BUILD_TESTS=OFF \
  -DTRANSCRIBE_BUILD_EXAMPLES=OFF \
  -DTRANSCRIBE_BUILD_TOOLS=OFF \
  -DTRANSCRIBE_METAL=ON \
  -DGGML_METAL=ON \
  -DGGML_METAL_EMBED_LIBRARY=ON \
  -DTRANSCRIBE_USE_OPENMP=OFF \
  -DGGML_NATIVE=ON
cmake --build .tools/build --config Release --parallel 8
```

Result: exit 0.

- Engine pin: `handy-computer/transcribe.cpp`
  `8facde6fcd8fb9caa585a5788ab450df6e8ec7db`, version `0.4.1`.
- Official Python binding: `bindings/python`, version `0.4.1`, stdlib-only
  ctypes; not installed globally.
- ABI hash: `f99ad4169374b8f3`; ABI file SHA-256 recorded in the lock.
- Vendored ggml: upstream `d7cb574130e6f01ad25b3289685489200febcd74`, vendored
  tree `417a338844d35617ec0cc5fd70ee39b0f98cd93f`, patch tree
  `ed9971fde1a4137415f891fb1a41647f2bd6609d`; three patch files hash-recorded.
- No `.gitmodules` and no submodules; clean-tree verification required and
  passed.
- Artifact: `.tools/build/src/libtranscribe.dylib` (resolves to
  `.tools/build/src/libtranscribe.0.4.1.dylib`), size 1,966,072 bytes, SHA-256
  `d3fe0516d1a0d8bcf80775857c29813ddbd787ebbe10d2bb507c2f0d0733d195`.
- Toolchain: CMake 4.4.4, Ninja 1.13.2, Apple clang 21.0.0, Python 3.13.0,
  macOS 27.0.1 arm64.
- Build metadata (ignored): `.tools/build/engine-build.json`.

Lock/artifact verification:

```text
python3 spikes/001-transcription/tools/build_engine.py --verify-only
exit 0
lock_check.verified = true
```

The official binding import check (library load + backend enumeration only; no
model, no inference) reports:

- `native_version = 0.4.1`, `native_commit = 8facde6` (unambiguous prefix of the
  pinned full revision).
- Registered devices: `MTL0` kind `metal`, device type `gpu`, reported memory
  26,800,603,136 bytes; `CPU` kind `cpu`, reported memory 34,359,738,368 bytes.

This is runtime **device-registry** evidence from `transcribe_cpp.backends()`
(a Metal device is registered and loadable), not proof of actual model
placement: no `Model` is constructed by the import check. Actual
`Model.backend`/`Model.device` remains a coordinator real-run measurement and
must be recorded from `Engine.info` then.

Runtime resource paths (relative to the spike root):

- engine source: `.tools/transcribe.cpp`
- binding source: `.tools/transcribe.cpp/bindings/python/src`
- library: `.tools/build/src/libtranscribe.dylib`
- discovery order is recorded in `engine.lock.json`; explicit `library_path`
  is also accepted. `library_path=None` never searches the host, never builds,
  and never downloads.

## Contract implementation

- Exact `Engine` surface from SPEC: constructor, `info`, `transcribe`,
  `start_stream`, `feed`, `close`.
- Constructor loads one model once. Batch and stream sessions are separate and
  reused; per-call/per-stream language hints do not reload the model. Any
  failure after model load (capabilities/backend/probe/info construction) closes
  the model before propagating.
- `info` is a JSON-serializable dict (checked with `allow_nan=False`) and
  includes:
  - engine/version/native commit/pinned revision/library/binding, actual
    binding source path/scope, lock and artifact-hash verification;
  - model file name, scope, size, arch, variant, roles;
  - requested/resolved backend policy, reported native backend, device kind/
    type/id/memory snapshot, and evidence source; an empty backend string is
    reported as `"unknown"`, never guessed;
  - constructor wall time, native `load_ms` (or `None` + source/reason),
    capabilities (batch/native stream/timestamps/languages/LID/max audio),
    default language resolution, stream defaults, and explicit limitations;
  - compatibility aliases used by the runner: top-level `load_ms`,
    `resolved_language`, `detected_language`, `lid_supported`, a
    `native_stream` exposure block, context request/application aliases, and
    `capabilities.lid`/`streaming`.
- `transcribe` validates sample rate exactly 16000, 1-D mono numeric samples,
  finite values, float32 packability, nonempty audio, and the model’s reported
  `max_audio_ms`. It returns `text` (native cumulative `full_text`), token rows
  with nullable times, nullable native `decode_ms`, `final`, timestamp kind,
  language requested/resolved/detected/LID aliases.
- `start_stream` validates caller cadence/context/agreement/policy, requires
  advertised native streaming, and never falls back to batch. It fails closed
  with `UnsupportedCapability` if the binding lacks the Parakeet stream
  extension or the model does not accept it; it never starts a stream at an
  unlabelled model/family default. Native begin rejection is a clear
  `EngineError` naming the requested context; the pinned Nemotron 3.5 menu is
  `{0,3,6,13}`, so the API default `3` is valid.
- Stream context evidence is public in `info.native_stream`,
  `info.stream_contract`, top-level info aliases, and every feed/final result:
  requested, applied (`native` only after successful begin), accepted (`null`,
  not exposed), model default (`null`, not exposed), source, and reason. The
  API default 3 is explicitly not labelled model-default evidence.
- `feed`:
  - non-final empty → validation error;
  - non-final audio → one native feed + cumulative `full_text`/token snapshot,
    committed/tentative/display views, revision, input/audio/buffer fields;
  - final with audio → feed then finalize; final empty → native flush only;
  - final result’s `final_text` is the authoritative final `full_text`, while
    native `committed_text` is preserved separately;
  - a terminal native feed/finalize error marks the stream failed and releases
    the adapter lifecycle (restart/close/batch no longer blocked by a stale
    "active" flag); a retryable pre-native error keeps it active;
  - no batch call is substituted for native streaming.
- `close()` resets an active/finalized/failed stream to release the model stream
  lease, closes sessions then model, is idempotent, and never raises. Close
  errors are recorded by type in `info.close_errors`.
- Native text/row copies are made by the official binding at the FFI boundary;
  the adapter does not retain borrowed native pointers. A second mutating call
  cannot invalidate a returned dict.
- Native timings: zero or non-finite values become `None`; stream calls do not
  inherit batch timings. Runner call wall time is separate.
- Token times are `None` when the returned timestamp kind is `none`/unknown;
  real token times are preserved otherwise.
- Language:
  - `auto`/`autodetect` → native empty/NULL hint, recorded as
    `auto_sentinel = native_null_empty_hint`; this is the Parakeet
    `prompt.auto_id` path, not the literal string `"auto"`;
  - exact declared locale (for example `es-US` in the Nemotron 3.5 manifest),
    case-fold, short alias, or declared-language-prefix fallback; each mapping
    is recorded;
  - unsupported language fails before the native call with the available list;
  - requested/resolved/detected and LID support are recorded per call/stream.
- The official binding loader verifies the Python source origin
  (`<binding_src>/transcribe_cpp/__init__.py`) in addition to the native dylib,
  restores `TRANSCRIBE_LIBRARY` and `sys.path`, and cleans partial imports on
  failure.
- Streaming context/cadence:
  - `att_context_right_frames` is passed through; requested/applied values are
    recorded, accepted/model-default values stay null because the binding does
    not expose them;
  - `feed_chunk_ms` is recorded as caller cadence and is not sent as a native
    stream field;
  - `stable-prefix` maps to native `stable_prefix` with `agreement_n`; native
    committed/tentative units remain native units, distinct from runner
    word-level LA-2.
- JSON output is strict; non-finite native metadata is sanitized to null/None.
- `info` does not publish absolute model/cache paths: project resources are
  relative; external model paths are reduced to file name + `external` scope.

## Fix round 1 — independent review dispositions

Review: `review/task-1-review.md` (F-01..F-07). No library pin/hash changed;
there was no ABI change. Backend/runtime resources remain the same reviewed
build.

Red evidence after adding failing tests for the review findings (backend-only):

```text
python3 -m unittest discover -s spikes/001-transcription/tests \
  -p test_backend.py -v
Ran 55 tests in 1.331s
FAILED (failures=9, errors=5)
```

Representative red failures were: F-01 accepted the stream silently when
`model.accepts(ParakeetStreamOptions)` was false and lacked the public context
keys; F-02 left `_stream_active=True` and `start_stream()` raised "already
active" after a terminal feed error; F-03 accepted `1e300`/`3.5e38`; F-01 info
keys `att_context_right_frames_requested`/`att_context_right_frames_applied`
were missing. The first F-05 harness used the patched `_load_binding` mock, so
its failures were not meaningful; it now calls the saved real loader, and the
origin rejection is covered green below. The F-04 test initially passed
because `__del__` masked the leak; it was strengthened to hold the
exception/traceback and assert explicit constructor cleanup.

Green evidence after fixes:

```text
python3 -m unittest discover -s spikes/001-transcription/tests \
  -p test_backend.py -v
Ran 56 tests in 1.372s
OK

python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 201 tests in 2.427s
OK
```

Dispositions:

- **F-01 fixed (high).** `start_stream` now fails closed with
  `UnsupportedCapability` when the binding lacks the Parakeet stream extension
  or the model does not accept it; it never starts a stream without the
  requested cache-aware context. Native begin rejection remains a clear
  `EngineError`. No batch fallback. Public context metadata is now exposed in
  `info.native_stream`, `info.stream_contract`, top-level info aliases, and
  every native feed/final result (flat plus `result.native_stream`):
  - `att_context_right_frames_default`: 3, with
    `att_context_right_frames_default_is_model_default=false` and evidence
    "Engine API default; not model-default evidence";
  - `att_context_right_frames_requested`;
  - `att_context_right_frames_applied` (requested value only after native
    `stream_begin` succeeded; `null` for `-1` model-default requests and all
    failures);
  - `att_context_right_frames_accepted`: `null` (native left/right accepted
    context is not exposed);
  - `model_default_att_context_right_frames`: `null` (not exposed; the
    documented 13 remains a separate documented value, never runtime evidence);
  - `applied_context_source`: `"native"` only when the native begin accepted
    the requested value, otherwise `"unavailable"`;
  - `applied_context_evidence`: explicit provenance (`native begin succeeded...`,
    `model.accepts... was false`, `native begin rejected...`, or model-default
    requested/not exposed);
  - `att_context_reason`/`reason` with explicit values such as
    `applied_native_begin_accepted`,
    `model_does_not_accept_parakeet_stream_extension`,
    `binding_has_no_parakeet_stream_extension`, `native_begin_rejected`,
    `model_default_requested_not_exposed`, or `no_stream_started`.
  Runner coordination keys were sent to `asr-runner`; its existing
  `_native_stream_exposure` reads `att_context_right_frames_applied` and
  `stream_contract.att_context_right_frames_default` directly.
- **F-02 fixed (medium).** Both non-final and final `stream.feed()` calls are
  wrapped. On a terminal native state (`failed`/`finished`) the adapter clears
  `_stream_active`, preserves `_stream_failed`/`_stream_finalized`, and
  re-raises `EngineError` with the state. `start_stream()` can reset and proceed
  immediately; `transcribe()` is available again; `close()` resets the failed
  stream. A pre-native retryable error (state still `active` and no
  `last_status`) keeps the stream active for retry. Fakes now model real
  `idle/active/finished/failed` labels.
- **F-03 fixed (low).** `validate_samples` checks the packed float32 value
  after the required `array('f')` copy and rejects finite float64 values that
  overflow to float32 infinity (`1e300`, `-1e300`, `3.5e38`).
- **F-04 fixed (low).** `_build_info` is inside constructor cleanup; a failure
  there calls `_close_resources()` and marks the engine closed before
  propagating. The fake model's `arch` property raises to test this.
- **F-05 fixed (low).** `_load_binding` now verifies the Python source origin:
  a pre-imported or imported `transcribe_cpp` is accepted only when its
  `__file__` is exactly `<binding_src>/transcribe_cpp/__init__.py`, not merely
  when it reports the same dylib. New fake-package tests cover env restoration,
  sys.path insertion/removal, origin rejection for a pre-imported alternate
  source, reported-library mismatch, and import-failure cleanup. The real
  pinned loader was re-run manually (library load + backend enumeration only):
  origin `.../bindings/python/src/transcribe_cpp/__init__.py`, native 0.4.1,
  commit `8facde6`, library hash verified.
- **F-06 fixed (low).** The report now distinguishes runtime device-registry
  evidence from actual `Model.backend`/`Model.device` placement, which remains
  a coordinator real-run measurement. The build import check proves the dylib
  loads, its version/commit, and that a Metal device is registered; it does not
  load a model and does not itself inspect the Python source package. The
  separate real `_load_binding` smoke check proves the pinned Python source
  origin. Actual model backend/device placement remains for the coordinator.
- **F-07 fixed (low).** The fake stream uses `finished` (not `finalized`) and a
  single `finalize_calls` counter; tests assert the real terminal label.

## Fix round 2 — N-01 non-final snapshot/text-view lifecycle

Review: `review/task-1-fix-1-review.md`, finding N-01. Scope was limited to the
remaining terminal snapshot/text-view lifecycle gap; loader cache nit N-02 and
other residual/minor items were intentionally deferred.

RED evidence after adding the regression tests (backend-only):

```text
python3 -m unittest discover -s spikes/001-transcription/tests \
  -p test_backend.py -v
Ran 59 tests in 1.302s
FAILED (failures=2)
```

The two failures reproduced N-01: a non-final `snapshot()` failure with native
state `failed` left the adapter active, so the next `feed()` did not raise and
`start_stream()` would still say "already active"; a non-final `text()` failure
propagated without the lifecycle-synchronized stage/error path. The
pre-existing final feed/finalize/snapshot paths and batch behavior were
unchanged.

GREEN evidence after the fix:

```text
python3 -m unittest discover -s spikes/001-transcription/tests \
  -p test_backend.py -v
Ran 59 tests in 1.334s
OK

python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 204 tests in 2.441s
OK
```

Disposition:

- **N-01 fixed (medium).** The non-final `feed` branch now keeps
  `stream.feed()`, `stream.snapshot()`, and `_result_payload()`/text-view
  construction inside one staged `try` (`feed` → `snapshot` → `text_views`).
  Any exception calls `_mark_stream_failure(stream)` and re-raises a clear
  `EngineError` naming the stage and native state. Terminal `failed`/`finished`
  states clear `_stream_active` and set `_stream_failed`/`_stream_finalized`;
  an `active` state with no terminal status remains retryable, matching the
  pre-native/Busy behavior. Regression tests cover:
  - non-final snapshot failure (`failed`) → subsequent feed rejected, restart
    resets and proceeds;
  - non-final text-view failure (`failed`) → restart resets and proceeds;
  - non-final snapshot failure while native state remains `active` → next feed
    succeeds (no over-eager poisoning);
  - close after non-final snapshot failure resets the failed stream.
- No pin/ABI/library hash change; `build_engine.py --verify-only` remains green
  with the reviewed artifact.

## Self-review and limitations

Self-review performed against SPEC.md and preflight resolutions:

- Confirmed the official headers’ stream lifecycle, commit-policy enum,
  `stream_text` pointer lifetime, feed/final/flush rules, timings
  zero-means-absent contract, `att_context_right` sentinel/`-1` semantics, and
  Parakeet extension kind.
- Checked the actual pinned multilingual model docs/manifest: Nemotron 3.5
  supports `en-US`, `es-US`, `es-ES`, etc.; its cache-aware menu is
  `{0,3,6,13}`; auto mode is an empty hint that selects `prompt.auto_id`; no
  hidden default language is injected.
- Corrected an earlier draft assumption that the cached model was the
  English-only `nemotron-speech-streaming-en-0.6b` (menu `{0,1,6,13}`). The
  implementation/report/lock now use the actual multilingual Nemotron 3.5
  contract; runner was notified.
- Verified empty final flush, final authoritative text, reset between streams,
  close-after-error, and no-batch-fallback behavior with fakes.
- Fix round 1: verified fail-closed Parakeet context handling, public
  requested/applied/accepted/default context metadata, terminal feed-error
  lifecycle recovery, float32 overflow rejection, constructor info-build
  cleanup, Python binding source-origin enforcement, env/sys.path restoration,
  and real-binding terminal state labels.
- Fix round 2: verified the non-final snapshot/text-view error path invokes
  the same terminal-state synchronizer, with restart/retry/close regressions;
  deferred N-02/loader-cache and residual minors as instructed.
- Verified the source-pin guard rejects wrong revision, dirty tree, changed
  ggml tree/sha, changed patch tree/file, lock drift, and tampered library bytes
  in temporary directories.
- Verified the official binding loads the exact locked library and enumerates
  the Metal device without loading a model.

Remaining limitations/concerns:

1. **No real model was loaded or inferred in this slice.** This follows the
   no-timed-inference/coordinator-serialization instruction. Consequently the
   real model’s capability values, `supports_language_detect`, streaming
   `snapshot()` timing behavior, extension/value acceptance, and the private
   `transcribe_get_timings` load-ms probe are not independently exercised here.
   The adapter fails closed if the real model rejects the Parakeet stream
   extension or the requested context value.
2. **Accepted/default native context is not exposed.** The pinned binding has
   no accessor for the selected `(left,right)` or model default. `Engine`
   records the requested value, the applied value only after native
   `stream_begin` accepted it, and leaves accepted/model-default null with
   explicit evidence strings. The API default 3 is not model-default evidence.
   Do not treat the nominal context as measured latency.
3. **`decode_ms` for native streams may be null.** The C timings contract is
   batch-run-scoped; zero/unknown is reported as null rather than a fabricated
   zero. Runner call-wall timing remains separate.
4. **Clean rebuilds may change the Mach-O artifact hash.** The lock deliberately
   pins the reviewed artifact hash; a rebuild that changes it fails
   `build_engine.py`/`Engine` until the lock is re-reviewed and updated. This
   is an integrity choice, not a reproducibility claim.
5. **Raw bytes PCM is rejected.** The adapter accepts numeric 1-D sequences and
   float buffers (the runner supplies `array('d')`), but rejects ambiguous
   `bytes`/`bytearray` rather than guessing int16 vs float32.
6. **One native library per process.** The official binding is imported once
   against the resolved library; a second engine with a different library path
   fails clearly rather than silently reusing the first native library. A
   pre-imported `transcribe_cpp` is accepted only from the pinned source
   directory, not merely because it reports the same dylib.
7. **Native streaming with this adapter is Parakeet-cache-aware only.** A
   streaming model that does not accept the Parakeet stream extension fails
   closed instead of running at an unlabelled family default. This is
   intentional for the spike’s R=3/R=13 cache-aware comparison.
8. Owner-observed Nemotron streaming behavior (English+Spanish, mid-sentence
   switching) is recorded in `OWNER-OBSERVATIONS.md` as owner observation, not
   by this slice; no inference result from this work is claimed as an
   independent measurement.

## Coordinator handoff

1. Build/verify: `python3 spikes/001-transcription/tools/build_engine.py --import-check`
   then `... --verify-only`.
2. Pass the cached model path to `backend.Engine`; run real batch/native-stream
   measurements only when CPU/GPU work is idle. The adapter itself does not
   load a model until `Engine(...)` is constructed.
3. Use `att_context_right_frames=3` for the specified native arm and label
   `13` only as an explicit max-accuracy control. If the real model/binding
   rejects the Parakeet extension or value, `start_stream` raises
   `UnsupportedCapability`/`EngineError`; record that as an error trial, never
   as an unlabelled default-context run.
4. Preserve `info.native_stream`/`info.stream_contract` and per-result context
   fields (`att_context_right_frames_requested`,
   `att_context_right_frames_applied`, `att_context_right_frames_accepted`,
   `model_default_att_context_right_frames`, `applied_context_source`,
   `att_context_reason`). `applied_context_source="native"` means native begin
   accepted the requested value; accepted left/right and model default remain
   null unless a future binding exposes them.
5. Preserve the engine-reported backend/load evidence and separately measured
   runner call wall time; do not describe native lookahead as measured latency.
