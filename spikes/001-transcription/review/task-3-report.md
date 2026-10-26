# Task 3 report — licensed bilingual fixtures and provenance

Status: **DONE** (slice complete; isolated fixture tests and the full root
discovery command are green).

Date: 2026-10-26. Base: `fc87550aadab04375c2f844dfc0e3a774fd27295`.

## Changed files

Authored/created (nothing staged or committed):

- `spikes/001-transcription/fixtures/manifest.json` — strict schema-v1 manifest,
  four fixtures, relative POSIX paths from the spike root.  The single documented
  value extension is `language="mixed"` / `asr_language="auto"` for the mixed
  fixture; all other fields follow the SPEC schema exactly.
- `spikes/001-transcription/fixtures/manifest_tools.py` — stdlib-only validator:
  exact keys, safe confined paths, hashes, PCM16 mono 16 kHz layout, duration,
  ordered contiguous oracle/derived segments.
- `spikes/001-transcription/fixtures/README.md` — attribution, source pins,
  conversion/derivation, exact regeneration and verification commands.
- `spikes/001-transcription/fixtures/NOTICE-FLEURS-CC-BY-4.0.txt` — required
  CC BY 4.0 attribution and change notice.
- `spikes/001-transcription/fixtures/en_us_10233995782544396174.{wav,txt}`
- `spikes/001-transcription/fixtures/es_419_10149016836336603986.{wav,txt}`
- `spikes/001-transcription/fixtures/derived_en_us_10233995782544396174_repeat2.{wav,txt}`
- `spikes/001-transcription/fixtures/derived_en_us_es_419_switch.{wav,txt}`
- `spikes/001-transcription/tools/fetch_fixtures.py` — bounded-Range acquisition,
  direct TSV, conversion, atomic/no-clobber writes, `--verify-only`, `--dry-run`,
  `--output-dir`, explicit `--force`.
- `spikes/001-transcription/tests/test_fixtures.py` — 36 offline tests.
- `spikes/001-transcription/review/task-3-review.md` — preserved independent
  review report (verbatim handoff).
- `spikes/001-transcription/review/task-3-report.md` — this report plus fix round.

Additive follow-up: the mixed EN→ES switch fixture was added after the initial
slice from the already-curated PCM clips, without changing the two original
fixtures or the repeated fixture.  Schema values were coordinated with
`asr-runner` (it delegates validation to `manifest_tools.py` and passes
`asr_language` through), and `asr-engine` confirmed `auto` maps to the native
NULL/auto hint.  No new source row, dataset member or private audio was added.

Downloaded source members/prefixes/TSVs remain only under the ignored
`spikes/001-transcription/.cache/`; no cache or temporary staging output is
tracked.

## Verified source and license

- Dataset: FLEURS (Google Research), pinned revision
  `70bb2e84b976b7e960aa89f1c648e09c59f894dd`.
  - Canonical page: <https://huggingface.co/datasets/google/fleurs>
  - Card metadata says `license: cc-by-4.0`. Retrieved card at the pinned
    revision: <https://huggingface.co/datasets/google/fleurs/raw/70bb2e84b976b7e960aa89f1c648e09c59f894dd/README.md>
  - Maintainer confirmation: <https://huggingface.co/datasets/google/fleurs/discussions/2>
    (“Yes cc-by-4.0”, 2022-05-26).
- License deed: <https://creativecommons.org/licenses/by/4.0/>
- Paper/citation: Conneau et al., FLEURS, <https://arxiv.org/abs/2205.12446>
- Pinned configs/splits are `en_us` and `es_419`, `test`.
- Source rows are 0-based data rows in the direct `test.tsv` (no header):
  - `en_us` row 518, `10233995782544396174.wav`
  - `es_419` row 322, `10149016836336603986.wav`
- TSV SHA-256 pins:
  - `en_us`: `74c046239374deeb60fa63f258f907388093a32bcaa3140965f70ef05c79f7ca`
  - `es_419`: `d107a93a4f54a18ac25cd470bb4cdadce14fb075b0c1d1542258e274d209ec09`
- Source member SHA-256 (`source.audio_sha256`):
  - `en_us`: `bfa2f3fb72a05cbcb7c0000a460435f2d0eedca7c5cc90f01aacc89127df7f63`
    (276,538 source bytes)
  - `es_419`: `13b06188bd62a1a63ed350e6fe1a1ee8518db1ea7bc8f75d72849ca023de7c32`
    (361,018 source bytes)

The acquisition route was the preflight-verified one: direct small TSV download,
then one bounded HTTP Range prefix per locale (8,388,608 bytes), requiring
**HTTP 206** and a matching `Content-Range` (`0-8388607/289851356` for en_us,
`0-8388607/582112372` for es_419). No dataset-server row API and no whole-split
download were used. The truncated prefix is read with `tarfile` `r|gz`; tar order
is not TSV order, so members are matched by filename to the pinned TSV row and
only complete members are accepted.

## Fixture inventory and sizes

| Fixture | Language / ASR hint | Duration | WAV bytes | Ref bytes |
|---|---|---:|---:|---:|
| `fleurs-en-us-10233995782544396174` | en / en-US | 4.320 s | 138,284 | 87 |
| `fleurs-es-419-10149016836336603986` | es / es-US | 5.640 s | 180,524 | 66 |
| `derived-en-us-10233995782544396174-repeat2` | en / en-US | 8.640 s | 276,524 | 174 |
| `derived-en-us-es-419-switch` | mixed / auto | 9.960 s | 318,764 | 153 |

- Total audio duration: **28.560 s**. Every default fixture is ≤20 s.
- WAV + reference bytes: **914,576**; including `manifest.json` (5,334 bytes):
  **919,910** output bytes.
- FLEURS source WAVs are mono 16 kHz `WAVE_FORMAT_IEEE_FLOAT` (32-bit, tag 3).
  The stdlib converter recorded as
  `python3.13 stdlib float32-to-pcm16 mono/16000 v1` clips to `[-1,1]`, scales
  by 32767 with rounding, and writes PCM16 mono 16 kHz WAVs via `wave`. No
  `audioop` and no external converter.
- The repeated fixture is two back-to-back copies of the complete English clip;
  its reference is the source `raw_transcription` repeated twice with a space.
  It uses two `derived_assembly` segments and a non-“none” conversion tool.
- The mixed fixture is the complete English clip followed by the complete
  Spanish clip, with reference `en raw_transcription + " " + es raw_transcription`.
  It is an explicitly synthetic switch between **two different recordings and
  speakers**, not a natural mid-sentence switch and not a claim about one.  It
  uses two `derived_assembly` segments, `language="mixed"` and
  `asr_language="auto"`; its singular `source` object records the first (English)
  segment.  Both source configs, rows, item IDs and `audio_sha256` values are in
  the machine-readable `conversion.tool` record
  (`sources=<config>:<row>:<item>:<sha256>;…`), repeated in
  `fixtures/README.md`.  It was assembled from the already-curated PCM clips; no
  new source row, dataset member or private audio was added for it.
- Original fixtures use one `oracle_file_boundary` segment from 0 to duration.
  These are harness/file boundaries only — not VAD, not gold word timing, and
  not display-latency truth.
- `asr_language` is `en-US` / `es-US` for single-language fixtures and `auto` for
  the mixed fixture.  `asr-engine` confirmed `auto` reaches the cached Nemotron
  native empty/NULL language hint (no forced prompt, no model reload);
  `asr-runner` confirmed it delegates manifest validation to
  `fixtures/manifest_tools.py` and passes `asr_language` through unchanged.
- `reference_column` is `raw_transcription` (human-authored FLEURS reference text
  plus one trailing newline).

## Exact regeneration / verification

From the repository root:

```sh
# Offline only (no network): schema, confinement, hashes, WAV layout, duration,
# segments, license/provenance files.
python3 spikes/001-transcription/tools/fetch_fixtures.py --verify-only

# Bounded regeneration/compare; refuses modified tracked files.
python3 spikes/001-transcription/tools/fetch_fixtures.py
```

Observed:

```text
$ python3 spikes/001-transcription/tools/fetch_fixtures.py --verify-only
verified 4 fixtures, 914576 bytes, 28.560 s
```

A pre-F1 regeneration run reported all eight assets and the manifest unchanged.
F1 hardening then changed only the mixed manifest conversion string; per the
review instruction no re-download/re-fetch or WAV/reference rewrite was done in
the fix round. The fixture test asserts the fetch generator's mixed conversion
string equals the manifest record, and `--verify-only` revalidated every asset
hash after the edit. A pre-F1 staged regeneration under
`.cache/fixtures-regenerated-verify2` produced byte-identical eight assets and
equal WAV/reference hashes.

The fetch preflight refuses to overwrite any differing existing file (no
partial regeneration); `--force` is explicit. `--output-dir` stages under a
project-local alternate path.

## TDD evidence

Red, before implementation (root discovery command from SPEC):

```sh
python3 -m unittest discover -s spikes/001-transcription/tests -v
```

Observed: `Ran 2 tests ... FAILED (errors=2)`; the fixture test failed with
`ModuleNotFoundError: No module named 'fetch_fixtures'` (the other error was an
unrelated sibling module import at that moment). Red was expected because the
fixture tools and validator did not exist.

Green, offline:

```sh
python3 -m unittest spikes/001-transcription/tests/test_fixtures.py -v
python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_fixtures.py' -v
```

Observed: **Ran 36 tests ... OK** for both commands.

Coverage includes: exact schema keys/version/sample rate; unknown/missing/duplicate
fields; duplicate JSON keys and nonfinite JSON; safe IDs; traversal, absolute,
Windows-drive, dot-component and symlink-escape rejection (including a valid WAV
outside the root and a symlink alias to a duplicate resolved path); duplicate
IDs/paths; WAV channels/rate/sample-width/duration guards; audio and reference
hash mismatches; invalid/empty UTF-8 references; ordered contiguous segment
coverage and kinds; derived-assembly semantics (including the mixed EN→ES switch,
its exact concatenated reference/frame count, and rejection of a derived segment
with conversion tool `"none"`); machine-readable two-source provenance in the
mixed `conversion.tool`; source/license provenance text; fetch Content-Range
parsing; non-206/no-body-read and bad-Content-Range rejection; complete-member
extraction before a truncated tail plus rejection of truncated/missing members;
no-clobber/atomic write behavior and no partial write on refusal;
float32-to-PCM16 conversion and clipping. The corrupt-copy tests mutate only
temporary copies and assert the curated original’s hash is unchanged.

Integration note: after the other workers' modules landed (including the runner
F3 test-fixture update), the full root discovery command above ran
**181 tests ... OK**, including all 36 fixture tests.

Public-artifact scan on this slice:

```sh
python3 spikes/001-transcription/tools/audit_public.py \
  spikes/001-transcription/fixtures \
  spikes/001-transcription/tools/fetch_fixtures.py \
  spikes/001-transcription/tests/test_fixtures.py \
  spikes/001-transcription/review/task-3-report.md \
  spikes/001-transcription/review/task-3-review.md
```

Observed: `scanned 16 file(s)` / `no public-artifact findings`.

## Self-review and concerns

- Schema is intentionally exact; unknown fields are rejected to catch drift
  between this fixture producer and the Task 2 runner.
- Paths resolve from the spike root, not CWD/manifest directory; escaping
  symlinks and traversal are rejected before hashing.
- Fetch failure modes are explicit: a non-206 response is rejected without
  reading the whole body, source/TSV hashes must match pins, and truncated tar
  members are never accepted.
- Concern (minor): the two derived fixtures add 18.60 s to a default run that
  would otherwise be 9.96 s (total 28.56 s). Both remain ≤20 s and are useful
  for explicit-assembly, repetition and synthetic EN→ES switch coverage; the
  runner’s fixture filter can exclude either by ID if the default run must stay
  at the two original clips.
- No timed inference, microphone/live-call access, private audio, whole-split
  download, host install, new model download, commit, or subagent was used.

## Fix round 1 — independent review

The independent review is preserved unchanged at
`review/task-3-review.md`. Findings were checked against the working code and
fixed as follows (no commit, staging, index change, network fetch, asset
rewrite, runner API change or SPEC edit):

- **F1 (medium) — machine-readable two-source provenance.** The mixed fixture's
  `conversion.tool` now carries both complete source records in the form
  `sources=en_us:518:10233995782544396174.wav:<sha256>;es_419:322:10149016836336603986.wav:<sha256>`.
  The fetch generator constant, manifest, README and NOTICE were updated. A
  test asserts exact generator/manifest equality and both source identities and
  SHA-256 values. The singular `source` object still records the first segment;
  the second source is now machine-readable in the published conversion record.
- **F2 (medium) — offline acquisition rejection/extraction tests.** Added
  fake-response tests proving `_fetch_prefix` rejects HTTP 200 without reading
  the body (`read_calls == 0`) and rejects a mismatched `Content-Range` total
  before reading. Added in-memory tar.gz tests proving a complete wanted member
  is accepted before a truncated tail, while a member truncated mid-payload or
  a missing member raises `FetchError`. No network.
- **F3 (low) — derived assembly requires real derivation.** The validator now
  rejects any `derived_assembly` segment when `conversion.tool` normalizes to
  `"none"`, for both single- and multi-segment fixtures. Tests cover the mixed
  multi-segment case, a single derived segment, and `" none "`. The runner's
  synthetic language test was updated by `asr-runner` to use a non-none tool;
  no runner API change.
- **F4 (low) — normalized/duplicate path bypass.** Path validation now rejects
  any lexical `.` component before `PurePosixPath` normalization, and
  `validate_manifest` also rejects duplicate **resolved** paths. Tests cover
  `fixtures/./<existing>.wav` and a symlink alias to the same WAV.
- **F5 (low) — escape test false-green.** The test now points at a valid WAV
  outside the temp spike root and asserts the specific `escapes spike root`
  message. Guard tamper evidence (temporary copy with the containment guard
  removed) produced:
  `TAMPER EVIDENCE: guard removed -> validation ACCEPTED escaping symlink (new test would fail)`.
- **F6 (cross-task) — aggregate/endpoint honesty.** Fixture README now states
  that a default micro-aggregate mixes natural and derived material, recommends
  the two original IDs for a natural-only headline, and notes that the Task 2
  endpoint arm decodes derived fixtures per segment, so the mixed fixture does
  not exercise within-call switching there. Natural-vs-derived aggregate
  separation remains coordinator final-analysis responsibility.
- **F7 (low) — wrong table direction.** README now points to the pinned source
  metadata table **below** and to the manifest conversion record.
- **F8 (info) — reviewed diff.** `spikes/001-transcription/.tools/reviews/task-3.diff`
  exists (102,322 bytes); the earlier root path/view was a scout assignment
  issue, not missing repository evidence. The review file was preserved at the
  requested tracked path.

Test-first evidence before the fixes: the expanded fixture suite ran 35 tests
with 4 failures — F1 provenance, F3 derived+none acceptance, F4 dot-component
acceptance, and one initial F2 test-construction mistake (the truncation cut was
too large); the F2 constructor was corrected to cut at the 512-byte tar header
plus 1024 payload bytes. Guard tamper evidence for the acquisition check: a
temporary copy with the non-206 guard disabled read the fake body
(`read_calls=1`) and raised the wrong error, while the fixed test expects zero
reads and the bounded-Range refusal.

Covering green commands after fixes:

```text
$ python3 -m unittest spikes/001-transcription/tests/test_fixtures.py -v
Ran 36 tests ... OK

$ python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 181 tests ... OK

$ python3 spikes/001-transcription/tools/fetch_fixtures.py --verify-only
verified 4 fixtures, 914576 bytes, 28.560 s
```

Remaining concerns: F6 aggregate separation is coordinator-owned; the singular
manifest `source` object for the mixed fixture remains (full two-source
provenance is in `conversion.tool` and README); SPEC's approved mixed/auto and
natural-vs-derived/endpoint note is coordinator-owned and was not edited here;
the two derived fixtures add 18.60 s to the default 28.56 s run and can be
excluded by `derived-*` filter. No fixture WAV/reference bytes were rewritten in
this fix round; only the mixed manifest conversion string, validator, tests,
fetcher constant and docs changed.
