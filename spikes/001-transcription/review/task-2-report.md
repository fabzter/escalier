# Task 2 — replay runner, policies and metrics

Status: **DONE_WITH_CONCERNS**

Implemented `run.py`, `policy.py`, `metrics.py` and the three owned deterministic test
modules. No model inference, timed experiment, GUI/capture action or commit was run.
The real-model arms remain for the coordinator after workers are idle.

## Changed files

- `spikes/001-transcription/run.py`
- `spikes/001-transcription/policy.py`
- `spikes/001-transcription/metrics.py`
- `spikes/001-transcription/tests/test_policy.py`
- `spikes/001-transcription/tests/test_metrics.py`
- `spikes/001-transcription/tests/test_runner.py`
- `spikes/001-transcription/review/task-2-report.md`

No sibling-owned files were edited. `run.py` consumes the fixture slice's strict
`fixtures/manifest_tools.py` validator and the manifest it produces.

## Red / green evidence

### Red (before implementation)

Command (repository root):

```text
python3 -m unittest discover -s spikes/001-transcription/tests -v
```

Observed:

```text
ERROR: test_metrics (unittest.loader._FailedTest.test_metrics)
ModuleNotFoundError: No module named 'metrics'
ERROR: test_policy (unittest.loader._FailedTest.test_policy)
ModuleNotFoundError: No module named 'policy'
ERROR: test_runner (unittest.loader._FailedTest.test_runner)
ModuleNotFoundError: No module named 'run'
Ran 43 tests in 0.117s
FAILED (errors=3)
```

(The other 40 tests were sibling fixture/public-audit suites already present.)

### Green (initial implementation snapshot)

Targeted suites:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_policy.py' -v
Ran 19 tests ... OK

python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_metrics.py' -v
Ran 20 tests ... OK

python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_runner.py' -v
Ran 36 tests ... OK
```

Root discovery command from SPEC.md:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 180 tests in 2.432s
OK
```

Other checks:

```text
python3 -m py_compile spikes/001-transcription/run.py \
  spikes/001-transcription/policy.py spikes/001-transcription/metrics.py
# exit 0, "py_compile OK"

python3 spikes/001-transcription/run.py --help
# parses; documents model/library/manifest/arm/output/repeats/warmup/fixture,
# language + asr-language, partial interval, max window, feed cadence,
# right context, commit policy, agreement, clock mode, window mode, threads,
# CPU, overwrite and precomputed hashes.
```

Real curated manifest consumed without inference:

```text
python3 - <<'PY'
import sys; sys.path.insert(0, 'spikes/001-transcription')
import run
m = run.load_manifest(run.SPIKE_ROOT / 'fixtures' / 'manifest.json')
print(len(m.fixtures), [f.id for f in m.fixtures])
PY
# 4 ['fleurs-en-us-10233995782544396174', 'fleurs-es-419-10149016836336603986',
#    'derived-en-us-10233995782544396174-repeat2', 'derived-en-us-es-419-switch']
```

The mixed EN→ES fixture loads with `language="mixed"`, `asr_language="auto"`, two
`derived_assembly` segments, 9.96 s.

## Review round 1 fixes

Review source: `review/task-2-review.md` (I-1 plus M-1…M-6). Coordinator also added
residual F6 (default-fixture composition limitation) as documentation only.

### Red for the new review assertions

```text
python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_runner.py' -v
Ran 44 tests in 0.081s
FAILED (failures=3, errors=6)
```

Failures/errors were the intended new assertions: missing `context_metadata`, missing
`_feed_native_final`, unlabelled R=13-vs-R=3 default, zero/negative `decode_ms` counted
as known, and the CLI default still 13.

### Findings status

| ID | Status | Resolution |
|---|---|---|
| **I-1** | **Fixed** | Native default is now **R=3** in `ReplayConfig` and CLI. Per-arm context metadata (`context_label`, requested/native-default/documented-offline/documented-model-default, `stream_latency_setting`, `context_confound`, derived `limitation`) is recorded in every trial `replay.context`, effective settings, and document replay. R=13 native remains possible only as `native_R=13_explicit_control`, never the default. The limitation is derived from effective settings, not hardcoded. |
| **M-1** | **Deferred with wording fixed** | Replay origin is still `t0`, one sample period before first-sample availability. `replay_origin_note` and metric definitions now state the 0.0625 ms/16 kHz conservative bias and retain the convention for metric stability. No metric values changed. |
| **M-2** | **Fixed** | Runner maps native `decode_ms <= 0`, nonfinite and absent to null; metric accounting counts them as unknown, never known-zero. Tests cover 0.0, negative and NaN. |
| **M-3** | **Fixed (docs)** | `load_manifest` docstring and `--max-window-ms` help now state that the shared validator fully validates every entry, including its own ≤20 s cap, before selection; `max_window_ms` can be stricter but cannot relax that cap. No validator duplication or fixture API change. |
| **M-4** | **Fixed** | `ReplayRunner._engine_info` now delegates to the module-level `_read_engine_info`; one implementation. |
| **M-5** | **Fixed where reachable** | Added a fatal-native `execute_plan` test over two fixtures/two repeats asserting later trials are `skipped`, `timings=None`, and state-poisoning is explicit. Extracted `_feed_native_final` and added a direct empty-final-flush contract test; the branch remains defensive/unreachable under the normal tick schedule. |
| **M-6** | **Deferred** | `run.py` remains a single module (~2.4k lines). Sections are coherent; no risky split during review fixes. Recorded for later cleanup. |
| **F6** | **Fixed (metadata)** | `DEFAULT_LIMITATIONS` now states that default fixtures mix natural FLEURS and derived/synthetic assemblies, endpoint splits derived assemblies at oracle segment boundaries, and within-call/mid-sentence switching is not tested. No schema/fixture behavior change. |

### Native context evidence separation

`engine.info.native_stream`/`stream_contract` is consumed defensively:

- `adapter_default` from `stream_contract.att_context_right_frames_default` (expected
  3), with `adapter_default_is_model_default` and evidence text.
- `applied` only from explicit engine-reported applied fields
  (`att_context_right_frames_applied` or alias). Requested is never substituted.
- `accepted` from the engine-reported accepted field, normally null because the native
  accepted value is unexposed; null is preserved, not backfilled.
- `documented_model_default=13` is recorded as documentation, separate from runtime
  evidence; `exposed_model_default` is null unless the engine exposes it.
- `att_context_reason`, `applied_context_source` and `accepted_evidence` are retained.
- `applied_context_status` is `engine_reported` or `unavailable_not_inferred`.
- Requested-vs-adapter-default and requested-vs-documented-model-default booleans are
  recorded.

Coordinated with `asr-engine` (Task 1 F01), which implemented these public fields on
`engine.info`, `engine.info.stream_contract`, `engine.info.native_stream`, top-level
aliases and stream results: `att_context_right_frames_default` (API default 3, flagged
not-model-default), `_requested`, `_applied` (int or null; requested after native begin
succeeded), `_accepted` (null; native accepted value unexposed),
`applied_context_source` (`native`/`unavailable`), `att_context_reason`,
`model_default_att_context_right_frames` (null; unexposed), plus
`att_context_right_frames_default_is_model_default=false` and evidence text. The runner
records `applied` separately from `accepted`, keeps the documented 13 constant
separate, and never substitutes requested. Defensive aliases and nested contract
fallbacks are supported. Result-level context extras are retained in `native_extra`.

### Verification snapshot after fixes

```text
python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_policy.py'
Ran 19 tests in 0.001s
OK

python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_metrics.py'
Ran 20 tests in 0.001s
OK

python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_runner.py'
Ran 44 tests in 0.067s
OK

python3 -m py_compile spikes/001-transcription/run.py \
  spikes/001-transcription/policy.py spikes/001-transcription/metrics.py
# exit 0, compile OK

python3 spikes/001-transcription/run.py --help
# native comparison default R=3; R=13 explicit control; adapter default 3;
# documented model default 13
```

Root discovery while sibling Task 1 F01 was mid-edit:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 200 tests in 2.402s
FAILED (failures=8, errors=6)
```

All 14 failures/errors were in sibling `tests/test_backend.py`, not this slice. Re-run
after those Task 1 edits settled:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 200 tests in 2.772s
OK
```

The earlier 180-test root snapshot also passed; current root discovery is green. A
subsequent re-run after a sibling test addition observed `Ran 201 tests in 2.482s / OK`
— root counts are dated snapshots and move as sibling tests land.

## Implementation summary

### Arms (`run.ReplayRunner`)

- `endpoint`: batch-decodes each oracle fixture segment when its end arrives. For a
  one-segment fixture this is one full-clip decode; a derived assembly is decoded
  segment-by-segment with no cross-segment conditioning. Boundaries are oracle
  metadata, never a tested VAD.
- `hybrid`: fixed-start growing-prefix batch decoding with runner word-level LA-2.
  Before each call `prefix_end = min(selected_tick_sample, arrived_samples)`, frozen
  for the call. A slow call coalesces missed ticks to the latest eligible tick; the
  skipped ticks, selected/completed tick, frozen horizon, queue lag and backlog are
  recorded. At audio end pending partials are bypassed and the full arrived clip is
  finalized.
- `native-stream`: genuine `Engine.start_stream` + `Engine.feed`. Every arrived sample
  is fed exactly once in order. Slow feeds may coalesce caller-cadence ticks for
  display bookkeeping but never drop audio; remaining audio is fed with
  `final=True` (or an empty final flush when everything was already fed).
  `start_stream` is called once per trial, resetting stream state. `close()` is
  coordinator/CLI-owned and called once at process end.

Real replay uses `time.monotonic` and sleeps to audio-clock deadlines. Only arrived
audio is passed to the engine. Fake clocks and fake engines drive deterministic tests;
a fake-clock trial writes only `timings.simulated` and leaves `timings.measured` null.
The CLI refuses `--clock-mode fake` because a real backend cannot be paced coherently
without a fake engine; fake mode is an API/test harness facility.

### Stable evidence

`policy.StablePrefixPolicy` compares NFC/casefolded whitespace words with Unicode
punctuation removed and accents/ñ preserved. Words enter append-only stable history
only when they are in the common prefix of two consecutive hypotheses. A hypothesis
that does not begin with confirmed stable words produces an explicit
`stable_prefix_disagreement` record and does not rewrite history. Final text is
authoritative; if it does not begin with stable history a `final_correction` record is
emitted and history is retained unchanged.

`policy.NativeCommitTracker` tracks native `committed_text` separately using raw
whitespace-canonicalized character prefixes (native units are not assumed to be
runner words). Rewinds/disagreements and final corrections are explicit records.
Native result extras such as revisions/commit timing/buffer state are retained in
`native_extra` when exposed.

### Replay/metric definitions

- `first_partial_ms`: first nonempty partial result arrival (engine call return)
  relative to replay start `t0`, which is one sample period before the first fixture
  sample becomes available. These fields are conservatively high by 1/sample_rate
  (0.0625 ms at 16 kHz) versus a literal first-sample-availability origin; the
  convention is retained and stated in result definitions.
- `first_stable_ms`: first nonempty runner stable text (hybrid) or native
  `committed_text` (native stream) arrival relative to `t0`. Endpoint arm has no
  partial/stable results by construction; native reports null when committed text is
  not exposed before final.
- `final_after_audio_end_ms`: final call return minus fixture audio-end arrival.
- `call_wall_ms`: runner clock elapsed around one engine call; includes
  validation/transport/native compute, not pure GPU decode. Per-call plus totals/max.
- `queue_lag_ms`: call start minus selected scheduled tick/segment arrival.
- `frozen_prefix_samples` / `frozen_horizon_ms`: audio horizon frozen before the call.
- `arrived_samples` / `arrived_horizon_ms` / `backlog_samples`: audio available at
  call start beyond the frozen prefix.
- `arrived_samples_after` / `backlog_samples_after`: backlog after a slow call; for
  native this proves audio was waiting, not dropped.
- `coalesced_ticks`: scheduled ticks superseded after a slow call; recorded on the
  event that caused the miss or on finalization.
- `native_decode_ms`: native null-able decode component, with known/unknown counts.
  Zero, negative, nonfinite and absent values are unknown and never zero-filled.
- `word_end_latency_ms`: always null/unsupported. No independent gold word timings
  exist; model token end times are not truth.
- WER normalizer v1: NFC, casefold, punctuation→space, whitespace collapse, accents/ñ
  retained, digits unchanged, no number expansion. Not a vendor normalizer.
- WER: `(S+D+I)/reference_token_count`; empty reference → null WER with counts
  preserved. Deterministic Levenshtein tie order: match, substitution, deletion,
  insertion. Full operation alignment retained.
- Aggregates: micro S/D/I over summed reference count plus macro mean labelled as
  context; per-fixture micro records; warmup excluded.
- Fake-clock timing values are labelled `fake_clock_simulated` and populate only
  `simulated`; `measured` remains null.

### Integrity and provenance

- Manifest validation is delegated to `fixtures/manifest_tools.py` (strict schema,
  duplicate keys/IDs/paths, traversal/escape/symlink refusal, hashes, WAV PCM16 mono
  16 kHz duration/layout, ordered nonoverlapping oracle segments, UTF-8 reference,
  default ≤20 s). **Every entry is fully validated before selection**, including the
  shared validator's own ≤20 s cap. `run.py` then selects fixtures and applies the
  configured max-window check: selected clips above `--max-window-ms` raise
  `UnsupportedWindowError`; this option can be stricter than the shared cap but cannot
  relax it. Rolling windows are explicitly rejected (CLI choices only `fixed-start`).
- Default-result limitations state that the fixture set mixes natural and
  derived/synthetic material, and that endpoint derives are split at oracle segment
  boundaries and do not test within-call/mid-sentence language switching.
- Results include schema version, UTC timestamp, unique trial IDs, sanitized
  invocation/effective settings, Git commit/branch/dirty-tracked flag, SHA-256
  fingerprints for `run.py`, `policy.py`, `metrics.py`, `backend.py`,
  `engine.lock.json` and `fixtures/manifest_tools.py`, model/library basename + hash +
  size (no absolute paths), sanitized engine info, a compact build record from
  `engine.lock.json` (lock hash, engine name, artifact hash, backend import check,
  build/runtime/source-verification metadata), host/Python metadata without
  hostname/user/home, load/constructor timing, warmup trials, per-trial raw events,
  raw/normalized text, tokens, WER and timing blocks, metric definitions and
  limitations.
- Nonfinite native metadata becomes null; tokens with nonfinite times are nulled;
  transcript text is preserved. Results are strict JSON (`allow_nan=False`) written
  atomically via same-directory temp file + `os.replace`, with collision refusal
  unless explicitly allowed.
- Engine capability flags are rejected only when explicitly reported false; native
  start/feed errors become recorded error trials, never silent batch fallback. A
  failed native trial marks remaining trials skipped because stream state may be
  poisoned. Batch trial errors are recorded and the run continues.

## CLI examples

Replace bracketed placeholders with the coordinator's cached/build paths; no private
absolute paths are recorded in the report or result document.

Parakeet v3 Q8_0 — endpoint arm:

```bash
python3 spikes/001-transcription/run.py \
  --model <cached-parakeet-v3-q8_0-model> \
  --library <built-libtranscribe-helper> \
  --manifest spikes/001-transcription/fixtures/manifest.json \
  --arm endpoint \
  --output spikes/001-transcription/results/parakeet-v3-endpoint.json \
  --repeats 2 --warmup 1 --clock-mode real
```

Parakeet v3 Q8_0 — hybrid LA-2 arm:

```bash
python3 spikes/001-transcription/run.py \
  --model <cached-parakeet-v3-q8_0-model> \
  --library <built-libtranscribe-helper> \
  --manifest spikes/001-transcription/fixtures/manifest.json \
  --arm hybrid \
  --partial-interval-ms 500 --max-window-ms 20000 \
  --output spikes/001-transcription/results/parakeet-v3-hybrid.json \
  --repeats 2 --warmup 1 --clock-mode real
```

Nemotron 3.5 streaming 0.6b multilingual — endpoint arm:

```bash
python3 spikes/001-transcription/run.py \
  --model <cached-nemotron-3.5-streaming-0.6b-model> \
  --library <built-libtranscribe-helper> \
  --manifest spikes/001-transcription/fixtures/manifest.json \
  --arm endpoint \
  --output spikes/001-transcription/results/nemotron-3.5-endpoint.json \
  --repeats 2 --warmup 1 --clock-mode real
```

Nemotron 3.5 streaming 0.6b multilingual — native-stream arm:

```bash
python3 spikes/001-transcription/run.py \
  --model <cached-nemotron-3.5-streaming-0.6b-model> \
  --library <built-libtranscribe-helper> \
  --manifest spikes/001-transcription/fixtures/manifest.json \
  --arm native-stream \
  --feed-chunk-ms 1120 --right-context-frames 3 \
  --commit-policy stable-prefix --agreement-n 2 \
  --output spikes/001-transcription/results/nemotron-3.5-native-stream.json \
  --repeats 2 --warmup 1 --clock-mode real
```

Language selection comes from each fixture's `asr_language` (`en-US`, `es-US`, or the
`auto` sentinel on the mixed EN→ES fixture). The runner passes it unchanged to the
engine; it never forces a first-language prompt and never reloads the model to change
it. Use `--fixture <id>` to select a subset, `--asr-language <tag>` only for an
explicit global prompt override, and `--model-sha256`/`--library-sha256` to avoid
re-hashing large files.

The native example above uses the binding comparison default **R=3**. An explicitly
labelled control may request `--right-context-frames 13`; results then carry
`context_label: native_R=13_explicit_control` and must not be presented as the
R=3-vs-offline-R=13 comparison. Applied context is always engine-reported only.

## Self-review and concerns

1. **Shared validator dependency.** `run.py` imports
   `fixtures/manifest_tools.py` by path instead of duplicating strict schema rules. It
   is green now and accepts the additive `language="mixed"` / `asr_language="auto"`
   extension, but its API/behavior is owned by the fixture slice. If that file moves
   or its `load_manifest(path, spike_root)` shape changes, the runner must be updated.
2. **No runtime adapter exercise.** Per instructions, no model inference was run, so
   SPEC field names (`committed_text`, `tentative_text`, `display_text`,
   `final_text`, `decode_ms`, token rows) are consumed from the contract, not verified
   against live native output. Missing fields degrade to null/`result.text` with notes;
   a genuinely different adapter shape would show up as null native evidence rather
   than invented values. Coordinator real runs remain the integration check.
3. **Endpoint multi-segment choice.** A derived assembly is decoded per oracle
   segment (no cross-segment conditioning) and segment texts are joined for WER.
   One-segment fixtures are a single full-clip decode. This is recorded as
   `endpoint_mode: per_oracle_segment_batch`; if review expects one whole-fixture
   decode instead, this is a small, deliberate change.
4. **Native context wording.** Binding default is now **native R=3**; the adapter API
   default is 3 and the documented model default is 13 (pinned menu `{0,3,6,13}` per
   engine evidence). Native R=13 is explicitly labelled as a control and never the
   default. Per-trial `replay.context` carries the context label, requested/default/
   documented values, `stream_latency_setting`, confound text and a derived limitation.
   Applied context is recorded only from explicit engine-reported `applied` fields;
   when unexposed, `applied`/`accepted` stay null and `applied_context_status` is
   `unavailable_not_inferred`. The request is never substituted. Task 1 F01 keys were
   confirmed by the adapter worker and are covered by tests.
5. **CLI fake clock.** The CLI intentionally rejects `--clock-mode fake`; deterministic
   fake-clock execution is available via the `ReplayRunner` API used by tests. This
   avoids pretending a real native backend can be paced with a fake clock.
6. **`--asr-language` is a global prompt override**, not a per-ID mapping. Per-fixture
   defaults come from the manifest `asr_language`; mixed/auto is preserved.
7. **Empty-reference WER** is defined and tested in `metrics`, but the curated manifest
   validator rejects empty reference files. Direct/manifest-derived empty references
   are still handled with null WER and preserved S/D/I.
8. **No timed numbers are claimed here.** The owned 83 deterministic
   fake-engine/fake-clock tests and root discovery (200 tests) are green; this is not
   inference, accuracy or live-latency evidence. Real arms must be run by the
   coordinator after builders/workers are idle. Native applied-context keys are now
   implemented by Task 1 F01 and covered; `accepted` remains null when the adapter
   cannot expose it.
9. **M-6 deferred:** `run.py` remains one large module. Sections are coherent and a
   risky split during review fixes was avoided; a later cleanup can extract
   result/CLI metadata helpers.
10. **M-1 deferred with documented wording:** replay origin remains one sample period
    before first-sample availability; first-partial/stable values are 0.0625 ms high at
    16 kHz by convention, recorded in `replay_origin_note` and metric definitions.

No commits, staging, GitHub actions, subagents, model downloads, host installs, GUI or
capture permissions were used.
