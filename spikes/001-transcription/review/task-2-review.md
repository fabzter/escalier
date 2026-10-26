# Task 2 — replay runner, policies and metrics: spec + quality review

Base: `7dfcfd6628d0660c606bbb7914fa31e053365d22`
Head: `e50b023b7e5118c0800d3b45e883d62cc7cc7d4e`
Reviewed: `spikes/001-transcription/.tools/reviews/task-2.diff` (full 4,859-line diff, once), `spikes/001-transcription/.tools/reviews/task-2-compat.diff`, task brief, implementer report, SPEC replay/metric contracts, and preflight resolutions. Read-only review; no implementation, index, or commit changes. Full suite was not re-run (coordinator evidence accepted); one focused probe is recorded below.

## Spec Compliance

**Verdict: ❌ Issues found** — one Important spec mismatch (native-stream right-context default and the published context-confound statement); all other checked requirements are compliant or explicitly unverifiable without inference.

- ❌ **Native-stream right-context default and context-confound text contradict the binding contract.** See **I-1**. `ReplayConfig.right_context_frames` defaults to `13` (`spikes/001-transcription/run.py:430`), the CLI default is `13` (`run.py:2042`), the native CLI example and report use `13` (`spikes/001-transcription/review/task-2-report.md:253,285-287`), and tests pin `13` (`spikes/001-transcription/tests/test_runner.py:192,387,877`). The authoritative SPEC says the nominal native setting is R=3 and offline is R=13 (`spikes/001-transcription/SPEC.md:46`); the README states native-stream is R=3 (`spikes/001-transcription/README.md:18`); the preflight resolution states native R=3 vs offline R=13 is the explicit confound (`spikes/001-transcription/review/preflight-resolutions.md:18`); and the shared backend/API default is `3` (`spikes/001-transcription/backend.py:72`). `DEFAULT_LIMITATIONS` then says native-vs-offline R=13 remains a lookahead and architecture confound (`run.py:1582`), and `_native_stream_exposure` says native context is distinct from nominal offline R=13 (`run.py:1266-1269`). If native runs at 13, those statements are false; if it should run at 3, the runner and examples do not do it.
- ✅ **Frozen arrival horizon / no future audio.** `_arrived` only counts elapsed samples (`run.py:642-645`), and hybrid freezes `prefix = min(selected_tick_sample, arrived)` before the call (`run.py:808-812`). The native feed path takes `fixture.samples[fed:arrived]` and never advances `fed` beyond arrived (`run.py:1059-1069`); the final feed uses only `remaining = fixture.samples[fed:arrived]` (`run.py:1133-1142`). Tests assert the invariant and engine-call sample bounds (`tests/test_runner.py:204-247`).
- ✅ **Coalescing, final priority, no duplicated native samples.** Hybrid records skipped ticks, selects the latest eligible tick, and finalizes full arrived audio after slow calls (`run.py:660-683,794-872`). Native coalesces display ticks but feeds every arrived sample exactly once; the test compares the engine's fed history to the full fixture (`tests/test_runner.py:371-407`). Finalization after a very slow partial is tested (`tests/test_runner.py:250-278`), and stream state resets per trial (`tests/test_runner.py:409-432`).
- ✅ **Fake-vs-real timing, queue, and missing evidence.** Real/fake values are split into `measured`/`simulated` (`metrics.py:306-470`), queue lag is call start minus scheduled tick/segment arrival (`run.py:685-715`), and missing final/first-partial/first-stable/native-decode evidence has explicit null/status fields. Tests cover fake-only, real-only, endpoint, native-committed and missing-final cases (`tests/test_metrics.py:194-315`).
- ✅ **Normalization and micro WER.** Normalizer v1, deterministic Levenshtein tie-breaking, S/D/I counts, null empty-reference WER with preserved counts, and micro aggregation are implemented (`metrics.py:50-258`). Tests cover punctuation/case/accents, tie-breaking, empty references, operation alignment, and micro aggregation (`tests/test_metrics.py:17-134`).
- ✅ **Stable history vs native committed text.** Runner word-level LA-2 is append-only with explicit `stable_prefix_disagreement` and `final_correction` records (`policy.py:104-260`); native committed text is tracked separately by whitespace-canonicalized character prefix (`policy.py:262-333`). Tests pin two-hypothesis agreement, conflict retention, final correction, native append-only behavior, rewinds, and native final correction (`tests/test_policy.py:47-181`).
- ✅ **Fixture provenance, fingerprints, strict atomic JSON.** Fixture identities include relative WAV/reference paths, hashes, source/conversion metadata and oracle segments (`run.py:130-146`); results include manifest/source/engine/build/model/library/host/git metadata (`run.py:1637-1668,1721-1852`), sanitized nonfinite/token data (`run.py:353-393,1483-1500`), and atomic same-directory writes with collision refusal and `allow_nan=False` (`run.py:1671-1705`). Tests cover atomic collision/overwrite, nonfinite JSON, home redaction, metadata aggregates, and token/native-extra sanitization (`tests/test_runner.py:716-833`). Context caveat is I-1.
- ✅ **No forbidden operations in the reviewed code.** The runner is stdlib-only, imports the heavy backend lazily, performs no downloads/inference, and the compat addendum changes only a synthetic test fixture's conversion metadata and the report count.
- ⚠️ **Cannot verify from the diff:** actual native result field shapes and accepted/model-default context at runtime. No inference is permitted in this review. I checked the shared interfaces instead: `backend.Engine` exposes nullable `decode_ms` (zero/nonpositive becomes null: `backend.py:413-420`), native `committed_text`/`tentative_text`/`display_text`/`final_text` (`backend.py:983-994`), and `info.native_stream` reports accepted/model-default context as unavailable (`backend.py:658-663`). The coordinator's real-model runs remain the integration check; results correctly stay null rather than inferring native context.

### Compatibility addendum

`task-2-compat.diff` only:
- adds `entry["conversion"] = {"tool": "test assembly v1"}` to the synthetic mixed-language manifest test (`tests/test_runner.py:691`), which is required by the sibling validator's derived-assembly rule; and
- updates the report's suite count to 180.

No runner/policy/metrics source changes. Focused probe `python3 -m unittest spikes/001-transcription/tests/test_runner.py -k test_mixed_language_and_auto_hint_are_accepted` passed (1 test, 0.006s).

## Strengths

- Deterministic doubles are used for both clocks and engines; the tests exercise real scheduling/coalescing/finalization behavior rather than tautological mocks (`tests/test_runner.py:204-432`).
- The hybrid scheduler is careful: prefix frozen before the call, coalesced ticks recorded on the causing event, finalization bypasses pending partials, and `pending_coalesced` is attached to the final event (`run.py:794-918`).
- Native streaming is correctly separated from batch: one `start_stream` per trial, audio fed once in order, final flush with remaining audio, and fatal-stream-state abort rather than silent batch fallback (`run.py:1038-1180,1523-1551`).
- Policy semantics are explicit and auditable: append-only stable history, raw hypothesis retention, separate native commit tracking, explicit conflicts and final corrections (`policy.py`; `tests/test_policy.py`).
- WER and timing records are unusually honest about missing evidence: word-end latency is always null/unsupported, fake timings are separated, native decode zero/unknown is not intended to become a measured zero, and empty-reference WER is null with counts preserved (`metrics.py:38-42,209-258,457-469`).
- Result serialization is privacy-aware and fail-closed: home-path redaction, basename-only external paths, nonfinite sanitization, strict JSON, atomic replace and collision checks (`run.py:353-393,1637-1705`).
- Shared manifest validation is reused rather than duplicated, and the runner adds selection plus the configured max-window rejection (`run.py:212-306`).

## Issues

### Critical (Must Fix)

None.

### Important (Should Fix)

#### I-1 — Native-stream context default/confound is not the specified comparison

- **Locations:** `spikes/001-transcription/run.py:430` (default `13`), `run.py:2042` (argparse default `13`), `run.py:1582` (limitation text), `run.py:1266-1269` (context note), `run.py:1252-1259` (context exposure misses backend `stream_contract` default); examples/tests at `spikes/001-transcription/review/task-2-report.md:253,285-287` and `spikes/001-transcription/tests/test_runner.py:192,387,877`.
- **Contradicted by:** `spikes/001-transcription/SPEC.md:46` (“Nominal native R=3 and offline R=13…”), `spikes/001-transcription/README.md:18` (native R=3), `spikes/001-transcription/review/preflight-resolutions.md:18` (native R=3 vs offline R=13), and the shared backend default `spikes/001-transcription/backend.py:72` (`_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES = 3`).
- **What is wrong:** The native arm will run at R=13 by default, so the specified R=3 native condition is never measured. The default limitation says “Native-vs-offline R=13 remains both a lookahead and architecture confound”; with native R=13 and offline endpoint R=13, there is no R=13-vs-R=13 lookahead difference to attribute. `_native_stream_exposure` only reads `native_stream`/top-level keys (`run.py:1252-1259`) and reports `model_default=None`/`source=not_exposed_by_engine`, while the backend’s `stream_contract` exposes the adapter default 3 (`backend.py:713-720`; it survives only inside the raw `engine.info` block). The dedicated context block therefore loses the shared default and cannot show the requested-13-vs-default-3 discrepancy.
- **Why it matters:** This is the central experiment-design/claim constraint. Running the documented native example would produce evidence for a different configuration and publish an untrue context-confound explanation. No real run is claimed yet, so fix before the coordinator runs measured native arms.
- **Minimal fix:** Default `ReplayConfig.right_context_frames` and `--right-context-frames` to `3`; update the native CLI example and tests to 3; record an explicit per-arm context label (native R=3, endpoint offline R=13) and `stream_latency_setting`; make the limitation text derive from the effective settings; if an R=13 native control is desired, add it as an explicitly labelled control run rather than the default. Optionally surface `stream_contract.att_context_right_frames_default` (3) in the results so the requested-vs-default difference is visible.

### Minor (Nice to Have)

#### M-1 — Replay-start definition is one sample before “first fixture sample arrival”

`metrics.py:15-17` and `metrics.py:510` define replay start as the arrival of the first fixture sample, but `_arrived` makes sample 0 available at `t0 + 1/sample_rate` (`run.py:642-645`), and the recorded arrival model says exactly that (`run.py:1359-1361`). Thus the code's origin is 0.0625 ms before the first sample at 16 kHz, so `first_partial_ms`/`first_stable_ms` are 0.0625 ms larger than the stated first-sample-relative definition. Fix the definition wording, or subtract `1/sample_rate` from those replay-relative fields (or define `t0` at the first sample and adjust `_arrived`). `final_after_audio_end_ms` is unaffected.

#### M-2 — Native `decode_ms == 0.0` is counted as a known measurement by the runner

`metrics.py:387-395` treats `0.0` as a known native decode value, while `run.py:776` preserves it via `_finite_or_none`; SPEC says native timing values of zero mean unknown (`SPEC.md:19`). The pinned backend already maps zero/nonpositive to null (`backend.py:413-420`), so real runs are unaffected, but a fake/custom backend returning 0 would produce a fabricated “known zero.” Defensively map `<= 0` to null in the runner’s native decode accounting, or add a test pinning the backend guarantee.

#### M-3 — `load_manifest` docstring promises selection-scoped long-clip tolerance that the shared validator does not provide

`run.py:221-224` says an unselected longer curated clip does not make a filtered run fail, but `run.py:234` delegates validation to `fixtures/manifest_tools.py`, whose `_validate_fixture` rejects every fixture above 20 s before `only_ids` selection (`fixtures/manifest_tools.py:338-342`). Consequently `--fixture short` still fails on a manifest containing a 25 s clip, and `--max-window-ms > 20000` cannot make it runnable. The current curated manifest is unaffected. Reword the docstring/help or coordinate selection-aware validation with the fixture owner; do not duplicate the validator in `run.py`.

#### M-4 — Duplicate engine-info helper

`ReplayRunner._engine_info` (`run.py:1237-1242`) and module-level `_read_engine_info` (`run.py:1856-1861`) implement the same info-property/error/redaction logic. Consolidate to one helper or delegate the method to the module function.

#### M-5 — `execute_plan` abort/skip path and empty final-flush branch lack focused tests

`execute_plan` marks later trials `skipped` after a fatal native-stream error (`run.py:1523-1551`), but the only native-failure test checks the error trial's `fatal_stream_state` flag (`tests/test_runner.py:450-457`); no test asserts that subsequent fixtures/repeats become `skipped` with `timings=None`. The empty `feed_final_flush` branch (`run.py:1136-1138`) is also untested, though it appears unreachable under the normal tick schedule. Add a focused fake-stream failure over two fixtures (or two repeats) and, if the empty flush is intended as a defensive contract path, a direct test for it.

#### M-6 — `run.py` is large for a single new module (structure note, not blocking)

`run.py` is 2,250 new lines combining manifest consumption, replay scheduling, arm implementations, evidence sanitization, result serialization, fingerprints and CLI. The sections are coherent and well commented, but if this harness is retained, consider extracting result/metadata/CLI helpers in a later cleanup. Not a reason to block this task.

## Assessment

**Spec Compliance:** ❌ **Issues found** — I-1 must be fixed before any measured native-stream run; everything else I could verify from the diff is compliant. **⚠️ Cannot verify:** live native field shapes and accepted context without inference; the shared interfaces were checked and the coordinator's real runs remain the integration gate.

**Task quality:** **Needs fixes**

**Reasoning:** The deterministic harness is strong: it enforces frozen horizons, coalesces correctly, never duplicates native audio, separates fake/real evidence, and tests the difficult replay and policy cases. The context default/limitation mismatch is an experiment-design and truthfulness defect, not a cosmetic one; fix it before real measurements. The minor definition, zero-decode, interface, DRY and coverage notes can follow.
