# Contrarian preflight review — Spike 001 transcription

Date: 2026-10-26. Reviewer: adversarial preflight (read-only; no implementation).

> Retention note: this raw review is kept as evidence. On 2026-10-26 the
> personal-risk wording in the publication finding was generalized for the
> public repository while preserving the technical finding. The owner approved
> the public target and a privacy/Git-identity audit; see
> [task-4 report](task-4-report.md).
Scope: `spikes/001-transcription/PLAN.md`, `SPEC.md`, `docs/requirements.md`,
`docs/decisions/0001-native-macos-and-omp-rpc.md`, and the pinned upstream
`handy-computer/transcribe.cpp` sources/headers at
`8facde6fcd8fb9caa585a5788ab450df6e8ec7db`, plus the public model cards/dataset
metadata needed to check load-bearing claims.

## Verdict

**CONDITIONAL GO — do not dispatch Tasks 1–3 unchanged.**

There is no architectural dead end. The engine pin exists, both model docs support
the planned arms, the C API exposes a real streaming surface with committed/tentative
text, and the batch `endpoint`/`hybrid` plan is technically coherent. But three
pre-dispatch findings can silently invalidate the spike or block a task:

1. **Bilingual language is not representable in the backend/manifest contract.**
   `Engine(language=...)` is fixed at model load; Nemotron language is per-call and
   the fixtures are English *and* Spanish. The literal implementation either decodes
   Spanish with one prompt, constructs multiple engines (breaking "load once per arm"),
   or relies on `auto` without proving Parakeet accepts it.
2. **The fixture acquisition path is not solved.** The obvious per-clip FLEURS
   datasets-server API fails with a 300 MB parquet scan limit (703 MB for `es_419`,
   401 MB for `en_us`), the FLEURS test tarball is 582,112,372 bytes, and Common Voice
   17's HF repo contains no data files. A worker will either download a whole split
   (forbidden) or use a host package (forbidden). A bounded `Range`/`tarfile` extraction
   is viable and should be specified.
3. **Replay scheduling semantics are underspecified.** "No future samples" is tested,
   but the rule for freezing a prefix end at a scheduled tick, coalescing missed ticks
   after a slow decode, and prioritizing finalization is not. A synchronous decode that
   computes the prefix end at *execution* time leaks future audio into latency evidence.

One publication gate is also open: the package is to be public, and the documents
disclose private personal and interview context. That needs explicit consent or
generalization; it is a `[DECIDE]`, not a technical blocker.

If the three items above are fixed in SPEC/PLAN before dispatch, implementation can
proceed. The remaining High/Medium findings are implementation-time fixes with tests.

---

## Evidence checked (verified, at the pinned revision unless noted)

| Claim | Result |
| --- | --- |
| Engine pin `8facde6fcd8fb9caa585a5788ab450df6e8ec7db` | Exists; docs and headers fetched at that revision. |
| Parakeet v3 is offline-only | Confirmed by its model doc: "Not a streaming model"; token-level timestamps optional; CC-BY-4.0; Q8_0 740 MB. |
| Nemotron 3.5 is genuinely streamable | Confirmed: cache-aware FastConformer/RNN-T; offline `att_context_size=[56,13]`; streaming `--stream-chunk-ms 1120 --stream-att-right {0,3,6,13}` = 0/240/480/1040 ms lookahead; OpenMDW-1.1; Q8_0 751 MB; language required (`--language en-US`) or `auto`. |
| C API streaming surface | `transcribe_stream_begin/feed/finalize/reset`, `transcribe_stream_get_text` with append-only `committed_text` + volatile `tentative_text` + raw `full_text`; `transcribe_stream_feed` accepts arbitrary positive `n_samples`; `finalize` flushes lookahead; `reset` clears state. |
| Native commit policy | `transcribe_stream_params.commit_policy` = `AUTO` / `ON_FINALIZE` / `STABLE_PREFIX`; `stable_prefix_agreement_n` default `0`, library default **3 consecutive hypotheses**. |
| Native stream knob | `transcribe_parakeet_stream_ext.att_context_right` is in **encoder frames**; buffered sibling uses `left_ms/chunk_ms/right_ms`. There is **no** `chunk_ms` field on `transcribe_stream_params`; CLI `--stream-chunk-ms` is the caller's feed size, not a C API stream field. |
| `parakeet.h` menu comment | The header comment for the cache-aware extension lists a sibling's menu `{13,6,1,0}`; the 3.5 model doc lists `{0,3,6,13}`. The menu must be probed, not hardcoded. |
| Timings | `transcribe_get_timings` covers the most recent `transcribe_run` (mel/encode/decode), not streaming feeds; `0` means unknown; `transcribe_token.p` is NaN when absent. |
| Build layout | No `.gitmodules` (404). `ggml` is vendored at the repo root with `ggml/UPSTREAM` sha `d7cb574...` and three downstream patches. CMake minimum 3.16; Metal is enabled automatically on Apple Silicon. |
| Official Python binding | `bindings/python` 0.4.1 is ctypes-only, stdlib-only at runtime, and exposes `session.stream(language=..., commit_policy=..., stable_prefix_agreement_n=..., timestamps=...)` plus committed/tentative text. It needs a locally built shared library. |
| FLEURS license/provenance | `google/fleurs` is CC-BY-4.0. `test.tsv` is ~600 KB and has columns `id`, filename, transcription, raw_transcription, phonemes, num_samples, gender. Test tarballs advertise `Accept-Ranges: bytes`; `es_419` test is 582,112,372 bytes; first member readable from a 512 KB range. |
| FLEURS per-row API | `datasets-server` `/rows` fails: "Parquet error: Scan size limit exceeded" (703,032,560 bytes for `es_419`; 401,715,275 for `en_us`; limit 300,000,000). |
| Common Voice 17 on HF | `/splits` says the dataset directory contains no data files; not a per-clip source. |
| Local toolchain | `cmake 4.4.4`, `git`, `clang++`, `xcrun`, `ffmpeg`, `afconvert`, `python3 3.13.0` present. No host install is needed. |
| Repo state | Git is already initialized on `spike/transcription`, one commit, personal commit identity configured. PLAN's "initialize Git" is stale, not a blocker. |

No model was loaded and no inference was run in this review. The model files were not
found in the default Handy application-support models directory, so the plan's
"cached models" assumption still needs an explicit path/metadata precheck.

---

## Findings

Severity is about whether the issue can invalidate evidence or block a task, not
about implementation effort. `[DECIDE]` marks an owner judgment call.

### Critical

#### C-01 — Fixture acquisition as written is not executable without violating a constraint

- **Category:** fixtures / licensing
- **Location:** PLAN Task 3; SPEC §"Fixture manifest contract" lines 44–60;
  SPEC global constraint "Fetch only a few small licensed recordings, never a whole dataset."
- **Issue:** The two obvious bilingual public sources do not offer a working per-clip
  path. FLEURS' datasets-server row API fails on both target configs with a 300 MB
  parquet scan limit; its only per-config audio artifact is a 582 MB test tarball
  (whole split). Common Voice 17's HF repo has no data files. A worker following the
  brief literally will either download a whole split, install `datasets`/`huggingface_hub`
  on the host (forbidden), or stall. Two further traps: FLEURS tarball order is not the
  TSV row order (the first member is `test/1001146817223348054.wav`, ~821 KB ≈ 25.7 s,
  not TSV row 0), and a naive `tarfile` read of a truncated range raises `ReadError`
  after the last complete member.
- **Suggested fix:** Pin `google/fleurs` at revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`
  (`x-repo-commit` observed). Fetch `data/{es_419,en_us}/test.tsv` directly. Fetch a
  bounded `Range` prefix (e.g. 4–8 MB) of the corresponding `test.tar.gz`, stream it
  with `tarfile.open(mode="r|gz")`, stop after the needed members, and map by WAV
  filename—not tar position—to the TSV. Select clips with `num_samples` below the
  configured hybrid window for the default set; include one longer clip only in an
  explicitly labelled rollover fixture. Record source WAV hash, filename, TSV row index,
  dataset revision/config/split. Include CC-BY-4.0 attribution in `fixtures/`.
  Add a fetch-only fallback and a deterministic `--verify-only` mode.

#### C-02 — The backend contract cannot express per-fixture language

- **Category:** API / experiment validity
- **Location:** SPEC §"Python backend contract" lines 24–42 (`Engine.__init__(..., language="auto", ...)`,
  `transcribe(samples, *, sample_rate=16000)`, `start_stream(*, chunk_ms=1120, right_context=3)`);
  SPEC line 64 (arms); PLAN Task 1 ("Reuse the engine across partial requests and fixtures");
  manifest `language: "en"`.
- **Issue:** `language` is fixed at model construction, but Nemotron's language is a
  per-call prompt (`--language en-US`/`es-ES`/`auto`) and the fixture set is English and
  Spanish. The runner cannot select Spanish for a Spanish clip without either reloading
  the model (violating "model loading happens once per timed arm/process") or decoding
  Spanish with an English/auto prompt and hoping. `auto` may work, but that is an
  unproven assumption for Parakeet (which has no language-ID prompt in its model doc)
  and it changes the experiment from language-conditioned to language-detected. The
  manifest's `language: "en"` is also too coarse: Nemotron's Spanish locales are
  `es-US`/`es-ES`, while FLEURS is `es_419`; the prompt actually used must be recorded.
- **Suggested fix:** Make language per call: `transcribe(..., language=None)` and
  `start_stream(..., language=None)`, with the constructor value as a default. Add
  `source.locale` (dataset locale) and `asr_language` (BCP-47 prompt or `auto`) to each
  fixture. Resolve against the model's `capabilities.languages`; map the adapter's
  `"auto"` to the C API's NULL autodetect where required, and record requested prompt,
  detected language (when the model reports it), and whether the model supports LID.
  Record the resolved language per trial. Do not create one engine per language unless
  the plan explicitly accepts repeated model loads.

#### C-03 — Replay scheduler can leak future audio and mis-measure latency

- **Category:** runner / metrics
- **Location:** PLAN Task 2 ("no future samples", "paced-clock arrivals", coalescing);
  SPEC constraints lines 17 ("Inference sees only audio that has arrived") and 19
  (oracle endpoints, no word-end claims).
- **Issue:** The plan requires a no-future test but does not define the scheduler's
  load-bearing rule. With a synchronous decode, if the runner computes the prefix end
  from "samples available now" *after* decode returns, it includes audio that arrived
  during the decode and attributes it to an earlier scheduled tick; that is a silent
  future-audio leak and corrupts first-partial/stable/final latency. Similarly, after a
  slow decode, the next partial can jump several ticks; without a frozen scheduled tick
  and explicit coalescing counters, the backlog is unmeasured and results are not
  reproducible. Finalization priority is asserted in prose but not specified for a
  queue implementation.
- **Suggested fix:** Specify and test this algorithm: (a) precompute scheduled tick
  times from the audio clock; (b) at each tick, freeze `prefix_end = min(tick, arrived)`
  and never extend it during that decode; (c) after decode, if the next tick is already
  past, coalesce the missed ticks and record `scheduled_ticks`, `completed_ticks`,
  `coalesced_ticks`, `skipped_audio_ms`; (d) finalization always runs with the full
  arrived prefix and bypasses pending partials; (e) a slow-decode fake engine test
  asserts the prefix end equals the frozen tick, never `now`. Prefer a single-threaded
  scheduler for determinism; if using a thread, test the queue policy explicitly.

### High

#### H-01 — Native-stream commit policy is unset; native and hybrid are not policy-comparable

- **Category:** API / experiment validity
- **Location:** SPEC lines 35–42 (`start_stream` has no commit policy); SPEC line 64
  (`native-stream` arm); PLAN Task 2 ("LocalAgreement-2 hybrid and genuine native-stream arms").
- **Issue:** The C API's default `AUTO` uses a dispatcher/family-provided boundary, and
  `stable_prefix_agreement_n` defaults to **3 consecutive hypotheses**. The hybrid arm is
  explicitly LocalAgreement-2. If the native arm uses defaults, the comparison confounds
  model architecture with a 3-vs-2 agreement policy, and the reported `committed_text`
  may not be LA-2 at all. The SPEC's result dict has no field to reveal this.
- **Suggested fix:** Expose `commit_policy` and `stable_prefix_agreement_n` on
  `start_stream` (or fix them and document). For a fair policy comparison set
  `STABLE_PREFIX` + `n=2`, but do not assume the family honors generic agreement; also
  compute LA-2 in the runner from the raw cumulative `full_text` snapshots and report
  both native-committed and runner-LA-2 text. Record the policy, agreement `n`, and
  whether the family boundary was used.

#### H-02 — `right_context=3` and `chunk_ms=1120` conflate three different knobs

- **Category:** API / timestamp / latency
- **Location:** SPEC line 36 (`start_stream(*, chunk_ms=1120, right_context=3)`);
  SPEC line 64 ("nominal 1120 ms chunks/right context 3"); PLAN Task 1 ("Establish actual native streaming support").
- **Issue:** The C API's cache-aware extension has `att_context_right` in **encoder
  frames**; the buffered sibling has `right_ms`; there is no `chunk_ms` field on
  `transcribe_stream_params`. `--stream-chunk-ms` is the CLI's *feed* size, and
  `hello_stream` treats `chunk_ms` as a caller-side slice. Feeding 1120 ms is sensible
  because the model's internal chunk is 1120 ms, but calling it a native stream
  parameter is wrong. The `parakeet.h` header comment lists `{13,6,1,0}` for a sibling
  Nemotron while the 3.5 card lists `{0,3,6,13}`; hardcoding 3 or validating against
  the header comment can reject a valid model or accept an invalid one. Right-context 3
  is 240 ms lookahead, not end-to-end latency.
- **Suggested fix:** Rename to `feed_chunk_ms` (caller cadence) and a model-specific
  `stream_context` (e.g. `att_context_right_frames=3` for cache-aware; `right_ms` for
  buffered). Default `-1`/model default, probe
  `transcribe_model_accepts_ext_kind` and the model's accepted menu, and fail clearly if
  3 is not in it. Record the accepted menu, chosen value, lookahead in ms, internal
  chunk, and the distinction between algorithmic latency (`chunk + lookahead`) and
  measured wall latency. Never pass `feed_chunk_ms` as a native knob.

#### H-03 — Result schema loses the committed/tentative distinction and the final-authority rule

- **Category:** API / results
- **Location:** SPEC lines 40–42 (result dict: `text`, `tokens`, `decode_ms`, `final`);
  SPEC line 66 (stable prefix/final correction).
- **Issue:** The C API exposes four different texts: raw `full_text`, append-only
  `committed_text`, volatile `tentative_text`, and `display_text`. The contract has one
  `text` field and does not say whether it is raw, display, or committed. The runner's
  LA-2 policy needs raw cumulative hypotheses; the UI/stable-prefix evidence needs
  committed/tentative; WER needs the final authoritative `full_text` (the C API says
  `full_text` remains authoritative even when committed text disagrees). Without this,
  a worker may report display text as "the hypothesis" and silently hide revisions, or
  report committed text as the final transcript and understate WER.
- **Suggested fix:** Define `text` explicitly (recommend raw cumulative `full_text` for
  streaming), add `committed_text`, `tentative_text`, `display_text`, `final_text`,
  `revision`, `buffered_ms`, `audio_committed_ms`, and `committed_changed`/
  `tentative_changed`. Define that WER uses `final_text` (raw authoritative) and that
  stable-prefix WER may be reported separately with a label. Test first-feed pointer
  copy, final flush, and disagreement between committed and final.

#### H-04 — `decode_ms` conflates native compute, wall time, and "unknown"

- **Category:** metrics / timestamps
- **Location:** SPEC lines 40–42 (`decode_ms`); SPEC line 42 ("Runner times calls
  independently, rather than trusting reported native duration alone"); PLAN Task 2
  ("Record ... decode/queue time").
- **Issue:** `transcribe_get_timings` covers the most recent `transcribe_run` only;
  streaming `feed`/`finalize` do not update mel/encode/decode. Its zero values mean
  "unknown", not zero. A helper that copies native timings into every feed will report
  fabricated or stale `decode_ms`. A helper that uses Python wall time as `decode_ms`
  conflates queueing, JSON transfer, and decode. Token probabilities can be NaN, which
  is invalid JSON.
- **Suggested fix:** Require `wall_ms` for every call (runner-measured) and make
  `native_decode_ms` nullable, populated only for `transcribe_run` (and only when
  non-zero); set it to `null` with an explanation for streaming feeds. Record
  `load_ms` from native timings and process-start separately. Sanitize NaN/±Inf to
  `null` and emit JSON with `allow_nan=False`. Add synthetic tests for zero/unknown and
  NaN.

#### H-05 — A JSON/line protocol carrying PCM would dominate the measurements

- **Category:** backend / performance
- **Location:** PLAN Task 1 ("persistent C++ helper with a line-oriented protocol");
  SPEC lines 26–42 (backend contract).
- **Issue:** The brief says a persistent native helper is acceptable and mentions a
  "JSON helper". If PCM is transferred as JSON numbers, a 20 s prefix is 320k floats
  (≈1.3 MB binary, several MB of decimal text); a hybrid run of 20 cumulative calls
  transfers hundreds of megabytes and spends measurable CPU in Python serialization,
  distorting decode/queue/backlog metrics. Even short fixtures multiply this. A naive
  text protocol can also corrupt UTF-8 and deadlock on buffering.
- **Suggested fix:** Use length-prefixed binary frames for PCM (e.g. 4-byte little-endian
  length + float32LE samples) and JSON only for metadata/results; or adopt the official
  ctypes binding, which accepts Python buffer objects and avoids serialization. If a
  text protocol is retained, benchmark serialization separately and subtract it from no
  metric; test Unicode, quotes, newlines, partial lines, and large frames.

#### H-06 — WER normalization is undefined and will be wrong for Spanish

- **Category:** WER / metrics
- **Location:** SPEC line 19 ("Keep normalized WER ... with substitutions/deletions/insertions");
  SPEC line 68 (tests "WER normalization/counts"); PLAN Task 2 ("Normalization/empty-reference WER").
- **Issue:** "Normalized" is not defined. Published model WER uses `whisper-normalizer`;
  the spike's results will not be comparable unless that is stated. Common traps:
  lowercasing, punctuation removal, collapsing whitespace, handling `¿¡`, digits vs
  spelled numbers, and **ñ**—stripping combining marks turns `niño` into `nino` and
  changes the word. Empty/silent references make WER 0/0; per-file mean vs micro
  aggregation differ; partial hypotheses must not be scored as if final.
- **Suggested fix:** Pin a normalizer version and rules: NFC, case-folding, strip
  terminal punctuation (including `¿¡`), collapse whitespace, preserve accents/ñ,
  define digit handling, and state non-comparability with the model card. Define
  `wer=null` with `n_ref=0` for empty references, and report S/D/I counts plus
  reference/hypothesis text. Report per-fixture WER and micro-aggregate (sum errors /
  sum reference words), not only a mean of ratios. Add tests for accents, ñ, punctuation,
  digits, empty reference, empty hypothesis, and alignment tie-breaking.

#### H-07 — Manifest provenance is weaker than the prose requires

- **Category:** fixtures / provenance
- **Location:** SPEC §"Fixture manifest contract" lines 44–60 (schema has only
  `wav_sha256`, `reference_sha256`, `duration_s`, `source.url/revision/license/split/row`);
  SPEC line 60 ("Record source audio hash and conversion tool/version when conversion is required").
- **Issue:** The schema has no field for the **source audio hash**, conversion tool/version,
  dataset config, or a stable item id. `source.row` as an integer is brittle: FLEURS TSV
  row order is not the audio tar order, and the first column is a repeated sentence id,
  not a unique row id. A signed HF CDN URL must never be written as `source.url`.
- **Suggested fix:** Add `source.config`, `source.item_id` (WAV filename), `source.row_index`,
  `source.audio_sha256`, `source.dataset_revision`, `source.reference_column`, and
  `conversion: {tool, version, command}` (or `none`). Use the canonical dataset URL +
  revision, never the signed redirect. Make the manifest self-verifying: hashes, duration,
  language/locale, and segment bounds.

#### H-08 — Forced-cut/rollover behavior is neither designed nor tested

- **Category:** runner / policy
- **Location:** SPEC line 66 ("If fixed-window limits are reached, emit a clear
  unsupported/forced-cut outcome rather than silently leaking future audio");
  PLAN Task 2 ("reject unsupported rolling-window lengths explicitly").
- **Issue:** The plan says initial fixtures may be below the window limit and does not
  require a forced-cut test. If a fixture exceeds the 15–20 s window, the hybrid must
  either reject, or cut and stitch. Stitching has real hazards: token times are relative
  to the window, overlapping audio can duplicate words, and a stable prefix from window
  1 must not be re-emitted by window 2. A test only for "reject unsupported lengths" does
  not cover a supported forced-cut path.
- **Suggested fix:** Decide one behavior for the default: reject clips longer than the
  configured window with a clear `unsupported` outcome, or implement a documented
  rollover with global timestamp offsets, overlap dedupe, and an epoch id. Add a test at
  a small configured limit (e.g. 2 s) with a fake engine that proves no duplication, no
  lost audio, and correct offsets. If the default rejects, still test the rejection and
  do not include a longer clip in the default manifest.

#### H-09 — Public publication of private personal/interview context needs explicit confirmation

- **Category:** privacy / publication `[DECIDE]`
- **Location:** `docs/requirements.md` Purpose (lines 8–12); NFR-05/NFR-09 (lines 54, 58);
  PLAN Task 4 and integration/publication; SPEC line 21.
- **Issue:** The repository is approved for public creation "after privacy audit", but
  the documents disclose private personal context, the HackerRank interview context and
  a stealth feature baseline. That is a consequential personal disclosure beyond commit
  identity/model paths. The plan's privacy audit language focuses on results, absolute
  paths, weights, and Git identity; it does not explicitly cover doc-level personal data.
- **Suggested fix:** Add a publication gate: explicit owner confirmation that the
  Purpose/NFR-05/NFR-09 text is intended for a public repo, or generalize those passages
  before push. Include this in the final privacy audit alongside the automated scan.
  Do not silently redact owner-approved requirements; record the decision.

#### H-10 — The source-pin/build plan assumes submodules that do not exist

- **Category:** build / pin
- **Location:** PLAN Task 1 ("pin all source/submodule revisions and source hashes");
  SPEC line 15 ("Engine source pin ... revision ...").
- **Issue:** `transcribe.cpp` has no `.gitmodules`; `ggml` is vendored at the repo root
  with `ggml/UPSTREAM` sha `d7cb574130e6f01ad25b3289685489200febcd74` and three
  downstream patches. A worker looking for submodules will either waste time or record
  an incomplete pin. "Source hashes" of a tree is also undefined. The build uses CMake
  ≥ 3.16 and Metal automatically; a build flag alone is not backend evidence.
- **Suggested fix:** Define `engine.lock.json` with: repo URL, commit, `git rev-parse
  HEAD^{tree}`, `ggml/UPSTREAM` sha, downstream patch list, `transcribe` version (0.4.1),
  CMake/compiler versions, build flags, executable SHA-256, and clean/dirty status.
  Verify the clone's HEAD/tree matches the lock and fail on a dirty tree. Record the
  actual backend via `transcribe_model_backend()`, not the build flag. Do not invoke
  package managers; fail clearly if CMake/clang is missing.

### Medium

#### M-01 — `language="auto"` is not the C API's autodetect sentinel

- **Category:** API
- **Location:** SPEC line 30 (`language="auto"`); C API `transcribe_run_params.language`
  docs (NULL to autodetect).
- **Issue:** The C API documents NULL as autodetect; the CLI/model card use the string
  `auto`. The adapter may pass the literal `"auto"` to a family that expects NULL, or
  pass NULL to Parakeet which may not support LID. Parakeet's model doc has no language
  parameter.
- **Suggested fix:** Map `"auto"` to NULL (or the model-specific sentinel) only when
  `capabilities.supports_language_detect`; otherwise require an explicit language or
  omit the hint and record "not applicable". Add a fake-engine test for both capability
  states and a real-model check in the coordinator run.

#### M-02 — Session lifecycle across batch and stream is undefined

- **Category:** API / lifecycle
- **Location:** SPEC lines 29–42; PLAN Task 1 ("lifecycle/close, stream reset and final flush").
- **Issue:** A C API session is in one of four states; `transcribe_run` and
  `transcribe_stream_*` share result accessors. The adapter must define whether
  `transcribe()` and `start_stream()` reuse one session, create separate sessions from
  one model, or reset. Calling `transcribe()` after a stream or `start_stream()` after a
  batch run without reset can return stale or invalid results.
- **Suggested fix:** Use one loaded model and separate sessions for batch and stream (or
  reset explicitly between modes). Test `transcribe → start_stream → feed → finalize →
  transcribe`, `start_stream` twice without close, `feed` before `start_stream`, and
  `feed` after `finalize`. Record the session id/epoch in results.

#### M-03 — Helper robustness is not in the test plan

- **Category:** tests / backend
- **Location:** PLAN Task 1 ("lifecycle/close, serialization, persistent process/model reuse, stream reset and final flush").
- **Issue:** A persistent subprocess introduces failure modes that the listed tests do
  not cover: helper exits mid-feed, writes a partial JSON line, writes logs to stdout,
  fills stderr and deadlocks, hangs forever, or returns malformed JSON. `close()` after
  an error and idempotent close are listed, but not EOF/hang/timeout.
- **Suggested fix:** Add tests with a fake helper that exits, emits partial lines,
  emits non-JSON, writes to stderr, sleeps, and returns an error status. Add a
  configurable per-request timeout with kill/reap, drain stderr on a thread or use a
  separate protocol, and assert no zombie. Test double close and close after a failed
  constructor.

#### M-04 — C ABI struct initialization and pointer lifetime are easy to get wrong

- **Category:** API / backend
- **Location:** PLAN Task 1 ("persistent C++ helper ... avoids hand-written unsafe ABI guesses");
  C API header: `{0}` is rejected; every struct must use `transcribe_*_init()`; text
  pointers are invalidated by the next feed/reset/free.
- **Issue:** A C++ helper that zero-initializes `transcribe_stream_params` will get
  `TRANSCRIBE_ERR_BAD_STRUCT_SIZE`; a helper that stores `const char*` results past the
  next feed will return corrupted text. These are common and avoidable.
- **Suggested fix:** Require init functions for every public struct; copy strings
  immediately after each call; add tests that hold the first result while issuing a
  second feed and verify the first bytes are unchanged. Add a code-review checklist
  item for pointer lifetime.

#### M-05 — `feed(final=True)` semantics and edge cases are undefined

- **Category:** API
- **Location:** SPEC lines 35–37 (`feed(samples, *, final=False)`).
- **Issue:** It is unclear whether `final=True` (a) feeds the samples then finalizes,
  (b) flushes without feeding, or (c) is invalid with non-empty samples. Empty input,
  double finalize, `feed` after close, and `final=True` twice are not defined. The C API
  requires `n_samples > 0` for feed and a separate finalize call.
- **Suggested fix:** Define: non-empty `samples` + `final=True` = feed then finalize;
  empty `samples` + `final=True` = finalize only; empty + `final=False` = no-op or clear
  error (pick one); second finalize/feed after finalize = clear error. Add tests for all.

#### M-06 — The official ctypes binding was not evaluated

- **Category:** backend / risk
- **Location:** PLAN Task 1 (choice of helper); SPEC line 26 ("Internal implementation
  may use a persistent native JSON helper or bindings").
- **Issue:** `transcribe.cpp` ships a first-party Python binding (0.4.1, ctypes-only,
  stdlib at runtime) that already exposes per-stream language, commit policy, agreement
  `n`, timestamps, committed/tentative text, backend, capabilities, and timings. Writing
  a custom C++ helper duplicates the ABI/protocol risk and the PCM transport problem.
  The binding needs a locally built shared library, which is a build detail, not a host
  install.
- **Suggested fix:** Evaluate the binding first with `TRANSCRIBE_BUILD_SHARED=ON` and
  `TRANSCRIBE_LIBRARY`/auto-discovery, without pip install. If it works at the pin,
  prefer it (or a thin stdlib wrapper) and document the version/header-hash pin. If it
  is rejected, record the concrete reason and keep the binary-frame helper design.

#### M-07 — Cached-model paths and identity are not prechecked

- **Category:** build / provenance
- **Location:** SPEC line 14 ("Reuse cached Q8_0 Parakeet v3 and Nemotron 3.5 streaming models");
  PLAN Task 1 (build and test).
- **Issue:** The repo has no model paths; the plan takes them as CLI arguments but does
  not require verifying that the files are the expected architectures/quants, nor how to
  discover them. The default Handy application-support models directory inspected in
  this review contained no GGUF, so "cached" is an assertion that must be resolved before
  dispatch. Filename alone is not identity.
- **Suggested fix:** Add a preflight command that locates the two GGUF files from
  operator-supplied paths, reads GGUF metadata (architecture/variant/quant), checks the
  expected Q8_0 sizes (≈740 MB / ≈751 MB) and SHA-256, and records basename/size/hash
  only. Fail with a clear message if either is absent; never download a model.

#### M-08 — Manifest path resolution and CWD are ambiguous

- **Category:** fixtures / runner
- **Location:** SPEC line 60 ("Paths are relative to the spike root"); manifest example
  `"wav": "fixtures/example.wav"`; PLAN integration command runs from the repo root.
- **Issue:** If the runner resolves paths relative to the manifest's directory
  (`fixtures/`), `fixtures/example.wav` becomes `fixtures/fixtures/example.wav`. If it
  uses CWD, running from the repo root vs the spike root changes the target. Symlink
  escape is possible without a resolved-path check.
- **Suggested fix:** Define the spike root as `Path(__file__).parent` for `run.py`, or
  require `--root`; resolve each path with `.resolve()` and assert
  `is_relative_to(root)` (reject symlinks that escape). Add tests from both CWDs and a
  symlink escape test.

#### M-09 — `segments` schema is underspecified

- **Category:** fixtures / schema
- **Location:** SPEC lines 55–57 (`segments: [{start_s, end_s, kind: "oracle_file_boundary"}]`).
- **Issue:** Only one example `kind` is given; there is no rule for coverage, ordering,
  gaps/overlap, multiple segments, or a derived/assembled fixture. A derived fixture has
  no dataset file boundary, so `oracle_file_boundary` would be a false provenance claim.
- **Suggested fix:** Enumerate allowed kinds (`oracle_file_boundary`, `derived_assembly`,
  etc.), require sorted non-overlapping segments covering `[0, duration_s]`, and add a
  `derivation` block for assembled fixtures. Validate in tests; do not label a derived
  clip as a dataset file boundary.

#### M-10 — LocalAgreement-2 unit and revision rules are undefined

- **Category:** policy / tests
- **Location:** SPEC line 66 (stable prefix, conflicts, final correction); PLAN Task 2
  ("common-prefix disagreement, append-only stability, final correction").
- **Issue:** "Common prefix" can be computed on model token ids, token text, or
  whitespace words. Punctuation, case, SentencePiece markers, and Unicode normalization
  can cause permanent disagreement or false agreement. If the model's batch decode is
  nondeterministic for the same prefix, LA-2 never commits; that must be measured, not
  assumed. The plan does not say whether punctuation counts toward agreement.
- **Suggested fix:** Pin the comparison unit (recommend normalized whitespace words
  derived from token rows, with punctuation handled explicitly), minimum commit length,
  and conflict rule. Add tests for punctuation-only/case-only differences, Unicode/ñ,
  repeated prefixes, and a nondeterministic fake engine. In the real run, decode the same
  prefix twice and record determinism.

#### M-11 — Latency metric definitions are missing

- **Category:** metrics
- **Location:** SPEC lines 18–19, 68; PLAN Task 2 ("Record ... decode/queue time,
  coalescing/backlog ... not invented ground truth").
- **Issue:** "First partial", "stable", and "final" latency need explicit start/end
  events. Without gold word timings, a token's `end_ms` is a model timestamp, not a
  verified word end. The native model's algorithmic latency is `chunk + lookahead`
  (1120 ms + 240 ms at R=3), which is not the measured decode/display latency. Mixing
  these produces a misleading "latency" number.
- **Suggested fix:** Define: `first_partial_ms` = hypothesis arrival minus audio-arrival
  time of the first sample (or first speech, if VAD; not used here); `first_stable_ms` =
  first committed/LAA-2 prefix arrival; `final_ms` = finalize return minus audio-end
  arrival; `display_latency_ms` = text arrival minus the **model-reported** token end,
  labelled approximate; `algorithmic_latency_ms` = feed chunk + lookahead; `wall_ms` =
  measured call time. Keep unsupported fields null with an explanation.

#### M-12 — Simulated clock must not populate real latency fields

- **Category:** metrics / tests
- **Location:** SPEC line 17 ("label real paced replay versus simulation"); PLAN Task 2
  ("Use fake engine/clock for deterministic tests").
- **Issue:** A simulated run can feed all audio instantly and produce beautiful latency
  numbers that are meaningless. The plan says to label it, but labels are easy to lose
  when results are aggregated.
- **Suggested fix:** Add a `clock_mode` enum (`real_paced`, `simulated`, `fake`) to every
  result; in `simulated`/`fake` mode, force wall/latency fields to `null` or a separate
  `simulated_*` namespace. Add a test that simulated results cannot be written as real
  measured latency. Report the mode in the findings.

#### M-13 — JSON schema/NaN/output atomicity are not specified

- **Category:** metrics / results
- **Location:** SPEC line 68 (result fields); PLAN Task 2 (metrics).
- **Issue:** Python's `json.dump` emits `NaN`/`Infinity` by default, which is invalid
  JSON; token `p` is documented as NaN when absent, and timing values are 0 when unknown.
  There is no result schema version, no unique trial id, and no atomic-write rule; a
  crash can leave a partial JSON file.
- **Suggested fix:** Define a `schema_version`, `trial_id`, `command`, `git_commit`,
  `started_at`, `duration_ms`, and a JSON schema. Use `allow_nan=False`, convert unknown
  to `null`, write to a temp file + `os.replace`, and validate before/after. Test invalid
  output paths and a simulated crash.

#### M-14 — Privacy scan and Git identity checks are not automated

- **Category:** privacy / publication
- **Location:** PLAN integration ("privacy/identity audit"); SPEC line 21.
- **Issue:** The final audit is manual and after the fact. Results/lockfiles/logs can
  contain absolute paths, usernames, hostnames, serials, signed HF URLs, model paths, or
  the work email domain; a manual scan can miss them. `git config` being personal does
  not prove every commit is.
- **Suggested fix:** Add a tracked-file scanner (Python stdlib) that fails on
  `/Users/`, `/home/`, `$HOME`, hostname, `IOPlatformSerialNumber`, `*.gguf` paths,
  signed URL query strings, `.omp/`, and the work email domain. Add a
  `git log --format='%ae %ce'` check for every commit and a `gh auth status` check for the
  personal account. Run both before the public push.

#### M-15 — `.gitignore` lands in Task 4 while Tasks 1/3 create caches first

- **Category:** repository hygiene
- **Location:** PLAN Task 4 (`.gitignore`); Tasks 1/3 (`.cache/`, `.tools/`, model files);
  integration commit step.
- **Issue:** The plan dispatches all tasks together and Task 4 owns `.gitignore`. Before
  it exists, `.cache/`, `.tools/`, `build/`, and model files can appear. If the main
  agent stages with `git add -A`, a 1.5 GB model or a source clone can enter the public
  repo.
- **Suggested fix:** Create `.gitignore` before dispatching (or have Task 4 commit it
  first) with `.cache/`, `.tools/`, `build/`, `*.gguf`, `.omp/`, `__pycache__/`,
  `.DS_Store`, and explicit negations for `fixtures/**` and curated `results/*.json`.
  Stage explicit paths, never `git add -A`; check `git status`/`du` before committing.

#### M-16 — Native R=3 vs offline R=13 comparison needs a label/control

- **Category:** WER / experiment design
- **Location:** SPEC lines 64–66 (endpoint + native arms); model docs.
- **Issue:** The endpoint arm uses Nemotron's offline `[56,13]` max-accuracy path; the
  native arm is planned at right context 3 (240 ms lookahead). Any WER difference
  includes the latency setting, not just streaming. The doc says R=13 is byte-equal to
  offline; R=3 trades accuracy for latency. Without a label or an R=13 control, a reader
  can misattribute the gap.
- **Suggested fix:** Record `stream_latency_setting` per arm; state that endpoint is
  R=13 and native is R=3. Optionally add a native R=13 control (same model, no latency
  benefit) to separate streaming-vs-batch from latency-setting effects. Do not call the
  result a model leaderboard.

#### M-17 — The documented test command fails to import the spike modules

- **Category:** tests / process
- **Location:** PLAN integration ("`python3 -m unittest discover -s spikes/001-transcription/tests -v`").
- **Issue:** Verified in a temp fixture: with the start directory under `spikes/.../tests`,
  `unittest` puts that directory—not the spike root—on `sys.path`; `import backend`
  raises `ModuleNotFoundError`. The plan's exact command cannot run the tests from the
  repo root.
- **Suggested fix:** Run from the spike root (`cd spikes/001-transcription &&
  python3 -m unittest discover -s tests -v`) or add `-t spikes/001-transcription`, or
  insert `Path(__file__).parents[1]` in each test module. Use the corrected command in
  the plan, README, and reports; add a test that the documented command works.

#### M-18 — `run.py` CLI surface is under-specified

- **Category:** runner / UX
- **Location:** SPEC line 64 ("`run.py --help` documents model/helper paths, manifest,
  arm, output, repeats and timing configuration").
- **Issue:** The required experiment needs more: per-fixture/asr language, window
  length, partial interval, feed chunk, commit policy/agreement, timestamp request,
  warmup, seed, fixture filter, clock mode, and output collision behavior. Without
  explicit args, workers may hardcode values, making results non-reproducible.
- **Suggested fix:** Enumerate the CLI in SPEC/PLAN, validate `--arm` against model
  capabilities, reject `native-stream` for Parakeet, and include every parameter in the
  result JSON. Test `--help`, invalid arms, missing files, and output collisions.

#### M-19 — Python 3.13 removed `audioop`

- **Category:** fixtures / environment
- **Location:** PLAN Task 3 ("Use existing tools or standard library conversion where
  possible").
- **Issue:** The local interpreter is Python 3.13.0; `audioop` (a common resampling/
  conversion helper) was removed in 3.13. A worker may reach for it and fail. FLEURS
  WAVs are already 16 kHz mono PCM16, so no conversion is needed; Common Voice MP3 would
  need `afconvert`/`ffmpeg`.
- **Suggested fix:** Prefer FLEURS' native 16 kHz WAV; if conversion is required, use
  `afconvert`/`ffmpeg` (already present) and record the version/command. Do not depend on
  `audioop`; verify WAV type/rate/channels with `wave` + `array` in tests.

### Low

| ID | Category | Location | Issue | Suggested fix |
| --- | --- | --- | --- | --- |
| L-01 | API | SPEC line 33 (`info.capabilities`) | Only `batch/native_stream/timestamps` booleans; loses `languages`, `supports_language_detect`, `max_audio_ms`, `returned_timestamp_kind`, actual backend. | Add these fields; source them from the C API, not model names; test capability gating. |
| L-02 | API | C API threading note; SPEC line 17 | The C API forbids concurrent compute across sessions of one model; a two-channel design cannot run two streams in parallel on one model. | Document single-channel/serialized scope; do not parallelize on one model; one model per worker if future. |
| L-03 | publication | PLAN Task 4; SPEC line 21 | No attribution plan for Parakeet (CC-BY-4.0), Nemotron (OpenMDW-1.1), transcribe.cpp (MIT), FLEURS (CC-BY-4.0); project license undecided. | Add `THIRD_PARTY`/`NOTICE`/`fixtures/ATTRIBUTION.md`; README states license undecided; do not choose a license. |
| L-04 | publication | PLAN integration; repo state | Repo is already on `spike/transcription` with one commit; PLAN says "initialize Git"; no default-branch/no-license decision. | Update PLAN/ledger; decide `main` + work branch or set default explicitly; verify remote visibility and SHA. |
| L-05 | fixtures/tests | PLAN Task 3 | Tests do not explicitly cover duplicate fixture ids, zero fixtures, declared-vs-actual duration, unsupported schema_version, or a missing reference. | Add manifest validation tests and a zero/duplicate fixture test. |
| L-06 | WER/tests | PLAN Task 2 | Alignment tie-breaking and Unicode normalization are not pinned; two implementations can produce different S/D/I. | Pin a deterministic Levenshtein backtrace and Unicode rules; add fixture cases. |
| L-07 | results/tests | SPEC line 68; PLAN privacy audit | No test that result JSON/lockfiles contain no absolute paths/usernames/signed URLs. | Add the privacy scanner test from M-14 and a `no_absolute_paths` assertion. |
| L-08 | API/tests | SPEC lines 40–42 | `close()` idempotence is stated, but feed-before-start, double close, close after constructor failure, and operations after close are not all enumerated. | Add lifecycle tests for each. |
| L-09 | build | PLAN Task 1 | `Engine(executable=None)` is ambiguous: auto-build (network surprise) vs discover `.tools` vs error. | Require an explicit executable path or a documented `.tools` lookup; never build/download implicitly. |
| L-10 | results | SPEC line 33 | `info.load_ms` may include helper process startup if measured in Python; process-start and model-load are different. | Record `process_start_ms`, native `load_ms`, and total constructor time separately. |

---

## Test holes to close before the evidence gates

1. **Scheduler:** slow decode with a fake clock; frozen prefix end; missed-tick
   coalescing counters; no future samples; finalization bypasses pending work.
2. **Stream lifecycle:** reset between fixtures; first feed after reset; double
   `start_stream`; `feed` before start; `feed`/`finalize` after finalize; batch↔stream
   transitions; text pointers copied before the next feed.
3. **Native capability:** Parakeet advertises no streaming → clear unsupported error;
   Nemotron accepts the selected extension/right context; unsupported menu value →
   clear error; no batch fallback labelled streaming.
4. **Policy:** LA-2 unit (token/word), punctuation/case-only disagreement, ñ/Unicode,
   nondeterministic fake engine, stable-prefix conflict recording, final correction,
   forced cut/rollover offsets and no duplication.
5. **Inputs:** empty/silent/NaN/Inf, wrong sample rate, empty feed, huge feed, finite
   validation, model-load failure, truncated GGUF, permission denied.
6. **Helper:** crash mid-feed, partial JSON line, non-JSON, logs on stdout, stderr
   deadlock, hang/timeout, double close, zombie/reap.
7. **Manifest/fixtures:** duplicate ids/paths, zero fixtures, schema_version mismatch,
   duration mismatch, path traversal/symlink, corrupt fixture, modified tracked fixture,
   source hash mismatch, reference/audio mismatch.
8. **WER:** empty/empty, empty/non-empty, accented Spanish, ñ, punctuation, digits,
   alignment tie-break, micro vs macro, partial-vs-final labeling.
9. **Metrics/JSON:** unknown timings → null, NaN `p` → null, `allow_nan=False`,
   simulated clock cannot populate real latency, atomic output write, unique trial ids.
10. **Privacy/pin:** no absolute paths/usernames/hostnames/serials/signed URLs; every
    commit identity; lock-source tamper; executable hash mismatch; dirty tree.

---

## What is already sound (do not "fix" these away)

- The spike is correctly framed as feasibility, not a model leaderboard; no acceptance
  threshold is approved.
- The plan correctly forbids word-end/display-latency claims without gold timings, and
  requires null/unsupported rather than fabricated zeros.
- The plan correctly forbids a hidden batch fallback for native streaming, repeated CLI
  cold starts, host installs, model downloads, and model weights in publication.
- The plan correctly requires a pinned engine, source/executable fingerprints, licensed
  fixtures, retained evidence, independent reviews, and a privacy/identity audit before
  the public push.
- The C API is the right layer: it exposes genuine streaming committed/tentative text,
  commit policies, accepted context menus, actual backend, capabilities, and timings.
  The official ctypes binding is a legitimate way to avoid a custom helper; it is not an
  "undocumented ABI" shortcut.
- The FLEURS choice is otherwise strong: CC-BY-4.0, 16 kHz mono WAV, English/Spanish,
  complete single-utterance clips, and public metadata. The problem is the acquisition
  mechanism, not the dataset.

---

## Recommended pre-dispatch checklist

- [ ] Amend SPEC's backend contract: per-call `language`; `feed_chunk_ms` vs native
      context; commit policy/agreement; committed/tentative/final fields; `wall_ms` vs
      nullable native `decode_ms`.
- [ ] Amend the manifest: `source.config`, `item_id`, `row_index`, `audio_sha256`,
      `dataset_revision`, `reference_column`, `conversion`, `derived_assembly` kind;
      clarify path root.
- [ ] Add the bounded FLEURS `Range`/`tarfile` fetch design and select short clips;
      include CC-BY-4.0 attribution; no whole-split download; no `datasets` install.
- [ ] Specify binary PCM framing or adopt the official ctypes binding; benchmark/record
      transport overhead.
- [ ] Specify the frozen-tick replay scheduler and the coalescing/finalization rules;
      add the slow-decode test.
- [ ] Add the publication consent/redaction decision for private personal and interview
      context; add the automated privacy/identity scan.
- [ ] Fix the documented test command; add `.gitignore` before dispatch; stage explicit
      paths.
- [ ] Precheck cached model paths/GGUF metadata/SHA and record the actual backends.

If these are done, dispatch Tasks 1–5 with the existing disjoint ownership. None of the
findings requires a different ASR architecture, a different engine, or a new model.
