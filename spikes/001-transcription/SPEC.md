# Spike 001 — transcription feasibility specification

Owner scope approved 2026-10-26. This is a retained research harness, not approval to implement the full app. Authority: [requirements](../../docs/requirements.md), [research](../../docs/analysis/2026-10-26-live-asr-and-browser-privacy.md), and the owner's subsequent approval to test both installed models and retain spikes/tests/findings. [Preflight](review/preflight.md) informed the integration details below.

## Question and deliverables

Measure whether multilingual Parakeet batch decoding can provide useful partial results using fixed-start growing windows and LocalAgreement-2. Compare endpoint-only decoding and genuine Nemotron native streaming on the same small English/Spanish fixtures. Retain code, tests, provenance, event traces and findings here. No acceptance threshold or production model choice is approved. Tiny-fixture results are feasibility evidence, not a model leaderboard.

Retain a separate Natively/HackerRank claim trace under `../002-hackerrank-claims/`. Firefox remains a candidate, not an automatic capture workaround. Prefer invisible where demonstrably possible and disguised where not; neither is a runtime claim until tested.

## Global constraints

- No microphone, live call, interview participation, LLM inference, private-file upload, new model download or system-wide installation. Small licensed public fixture and pinned engine dependency downloads are permitted inside the project.
- Reuse cached Q8_0 Parakeet v3 and Nemotron 3.5 streaming models. No weights, private invitation identifiers, credentials, `.omp/` state or absolute home/cache paths in published artifacts. Generalize personal health/candidacy details in public prose while preserving functional requirements and the HackerRank product scenario.
- Engine pin: `handy-computer/transcribe.cpp` revision `8facde6fcd8fb9caa585a5788ab450df6e8ec7db`. Official docs/help first; relevant headers/implementation are authorized when needed. Build/source caches under this spike's ignored `.cache/` or `.tools/`; no host installs. Evaluate the official stdlib-only Python ctypes binding before inventing a helper/ABI. Native structs use official initializers and returned strings are copied before the next native call.
- One loaded model per arm/process; separate load, constructor, warmup and call timings. Reuse it across fixtures and partials, resetting stream/session state between trials. Compute is serialized; this is not a two-channel throughput/capture test.
- Decode only arrived audio, with a prefix frozen before each call. Real replay uses monotonic time. Coalesce stale partial jobs; prioritize finalization. Simulated/fake clocks must be labelled and cannot populate real measured latency fields.
- Fixture boundaries are **oracle endpoints**, not tested VAD. No independent gold word timings exist: word-end/display latency is unsupported, not derived from model timestamps as truth.
- Retain normalized WER with raw/normalized text and S/D/I counts, revisions, stable/final text, load/call/queue/replay timings and source/model/build fingerprints. Missing metrics are null/unsupported with explanation, never fabricated zeroes. Native timing values of zero mean unknown; stream calls must not inherit stale batch timings.
- Runtime backend evidence is required for hardware claims; a Metal build flag alone is insufficient. Measured arms run sequentially after build/test workers are idle.
- Public `fabzter/escalier` creation/push is approved after privacy and personal Git-identity audit. No license choice, force push, release or version bump. Stage explicit paths; never accidentally publish caches.
- Retain spikes, tests, plans and reviewed findings. No skill-scratch deletion. Authored edits use write/edit tools. Workers do not commit or spawn subagents.

## Python backend contract

`backend.py` exports this standard-library interface; internal bindings may load the pinned project's official Python binding without installing it globally:

```python
class Engine:
    def __init__(self, model_path, *, library_path=None, language="auto",
                 threads=4, use_gpu=True): ...
    @property
    def info(self) -> dict: ...
    def transcribe(self, samples, *, sample_rate=16000, language=None) -> dict: ...
    def start_stream(self, *, feed_chunk_ms=1120,
                     att_context_right_frames=3, language=None,
                     commit_policy="stable-prefix", agreement_n=2) -> None: ...
    def feed(self, samples, *, final=False) -> dict: ...
    def close(self) -> None: ...
```

Samples are finite mono float PCM at 16000 Hz. Reject invalid values/rates. Constructor loads once. `library_path=None` performs documented project-local discovery only, never implicit build/download. Language is overridable per batch call/stream; map `auto` to the family-appropriate autodetect sentinel, or omit an inapplicable hint and record that. Record requested/resolved/detected language and LID support; do not reload a model to change a prompt.

`info` includes native `load_ms` (nullable), constructor wall time, engine/model identity, actual backend evidence (or unknown), and capabilities: batch/native_stream/timestamps, languages/LID where exposed. Keep build source/tree, vendored ggml provenance/patches, tool versions/flags, library hash and clean source verification in lock/build metadata; do not assume nonexistent submodules.

`feed_chunk_ms` is caller cadence, NOT a native C API stream field. Right context is cache-aware encoder frames; chosen value must be accepted by the model/extension or fail clearly. Record the selected/accepted context and model default when exposed. Nominal native R=3 and offline R=13 differ in lookahead as well as architecture; label this confound. Commit policy is stable-prefix with agreement 2 where supported, with native committed text distinct from runner word-level LA-2. Do not assume the native policy's units equal runner words.

A result is JSON-serializable with `text` = raw cumulative native full_text (batch: complete hypothesis), `tokens` = `{text,start_ms,end_ms}` rows (nullable times), `decode_ms` = nullable native batch decode component, `final` boolean, plus native `committed_text`, `tentative_text`, `display_text` and `final_text` when exposed. On finalization `final_text` is authoritative raw full_text, even if committed history differs. Preserve revisions/commit timing/buffer state when exposed. Runner independently records call wall time, which includes validation/transport/native compute; do not label it pure GPU decode time. Sanitize nonfinite native metadata and write strict JSON.

One loaded model may own separate/reset batch and stream sessions. Feed before start, start twice while active, feed after finalize and compute after close fail clearly. Nonempty `feed(...,final=True)` feeds then finalizes; empty+final flushes only; empty nonfinal is a clear error. Copy results before another call invalidates native pointers. `close()` is idempotent and safe after errors. Unsupported native streaming never falls back silently to batch. If a custom helper proves necessary, use binary PCM frames rather than JSON float arrays and test EOF/malformed responses/timeout/stderr draining; document why official binding was insufficient.

## Fixture manifest and acquisition

`fixtures/manifest.json`: `schema_version:1`, `sample_rate:16000`, nonempty `fixtures`. Entries:

```json
{
  "id":"unique-safe-id", "language":"es", "asr_language":"es-US",
  "wav":"fixtures/example.wav", "reference":"fixtures/example.txt",
  "wav_sha256":"hex", "reference_sha256":"hex", "duration_s":1.0,
  "source":{"url":"canonical-public-source", "revision":"pinned-id",
            "license":"CC-BY-4.0", "config":"es_419", "locale":"es_419",
            "split":"test", "row":0, "item_id":"source.wav",
            "audio_sha256":"source-bytes-hash", "reference_column":"raw_transcription"},
  "conversion":{"tool":"none"},
  "segments":[{"start_s":0.0,"end_s":1.0,"kind":"oracle_file_boundary"}]
}
```

The approved synthetic code-switch probe additionally permits `language:"mixed"` with `asr_language:"auto"` (native autodetect/no fixed language hint). It must be labelled as an assembly of separate recordings, not natural within-sentence switching, with both source identities/hashes retained in machine-readable provenance. Keep natural and derived fixture results separate in headline interpretation; endpoint per-oracle-segment decoding is not a within-call mixed-language test. Dataset locale and model language hint are distinct metadata.

Paths resolve from the spike root (`Path(run.py).parent`), not CWD/manifest directory; reject traversal and escaping symlinks. PCM16 mono 16000 Hz WAVs and UTF-8 human references; no audioop dependency (Python 3.13). Validate schema/version, unique IDs/paths, hashes, actual duration and ordered nonoverlapping segment coverage of the complete clip. Derived assemblies require explicit derivation and `derived_assembly` segments, not a claim of original dataset boundaries. Default clips must be <=20 seconds; longer-call rollover is out of scope and must fail clearly at a configured smaller test limit too.

FLEURS per-row datasets-server queries currently exceed its scan limit. A verified alternative is bounded HTTP Range prefix acquisition of test.tar.gz, streamed with tarfile `r|gz`, with TSV filename matching (tar order is not TSV row order). Candidate pin `google/fleurs` `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, configs en_us/es_419. Verify CC-BY-4.0 and fetch direct test.tsv plus at most a bounded 4–8 MiB prefix per locale, selecting complete short members. Require HTTP 206/content-range before accepting bounded acquisition; do not fall back to whole-split download. Stop after needed complete members, handling truncated archive tail safely. Record canonical source/revision/filename/TSV row/hash, never transient signed URLs. An alternative small licensed per-clip source is permitted if documented.

Fetch refuses silent overwrite of modified curated files; provide verify-only or explicit alternate output. Include license attribution, source hashes and conversion command/version (or none), plus offline corrupt-copy/path/schema validation tests. Never download a full dataset/model or install host packages.

## Policy, replay and metric definitions

CLI `run.py --help`: model/library paths, manifest, arm, output, repeats, warmup, fixture filter, per-fixture language override if needed, partial interval, max window, feed cadence/right context/commit policy, clock mode. Record all effective settings; reject output collisions unless explicitly requested.

Arms: `endpoint`, `hybrid`, `native-stream`. Real-paced scheduler: scheduled ticks come from the audio clock. Before a decode freeze `prefix_end=min(selected_tick,arrived)`; never extend it during the call. After a slow call, coalesce missed ticks to the latest eligible tick, recording selected/completed/coalesced ticks, frozen audio horizon and lag. At end, bypass pending partials and finalize full arrived audio. Native streaming must feed every arrived sample exactly once in order, even if caller chunks are processed late; never drop stream audio when coalescing display requests. Tests use slow fake-clock decodes to prove these rules.

Runner LocalAgreement-2 compares NFC/casefolded whitespace words with Unicode punctuation ignored and accents/ñ preserved; native token policies remain separately labelled. Preserve append-only stable history; record conflicts explicitly. Final text may correct it without erasing history. WER normalizer v1: NFC + casefold, Unicode punctuation replaced by spaces, whitespace collapse, accents/ñ retained, digits unchanged (no number expansion). Not equivalent to vendor WER normalization. Deterministic Levenshtein tie-breaking and S/D/I; empty-reference WER null, with counts preserved. Report per-trial and micro-aggregate errors/reference count, not just mean ratios.

`first_partial_ms` and `first_stable_ms`: first nonempty result arrival relative to first fixture sample arrival. `final_after_audio_end_ms`: final return minus fixture audio-end arrival. `call_wall_ms`: runner monotonic elapsed around the call. Queue lag: call start minus chosen scheduled arrival. Word-end/display latency stays null with a no-gold-timing explanation. Neither these fields nor nominal chunk+lookahead are a live-call promise.

Results: schema_version, unique trial IDs, UTC timestamp, sanitized invocation/effective settings, Git commit and executed source fingerprints, library/source/build/model/fixture hashes, Python/OS/hardware, clock_mode, load/warmup, per-trial raw events/text/WER and aggregate definitions. Fake/simulated timing values are separate from real measured fields. Strict JSON (`allow_nan=False`), no nonfinite metadata, atomic output write and collision checks. Privacy scanning covers tracked docs/results/lockfiles, private paths/signed URLs/credentials/work identities; permit innocuous documentation of ignored-directory names.

## Evidence gates

1. Unit red/green evidence and tamper tests for integrity guards. Standard command from repo root: `python3 -m unittest discover -s spikes/001-transcription/tests -v`; tests add the spike root to sys.path as needed.
2. Pinned local engine builds; both existing model hashes are checked and real inference runs. Cached paths/hashes are already verified in the retained ledger; architecture/backend are still runtime checks.
3. Parakeet endpoint + hybrid; Nemotron endpoint + native stream; warmup and two measured repeats where practical. One loaded model per arm. Report blockers rather than fake success; label the native-vs-offline context confound.
4. Independent task spec/quality review and integrated branch review, with covering retests after fixes.
5. Commit harness before final recorded runs, or prove byte equality to its committed artifact. Do not claim an archive was tested without proving loaded paths.
6. Retain FINDINGS/results with commands and limitations; scan public privacy and all Git identities; verify remote visibility and pushed SHA.
