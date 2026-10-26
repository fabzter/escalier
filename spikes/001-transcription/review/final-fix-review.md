# Final fix-wave scoped re-review

Date: 2026-10-26. Reviewer: final integration reviewer (single scoped re-review).
Fix freeze: HEAD `54450511648a9c3dd9a12f47f1b5c0f4b657ee93`; base `23346c1bc5268923cfcacffeffdc6963459ac679`; whole-tree diff `spikes/001-transcription/.tools/reviews/final-fix-wave.diff`. The fix commit contains 15 changed paths: the 13 current documentation surfaces, the unmodified broad review, and the new fix report. Working tree was clean before this report; the coordinator's new untracked `review/final-validation.md` was inspected as evidence, not treated as part of the fix commit.

This is the last scoped review of FI-01..FI-06. It is documentation-only: no suite, build, model load, inference, codesign, app launch, GUI, browser, server, event tap, permission/TCC/Keychain action or network access was performed. The coordinator's final headless evidence is accepted as stated; only targeted raw-data checks for FI-02 and FI-04 were repeated.

## Verdicts

- **Fix-wave spec compliance: PASS.** All six findings are ADDRESSED; the edits are confined to current documentation and do not upgrade a runtime, product, stealth, capture, focus, TCC or publication claim.
- **Quality: PASS.** The fixes are minimal and reproducible; the timing table, fixture byte math, manifest quotation, citation range and status links check out. One non-blocking pre-existing wording residual is explicitly retained below; no new Critical or Important finding.
- **Public retained-spike snapshot: READY FOR THE PLANNED PUBLICATION GATE.** This scoped verdict clears the FI-01..FI-06 documentation fix wave, not publication itself. Publication remains conditional on committing the reports/evidence, freezing and re-attesting the final tree, the reachable-public-history/identity audit, the parentless-root creation and the exact approved push. It is not product readiness and grants no runtime approval.

## Finding dispositions

| Finding | Verdict | Current evidence |
|---|---|---|
| FI-01 — stale no-measured-ASR status surfaces | **ADDRESSED** | `AGENTS.md:4-8`; `docs/README.md:12,23,31`; `docs/requirements.md:77,114`; `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md:3,13,206-208,214,228-230`. They state four measured small-fixture cached-model ASR arms, distinguish the owner's Handy observation, point to `FINDINGS.md`/`results/EXECUTION.md`, and keep capture/focus/stealth runtime NOT RUN. |
| FI-02 — hybrid Spanish first-stable timing | **ADDRESSED** | `spikes/001-transcription/FINDINGS.md:89` is `2150.6`. Strict JSON: measured Spanish trials `2160.008` and `2141.224`; mean `2150.616`, rounded `2150.6`; the old `2105.1` is rejected. The diff changes exactly that cell. |
| FI-03 — completed/pending status lines | **ADDRESSED** | `README.md:33-36`; `spikes/README.md:8`; `spikes/001-transcription/README.md:3-4,145-147`; `spikes/001-transcription/results/README.md:8-9`; `docs/README.md:25-27`; `review/progress.md:37,108`; `review/final-review-brief.md:3-4`. Statuses record the broad review and fix wave, say the scoped re-review is still required, and keep 003/004/005 runtime NOT RUN. |
| FI-04 — manifest-inclusive byte total | **ADDRESSED** | `spikes/001-transcription/fixtures/README.md:54-55` now says 920,091. Actual: WAV 914,096 + reference 480 = 914,576; manifest 5,515; total 920,091. NOTICE (2,051 bytes) is separately retained and excluded. |
| FI-05 — obsolete mixed-fixture conversion literal | **ADDRESSED** | `spikes/001-transcription/fixtures/README.md:121-125` now uses `switch-concat v1 sources=… pcm v1` and points to the full `sources=<config>:<row>:<item>:<sha256>` list in `manifest.json`'s `conversion.tool`. The manifest’s current value is `switch-concat v1 sources=en_us:518:…;es_419:322:… pcm v1`; the fixture manifest was not modified. |
| FI-06 — under-inclusive companion permission anchor | **ADDRESSED** | `spikes/002-hackerrank-claims/SOURCES.md:28` now cites `natively-browser/src/manifest.json` lines **2, 8, 10–25**; the observation text is unchanged. No re-fetch or implementation read was needed. |

## Verification performed

### Scope and immutability

- `git diff --name-status 23346c1..HEAD` contains exactly the 15 expected paths; the 13 current docs are the only edited content and the two reports are additions.
- Protected-path diff is empty: no `*.py`, `*.swift`, `*.mjs`, `*.json`, `*.lock.json`, `tests/`, `results/`, `run.py`, `backend.py`, `metrics.py` or `policy.py` change. In particular, the measured result JSON, `fixtures/manifest.json`, `engine.lock.json`, WAV/reference files, tools and tests are untouched.
- The broad report is unchanged: 241 lines / 37,577 bytes, SHA-256 `f3079a89e74f4d16f58f43b89265cb0897143cda547051b6330628578250f167` for both the working file and `HEAD:…/final-integration-review.md`. Its FI findings and residual dispositions were not rewritten.
- The fix report itself says it is not a review verdict and claims no PASS/publication; its dispositions and checks are consistent with the actual diff.

### FI-01 claim check

- Current public surfaces no longer claim “no measured ASR.” Stale-phrase hits are confined to `docs/analysis/2026-10-25-feasibility.md:194` (explicit historical snapshot), historical `review/task-*` records, the broad review quoting the old defect, and the fix report’s negative-control prose. No current AGENTS/docs/requirements/2026-10-26 analysis surface carries the old claim.
- The replacement text says four measured cached-model arms on small licensed fixtures, separates the owner’s Handy observation, and preserves NOT RUN for capture, focus, stealth, live-call and full-app capability. No model winner, threshold, licence, assistance policy or runtime success is selected.
- `docs/requirements.md` keeps OBS-01 and all requirement IDs unchanged; only the treatment/status prose changed. `docs/README.md` links the current status table to retained READMEs, not stale PLAN-only entries.

### FI-02 raw-data check

Strict `json.load(..., parse_constant=reject)` over `results/parakeet-hybrid.json`, filtering `phase == "measured"` and the Spanish fixture, produced `[2160.008, 2141.224]`, mean `2150.616 → 2150.6`. The old `2105.1` negative control is rejected. The `git diff --unified=0` for `FINDINGS.md` contains one changed line and one cell, with the `n=2` table convention unchanged.

### FI-03 status/link check

- 001 is described as four measured small-fixture arms with broad review/fix wave recorded and scoped re-review pending in root, spike, results and progress surfaces.
- 003/004/005 are described as headless/build/signing reviewed with runtime/GUI/hook/recipient evidence NOT RUN; no scoped PASS, audit PASS or publication claim was added.
- The scoped re-review is explicitly listed as still required; no link targets a future `final-fix-review.md` that did not exist at the fix commit.
- All 74 relative links in the changed docs resolve; 0 missing. `review/progress.md` changes only the current integration status line and appends one continuity entry; the substantive historical task entries remain intact.
- No current doc removes a NOT RUN boundary; removed-old-status lines are replaced by narrower “runtime NOT RUN” status lines.

### FI-04/FI-05 fixture check

`wc -c` confirms WAV 914,096, reference 480, manifest 5,515, total 920,091. The four non-NOTICE references are 174, 153, 87 and 66 bytes. The NOTICE is not part of the WAV/reference/manifest subtotal. `manifest.json` and `manifest_tools.py` are unchanged by the fix wave. The README quotation is now an explicit abbreviated reference to the manifest’s current `conversion.tool`, not the obsolete `en_us row 518 + es_419 row 322` literal.

### FI-06 and coordinator evidence

- `SOURCES.md:28` is the only changed line: the citation range is broadened from `10–25` to `2, 8, 10–25`; the observation text is unchanged.
- The coordinator `final-validation.md` (untracked, not part of HEAD) is internally consistent: 204 Python + 36 shell + 54 capture + 80 Node + 69 core + 15 adapter + 12 keyboard Node = **470** cases, zero test failures; engine/fixtures verify-only and 004 static audits reported PASS; three existing packages read back ad-hoc/strict-valid with `TeamIdentifier=not set`; no app launch, inference or runtime claim. The `70` Markdown count is the current tracked set; the fix report’s earlier `69` is a checkpoint count from before all review artifacts were tracked. The final-tree counts must be refreshed after this report and `final-validation.md` are committed.
- The final-validation evidence does not sanitize private development history and does not upgrade any GUI/capture/focus/tap/TCC/browser/HackerRank claim; it explicitly remains test/artifact evidence, not a publication audit.

## Residual adjudication

- The broad review’s residual dispositions are accepted and are not reopened. This wave touched documentation only; it did not alter any measured source, fixture, result or manifest fingerprint, so the earlier “retain” reasons remain valid.
- **Retained non-blocking observation (R-01):** `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md:222` still says 003/004 are “planned/in progress, not validated,” while the same document’s status line and the spike status tables now say their headless/build/signing slices are reviewed and runtime remains NOT RUN. This is pre-existing plan/runtime wording, not a new capability claim, and it is retained to avoid an unbounded docs loop. The authoritative status surfaces and every runtime NOT RUN statement control; if a future editorial pass touches this paragraph, it can say the headless/build/signing slices are reviewed and runtime is NOT RUN.
- No new Critical or Important finding. No implementation, test, fixture, result, manifest, lock or historical-review edit was introduced by this fix wave.

## Remaining gates after this verdict

1. Commit this report and the coordinator’s `final-validation.md` with the current reports/ledger; do not alter source/test/docs outside the already-applied fix set and the new review/evidence artifacts.
2. Freeze the final tree, re-run the final manifest/diff/link/scanner counts for the added review artifacts, and do not claim the pre-fix 205-file/tree counts describe the final tree.
3. Complete the reachable-public-history/identity audit; create the new parentless `main` root from the exact audited tree; push only the approved `main` to `fabzter/escalier`; keep the private development branch and ancestry unchanged; do not gc, prune, rewrite or delete history.
4. Keep all GUI/capture/focus/TCC/tap/browser/HackerRank server-side and product claims NOT RUN; ad-hoc signing is not notarization, Developer ID or stable TCC identity.

## Final statement

**FI-01..FI-06: all ADDRESSED. New Important findings: none.** The documentation fix wave is consistent with the frozen measurements and retains every NOT RUN boundary. The retained-spike snapshot is ready for the planned publication gate, not for a product or runtime claim.
