# Spike 001 — transcription feasibility

Status: **four real-model arms measured on small fixtures; broad final integration
review and scoped documentation re-review complete.** This is a retained research
harness, not a full-app implementation or a model leaderboard.
The authoritative technical contract is [SPEC.md](SPEC.md); execution ownership and
current task state are in [PLAN.md](PLAN.md) and
[review/progress.md](review/progress.md).

## Question

Measure whether the cached multilingual Parakeet batch model can provide useful partial
results with fixed-start growing windows and LocalAgreement-2, compared with
endpoint-only decoding and genuine Nemotron native streaming on the same small
English/Spanish fixtures. Retain normalized WER, revisions, timings and limitations.

No acceptance threshold, production model choice or live-call latency promise is
approved. Results are feasibility evidence on synthetic/public short clips. The
native-stream right-context setting (R=3) and the offline model's R=13 setting differ in
lookahead as well as architecture, so a comparison must carry that confound label.

## Prerequisites

- macOS on Apple Silicon; the owner's observed host is an M2 Pro with 32 GiB RAM. The
  actual backend is a runtime observation, not inferred from a Metal build flag.
- Python 3.13 standard library for the harness. No `audioop` dependency.
- Pinned `handy-computer/transcribe.cpp` revision
  `8facde6fcd8fb9caa585a5788ab450df6e8ec7db`, built into a project-local artifact under
  the ignored `.tools/`/`.build/` directories with an installed compiler/CMake. No host
  package installation.
- Both already-installed cached Q8_0 model artifacts (Parakeet v3 and Nemotron 3.5
  streaming), reused in place. Supplied model paths are local inputs; weights are never
  copied into the repository. One loaded model per arm/process.
- A small FLEURS-derived fixture slice with provenance, CC-BY-4.0 attribution, hashes
  and oracle endpoint labels. Acquisition is bounded (HTTP Range prefix plus direct
  TSV/filename matching), not a whole-split download.
- No microphone, live call, interview access, LLM inference or new model download.

## Harness layout

The final names are owned by the individual implementation slices:

- `backend.py` — standard-library `Engine` adapter over the pinned native library.
- `run.py`, `policy.py`, `metrics.py` — replay runner, agreement/coalescing policy and
  metric definitions.
- `fixtures/` — manifest, short licensed WAVs/references and provenance.
- `tools/` — engine build/build-metadata helpers, fixture fetcher and
  `audit_public.py`.
- `tests/` — standard-library `unittest` coverage, including fake-engine/fake-clock
  cases and the public-artifact scanner.
- `review/` — retained preflight, resolutions, task reports and the progress ledger.

## Backend contract (summary)

[SPEC.md](SPEC.md) is authoritative. Public shape:

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

Samples are finite mono float PCM at 16 kHz. Constructor loads once; language is
overridable per call/stream. `library_path=None` performs documented project-local
discovery only, never an implicit build or download. `feed_chunk_ms` is caller cadence,
not a native stream field; `att_context_right_frames` is an encoder-frame setting. Native
committed/tentative text is distinct from runner word-level LocalAgreement-2. Unsupported
native streaming must fail clearly, never fall back silently to batch. `close()` is
idempotent.

`info` reports engine/model identity, capability flags, nullable native load time,
constructor wall time and actual backend evidence (or unknown). Native timing zero means
unknown; call wall time includes validation/transport/native compute and is not labelled
pure decode time. Results preserve raw cumulative `full_text`, token rows with nullable
times, committed/tentative/final text where exposed, and strict JSON with no nonfinite
metadata.

## Manifest and arms

`fixtures/manifest.json` is schema version 1 at 16 kHz. Each fixture records language and
ASR prompt, WAV/reference paths and SHA-256 values, duration, source revision/license/
row/filename metadata, conversion and oracle-boundary segments. The manifest is not a
VAD claim. Clips are short by default; over-limit windows fail clearly rather than
silently rolling over.

Arms: `endpoint`, `hybrid` (runner word-level LocalAgreement-2) and `native-stream`.
The replay scheduler freezes the prefix end before each call; stale partial requests are
coalesced; finalization has priority; native streaming still receives every arrived
sample exactly once and in order. Fake-clocked tests must not populate real measured
latency fields.

## Metrics and cautions

- Record load, constructor, warmup and call timings separately; reuse one loaded model
  across fixtures/partials, resetting stream state between trials.
- Keep raw/normalized reference and hypothesis text with S/D/I counts and revisions.
- Normalizer v1: NFC + casefold, Unicode punctuation to spaces, whitespace collapse,
  accents/ñ retained, digits unchanged. This is not vendor WER normalization.
- Report per-trial counts plus micro-aggregated errors/reference count, not only a mean
  ratio. Empty-reference WER is null.
- `first_partial_ms`, `first_stable_ms` and `final_after_audio_end_ms` are defined in
  SPEC. Word-end/display latency remains null: no independent gold word timings exist.
- Record queue lag/coalescing and frozen audio horizons. Simulated/fake timings stay in
  separate fields.
- Do not compare across different fixtures, languages, models or context settings
  without recording those differences. Tiny-fixture output is not a leaderboard.
- A native committed-text policy is not the runner's word-level agreement. Keep the
  labels separate.

## Commands

The integrated entry points are available; `--help` describes their current flags.
Exact recorded real-model invocations and fingerprints are in
[results/EXECUTION.md](results/EXECUTION.md).

```bash
python3 spikes/001-transcription/tools/build_engine.py --verify-only
python3 spikes/001-transcription/run.py --help
python3 spikes/001-transcription/tools/fetch_fixtures.py --verify-only
```

A run receives explicit model/library paths, the manifest, arm, output path, repeats,
warmup, fixture filter, optional language override and the partial/context/clock
settings described in SPEC. Reject output collisions unless explicitly permitted.

## Tests and evidence status

From the repository root:

```bash
python3 -m unittest discover -s spikes/001-transcription/tests -v
```

Tests add the spike root to `sys.path`; discovery alone does not. The canonical
content-scan and expected-identity audit commands are documented once in
[AGENTS.md](../../AGENTS.md#verification-commands). The scanner is a heuristic
public-artifact guard, not a privacy audit. Review records belong under
[review/](review/); completed task reports, the broad integration review and the
fix report are retained there.

Measured [findings](FINDINGS.md) and [selected JSON](results/README.md) retain four
successful real-model arms with actual Metal backend evidence, warmups separate from
measured trials, and natural/derived results separated. No model choice, full-app
capability, capture visibility or two-channel throughput is established.
