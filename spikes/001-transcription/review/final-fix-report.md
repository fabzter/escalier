# Final integration documentation fix report

Date: 2026-10-26. Worker: single consolidated documentation fix wave.
Input: `final-integration-review.md` findings FI-01..FI-06 and its residual
dispositions, applied at HEAD `23346c1bc5268923cfcacffeffdc6963459ac679`.

Scope was documentation only. No implementation, test, fixture, manifest,
engine lock, measured result JSON or historical report was modified. No model
was loaded, no inference or test suite was rerun, and no GUI, browser, server,
event-tap or permission action was performed. No commit, stage, tag, ref or
subagent was used. This report is not a scoped re-review verdict and claims no
PASS, audit PASS or publication readiness; the scoped re-review, the
privacy/reachable-history audit and the parentless-root publication plan remain
open gates, and every interactive runtime matrix remains NOT RUN.

## Dispositions

| Finding | Disposition | Changed surface |
|---|---|---|
| FI-01 | Fixed | `AGENTS.md:4-8`; `docs/README.md:12,23,31`; `docs/requirements.md:77,114`; `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md:3,7,13,206,208,214,230` |
| FI-02 | Fixed | `spikes/001-transcription/FINDINGS.md:89` (2105.1 → 2150.6) |
| FI-03 | Fixed | `README.md:33-36`; `spikes/README.md:8`; `spikes/001-transcription/README.md:3-4,145-147`; `spikes/001-transcription/results/README.md:8-9`; `spikes/001-transcription/review/progress.md:37,108`; `spikes/001-transcription/review/final-review-brief.md:3-4`; `docs/README.md:25-27` |
| FI-04 | Fixed | `spikes/001-transcription/fixtures/README.md:55` (919,910 → 920,091) |
| FI-05 | Fixed | `spikes/001-transcription/fixtures/README.md:121-125` (obsolete literal replaced) |
| FI-06 | Fixed | `spikes/002-hackerrank-claims/SOURCES.md:28` (lines 10–25 → lines 2, 8, 10–25) |

### FI-01 — measured-ASR status surfaces

Public status surfaces now state that Spike 001 has four measured cached-model
ASR arms on small licensed fixtures and point at `FINDINGS.md` and
`results/EXECUTION.md`. Capture, focus and stealth runtime, full-app capability
and live-call results remain unmeasured/NOT RUN. In the requirements baseline,
the OBS-01 treatment keeps the owner statement and ID unchanged and separates
the owner's Handy observation from the retained small-fixture probe; the design
status sentence now records measured ASR while capture/focus/stealth stay
unmeasured. In the analysis document, a dated `Measurement update
(2026-10-26)` paragraph was added before the Probe A heading, and the stale
"no measured" sentences at lines 3, 7, 13, 206, 212 (now 214) and 228 (now
230) were corrected while preserving the historical research content and the
2026-10-25 snapshot untouched.

### FI-02 — timing-table cell

`FINDINGS.md:89` Parakeet hybrid / Spanish first stable text is now `2150.6`
ms, the mean of the two measured trials `2160.008` and `2141.224`
(2150.616 → 2150.6). The whole 24-cell arrival-timing table was recomputed
from the four raw JSONs, not just this cell; see checks.

### FI-03 — completed-spike and pending-review status lines

The `docs/README.md` native rows 003/004/005 now read
"headless/build/signing … reviewed; runtime … NOT RUN" and link to the retained
`README.md` entries instead of `PLAN.md`. Root `README.md`, `spikes/README.md`,
`spikes/001-transcription/README.md`, `results/README.md`,
`review/progress.md` and `review/final-review-brief.md` now record the broad
review and this fix wave with links to existing artifacts only; no scoped-PASS,
audit-PASS or publication claim was added, and no link targets a nonexistent
future scoped-review file. `review/progress.md` keeps every historical entry
unchanged and gains one appended continuity entry. All interactive matrices
remain NOT RUN.

### FI-04 — fixture byte total

`fixtures/README.md:55` now reads 920,091 bytes including `manifest.json`
(914,096 WAV + 480 reference + 5,515 manifest = 920,091, verified with
`wc -c`). The 914,576 WAV/reference total is unchanged.

### FI-05 — obsolete conversion literal

The quoted assembly step now matches the current `conversion.tool` form
(`switch-concat v1 sources=… pcm v1`) and refers to `manifest.json`'s
`conversion.tool` record for the full `sources=<config>:<row>:<item>:<sha256>`
list instead of duplicating a drift-prone literal. `fixtures/manifest.json` and
`fixtures/manifest_tools.py` were not modified.

### FI-06 — manifest citation range

`SOURCES.md:28` now cites `natively-browser/src/manifest.json` lines 2, 8 and
10–25, covering `manifest_version: 3` (line 2), the `activeTab`/`scripting`
permissions (line 8) and `optional_host_permissions` (lines 10–25, with
`https://www.hackerrank.com/*` at line 15). The observation text is unchanged
and the pinned snapshot was read, not re-fetched.

## Checks performed

All commands were run from the repository root; no suite, build or model load.

- **Changed-path allowlist:** `git diff --name-only` lists exactly the 13
  intended documentation paths shown below; `git status` shows those files
  modified plus untracked `review/final-integration-review.md` (pre-existing
  review input) and this new `review/final-fix-report.md`.
- **Timing table recompute (strict raw JSON):** for each of the 8 arm/clip
  rows, both measured trials per metric were averaged and compared to the
  documented cell — 24 cells, 0 failures. Negative control: the pre-edit
  value `2105.1` failed (`doc=2105.1 calc=2150.6`); the corrected `2150.6`
  matches `mean(2160.008, 2141.224) = 2150.616 → 2150.6`.
- **Fixture byte math:** `wc -c` gives WAV 914,096 (138,284 + 180,524 +
  276,524 + 318,764), reference 480 (87 + 66 + 174 + 153), manifest 5,515;
  914,096 + 480 = 914,576 and 914,576 + 5,515 = 920,091.
- **Stale-current-surface scan:** `git grep` across all tracked `*.md` for
  `final integration review pending`, `final broad review pending`, `final
  integration verdict pending`, `Planned arms`, `task reports are added`,
  `no measured inference result`, `no measured ASR`, `independent
  inference/backend measurements have not run`, `have not established a
  measured inference`, `919,910`, `switch-concat en_us` returns hits only in
  explicitly historical artifacts kept unchanged by design:
  `docs/analysis/2026-10-25-feasibility.md:194` (historical snapshot the
  review ordered preserved) and `review/task-3-{report,review,fix-1-review}.md`
  (historical worker/reviewer records). No current status surface still
  carries a stale claim.
- **Markdown relative links:** scripted check over every `*.md` file —
  69 files, 142 relative links, 0 missing targets after this report exists.
- **Privacy heuristic scan:** `git diff -U0 -- '*.md'` added lines checked for
  absolute home paths, work/personal emails, API keys, tokens, private keys and
  secret-like strings — 0 hits; no trailing whitespace introduced.
- **Whitespace/conflict check:** `git diff --check` exit 0.
- **Measured-source/results immutability:** `git diff --exit-code` over
  `results/*.json`, `fixtures/manifest.json`, `engine.lock.json`, `run.py`,
  `backend.py`, `metrics.py`, `policy.py` is empty; `git status` shows no
  modification under `results/*.json`, the fixture WAV/reference files,
  `manifest_tools.py`, `tests/` or `tools/`. SHA-256 values recomputed after
  the wave are unchanged and still match `results/EXECUTION.md`:
  `parakeet-endpoint.json` `cead9e6366e6534fa14cafb1ca958c516aad9d72f1a9ce9a6b7220727432e640`,
  `parakeet-hybrid.json` `fd79981447b4f381461983b808e4401eb92294c514cee9a94fde08456a30c32d`,
  `nemotron-endpoint.json` `41c16fba5e5bb911c7d2d52b44d2bddd71c3da70cb4e6a4ba19936616a6cc487`,
  `nemotron-native-stream.json` `0d8a259e232e303aec6c5dfa9a73fa5ed36c80afa3ae003e07b82e9ad551de5a`,
  `fixtures/manifest.json` `f6aa1ab5ef83b89a6643f120314ed2fc16e5754d7cbd995d7b5c955e9b933794`,
  `engine.lock.json` `6b2aa39024eaa6f41524350a3e927e5bda457ef61ef2f97c3651822c8919c63f`.

## Changed paths (exact list)

- `AGENTS.md`
- `README.md`
- `docs/README.md`
- `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md`
- `docs/requirements.md`
- `spikes/001-transcription/FINDINGS.md`
- `spikes/001-transcription/README.md`
- `spikes/001-transcription/fixtures/README.md`
- `spikes/001-transcription/results/README.md`
- `spikes/001-transcription/review/final-review-brief.md`
- `spikes/001-transcription/review/progress.md`
- `spikes/002-hackerrank-claims/SOURCES.md`
- `spikes/README.md`
- New: `spikes/001-transcription/review/final-fix-report.md` (this file)

`final-integration-review.md` itself was not modified.

## Intentionally untouched

- `docs/analysis/2026-10-25-feasibility.md` and every `review/task-*` worker
  report/review: historical records of their revision; their stale status
  wording is not a current claim and is retained per the review's residual
  disposition.
- `run.py`, `backend.py`, `metrics.py`, `policy.py`, `manifest_tools.py`,
  `fixtures/manifest.json`, `engine.lock.json`, fixture WAV/reference files,
  all tests, all tools and all four `results/*.json`: measured/committed
  artifacts whose byte fingerprints carry the retained results.

## Remaining gates

The single scoped re-review of this fix wave, the privacy/reachable-public
-history/identity audit, and the parentless-root publication plan remain open.
Nothing here asserts those gates passed, upgrades any NOT RUN runtime row, or
selects a model, threshold, license or assistance policy.
