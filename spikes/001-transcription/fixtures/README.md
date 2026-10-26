# Licensed bilingual fixtures and provenance

This directory holds a deliberately tiny, pinned, human-referenced FLEURS slice
for the transcription feasibility harness.  It is not a benchmark and not a
model leaderboard: four short clips are enough to exercise English/Spanish
batch, partial-window and streaming paths, plus one explicitly synthetic
language switch, without a costly default run.

## License and attribution

The fixtures are derived from **FLEURS** by Google Research and are used under
**Creative Commons Attribution 4.0 International (CC BY 4.0)**:
<https://creativecommons.org/licenses/by/4.0/>.

- Dataset page: <https://huggingface.co/datasets/google/fleurs>
- Pinned revision: `70bb2e84b976b7e960aa89f1c648e09c59f894dd`
- Citation: Conneau et al., *FLEURS: Few-shot Learning Evaluation of Universal
  Representations of Speech*, arXiv:2205.12446
- Required attribution and change notice: [NOTICE-FLEURS-CC-BY-4.0.txt](NOTICE-FLEURS-CC-BY-4.0.txt).
  No endorsement by Google is implied.

## Contents

| Fixture ID | Lang / ASR hint | Duration | WAV bytes | Ref bytes | Source |
|---|---|---:|---:|---:|---|
| `fleurs-en-us-10233995782544396174` | en / en-US | 4.320 s | 138,284 | 87 | FLEURS `en_us` test, row 518, `10233995782544396174.wav` |
| `fleurs-es-419-10149016836336603986` | es / es-US | 5.640 s | 180,524 | 66 | FLEURS `es_419` test, row 322, `10149016836336603986.wav` |
| `derived-en-us-10233995782544396174-repeat2` | en / en-US | 8.640 s | 276,524 | 174 | explicit 2× assembly of the English source clip |
| `derived-en-us-es-419-switch` | mixed / auto | 9.960 s | 318,764 | 153 | explicit EN→ES concatenation: `en_us` row 518 + `es_419` row 322 |

The two original fixtures are **complete** short FLEURS recordings, not trimmed
clips.  The repeated fixture repeats the complete English clip twice, back to
back (no inserted silence), and its reference repeats the source reference with
a space.  The mixed fixture concatenates the complete English clip and then the
complete Spanish clip, back to back, and its reference is the English reference
followed by the Spanish reference.  It is a **synthetic switch between two
different recordings/speakers** for exercising a language change; it is not a
natural mid-sentence language switch and is not evidence about such switches.

The mixed fixture is the one documented schema extension for this slice:
`language` is `"mixed"` and `asr_language` is `"auto"` (the engine maps auto to
its native empty/NULL language hint).  Its singular `source` record points at
the first segment's English source.  Full machine-readable provenance for both
sources — config, row, item ID and `audio_sha256` for each — is carried in the
manifest `conversion.tool` record as `sources=<config>:<row>:<item>:<sha256>;…`
and repeated in the pinned source metadata table below.  Both derived fixtures
remain under the 20 s default limit and are not claimed to be original dataset
boundaries.

`asr_language` values are model-prompt hints.  `es-US` is not a claim that the
FLEURS `es_419` locale is US Spanish; the source `config`/`locale` remain
`es_419`.

All four entries are in the default manifest, for 28.560 s of audio and 914,576
bytes of WAV/reference data (920,091 bytes including `manifest.json`).  No clip
exceeds 20 s; long-call rollover is intentionally out of scope.  A runner
fixture filter can exclude the `derived-*` IDs when only the two original clips
are wanted.

Default aggregate caveat: a default run's micro-aggregate therefore mixes
natural and derived material; use the two original IDs for a natural-only
headline.  The Task 2 endpoint arm decodes each derived fixture per segment, so
this mixed fixture does not exercise within-call language switching in that arm
and no such claim is made.

## Source acquisition (bounded, not a whole-split download)

`tools/fetch_fixtures.py` was verified against the pinned revision and uses the
only approved route:

1. Fetch each small `test.tsv` directly from the pinned revision (no dataset
   server row queries) and verify its SHA-256:
   - `en_us`: `74c046239374deeb60fa63f258f907388093a32bcaa3140965f70ef05c79f7ca`
   - `es_419`: `d107a93a4f54a18ac25cd470bb4cdadce14fb075b0c1d1542258e274d209ec09`

   Canonical pinned TSV URLs:

   ```
   https://huggingface.co/datasets/google/fleurs/resolve/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data/en_us/test.tsv
   https://huggingface.co/datasets/google/fleurs/resolve/70bb2e84b976b7e960aa89f1c648e09c59f894dd/data/es_419/test.tsv
   ```
2. Request **one bounded HTTP Range prefix** of `audio/test.tar.gz` per locale,
   at most 8 MiB and at least 4 MiB, and require **HTTP 206** plus a matching
   `Content-Range` header.  A non-206 response is rejected without reading the
   body; the tool never falls back to a whole-split download.
3. Stream the truncated prefix with `tarfile` mode `r|gz` and accept only tar
   members whose extracted length equals the tar header size.  Tar member order
   is not TSV row order; members are mapped by filename to a 0-based TSV data
   row, then the pinned row/item ID is checked.
4. Stop after the selected complete members.  Source members and bounded
   prefixes live in the ignored `.cache/fixtures/` directory; only the small
   converted outputs and this provenance are tracked.

Pinned source metadata:

| Config | Tar total bytes | Selected item | TSV row (0-based) | Source WAV SHA-256 |
|---|---:|---|---:|---|
| `en_us` | 289,851,356 | `10233995782544396174.wav` | 518 | `bfa2f3fb72a05cbcb7c0000a460435f2d0eedca7c5cc90f01aacc89127df7f63` |
| `es_419` | 582,112,372 | `10149016836336603986.wav` | 322 | `13b06188bd62a1a63ed350e6fe1a1ee8518db1ea7bc8f75d72849ca023de7c32` |

`source.audio_sha256` is the SHA-256 of the original tar member bytes.
`wav_sha256` is the SHA-256 of the converted PCM16 WAV.  `reference_column` is
`raw_transcription`; the reference file is that human-authored FLEURS reference
text plus one trailing newline, not ASR output and not a
normalized/vendor-flavored WER text.  FLEURS records read speech against
human-authored FLoRes sentences (human-translated for non-English locales) and
aligns at document/segment level, so these are text references, not independent
verbatim word-level timing annotations.

## Conversion

The FLEURS source members are mono 16 kHz **IEEE-float 32-bit** WAVs
(`WAVE_FORMAT_IEEE_FLOAT`, tag 3).  The standard-library converter in
`tools/fetch_fixtures.py` (recorded per manifest entry as
`python3.13 stdlib float32-to-pcm16 mono/16000 v1`) parses the RIFF chunks,
requires mono/16 kHz/32-bit float, clips to `[-1, 1]`, scales by 32767 with
rounding, and writes canonical PCM16 mono 16 kHz WAVs through the `wave` module.
No `audioop`, external converter, host package, model or private audio is used.
The repeated fixture is produced by an explicitly recorded assembly step
(`; repeat-2 pcm assembly v1`) that concatenates two copies of the PCM payload.
The mixed fixture uses a separate explicitly recorded assembly step
(`; switch-concat v1 sources=… pcm v1`, with the full
`sources=<config>:<row>:<item>:<sha256>` list in `manifest.json`'s `conversion.tool`)
that concatenates the English and Spanish PCM payloads without resampling or
inserted silence.

## Boundaries are oracle endpoints, not VAD or word timings

Each original fixture has one `oracle_file_boundary` segment from `0.0` to the
file duration.  Each derived fixture has two contiguous `derived_assembly`
segments.  These boundaries are file/assembly boundaries supplied by this
harness.  They are **not** voice-activity detection, phrase segmentation, gold
word timings or display-latency truth.  No independent word-level timing oracle
exists for these clips.

## Verify or regenerate

From the repository root (paths resolve from the spike root, not the manifest
directory or CWD):

```sh
# Offline: validate schema, confinement, hashes, WAV layout, durations, segments.
python3 spikes/001-transcription/tools/fetch_fixtures.py --verify-only

# Regenerate/compare.  This performs only bounded Range reads and refuses to
# silently overwrite a modified tracked fixture.
python3 spikes/001-transcription/tools/fetch_fixtures.py

# Optional staging into an alternate project-local directory.
python3 spikes/001-transcription/tools/fetch_fixtures.py \
  --output-dir spikes/001-transcription/.cache/fixtures-regenerated

# Show planned outputs without writing.
python3 spikes/001-transcription/tools/fetch_fixtures.py --dry-run
```

`--force` is required to overwrite differing existing files and is intentionally
not the default.  `--verify-only` has no network access.  `--prefix-bytes` is
constrained to 4-8 MiB.  The default output is this `fixtures/` directory and the
default cache is `.cache/fixtures/` inside the spike.
