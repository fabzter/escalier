# Final retained-spike integration review

Date: 2026-10-26
Reviewer: final integration reviewer (single broad review)
Repository freeze: HEAD `23346c1bc5268923cfcacffeffdc6963459ac679`, tree `6b4cb2bc2511cf4d6b97345b05a9b7963bd17c4d`, 205 tracked files. Base for the whole-tree diff: Git empty tree `4b825dc642cb6eb9a060e54bf8d69288fbee4904`. Working tree was clean at dispatch. This report is the only write.

This is a retained-spike snapshot review, not product readiness, not a full-app implementation review, and not a claim of runtime GUI, capture, keyboard-hook, TCC or HackerRank server-side behaviour. No model was loaded, no inference was rerun, no GUI/browser/server/tap/permission action was performed, and no test suite or build was rerun. Coordinator evidence is accepted as stated; independent read-only checks below cover only the frozen artifacts.

## Verdicts

- **Spec compliance: PASS WITH CONCERNS (conditional).** All approved bounded spike deliverables, evidence gates, licensing, measurement retention, runtime NOT-RUN boundaries and the parentless-root publication plan are present. The concerns are documentation truth/provenance defects (`FI-01`, `FI-02`), not a missing capability or a runtime overclaim.
- **Quality: PASS WITH CONCERNS.** The harnesses are unusually well bounded, fingerprinted and test-backed for retained research code. Remaining source/test residuals are bounded-prototype limitations, not production defects; the actionable items are documentation-only.
- **Critical findings: none.**
- **Ready to publish the retained-spike snapshot? With fixes.** Fix the documentation/provenance findings, run the one scoped re-review, then freeze the final tree and execute the parentless-root publication gates. Do not publish the private development branch, and do not infer product readiness, runtime success, model selection, licensing or assistance policy.

## Strengths

- **Frozen-tree integrity is exact.** The manifest contains 205 unique paths and every entry's mode, blob SHA, byte count and SHA-256 agrees with `git ls-tree -r -l HEAD`. The two generated diff sizes and SHA-256 values match the coordinator's freeze. `final-source-docs.diff` contains 197 file headers and excludes exactly the four `.wav` fixtures and four curated `results/*.json` files — no other tracked path is silently dropped.
- **Measurement provenance is strong.** The four retained JSON files each contain 12 successful trials (4 warmup + 8 measured; 48 total, 16 warmup + 32 measured). The recorded source SHA-256 values match the current committed files and the measured commit `94c895b9a057e1deca57ce2832e36655120ee759`; `git diff 94c895b..HEAD` over `run.py`, `backend.py`, `metrics.py`, `policy.py`, `manifest_tools.py`, `manifest.json`, `engine.lock.json`, tools and tests is empty. The measured implementation bytes therefore remain the committed bytes.
- **Backend and context evidence are honest.** Every arm records Apple M2 Pro `MTL0` Metal evidence, the pinned library SHA-256 and model SHA-256/size. Native R=3 is requested and reported applied in all 12 native trials; the accepted `(left,right)` pair and model default remain `null`; native decode-component values remain unknown/null; batch timings are not inherited. Endpoint arms correctly report no partial/stable metrics.
- **Natural and derived evidence are separated.** Natural EN/ES covers 50 reference tokens per arm; endpoint Parakeet, hybrid and endpoint Nemotron are 0%; native R=3 is 36%. Derived switch results (hybrid 68%, native 64%) are labelled separately, and the endpoint per-segment 0% result is explicitly not within-call bilingual proof. The mixed fixture is a synthetic assembly of different recordings, not a natural code-switch claim.
- **The R=3 versus documented offline R=13 confound is explicit.** `run.py` defaults to R=3, R=13 is only a labelled control, and `FINDINGS.md`, `README.md`, `SPEC.md` and result metadata all warn that lookahead and architecture are confounded. Requested/applied/accepted/model-default values are kept distinct.
- **Licensing and fixture provenance are complete.** Four tiny FLEURS-derived fixtures (CC-BY-4.0), one NOTICE, one manifest and human references are tracked. The pinned revision, source rows, source hashes, conversion tools, source/derived split and no-endorsement notice are present. The mixed fixture's two sources are machine-readable in `conversion.tool`.
- **Privacy boundary is well designed.** The current-tree scanner passes 205 files; all 24 local commit identities are the approved personal identity; only `spike/transcription` and no tags exist; origin is exactly `https://github.com/fabzter/escalier.git`. `.omp/`, caches, builds, models and review diffs are ignored. The publication plan correctly avoids rewriting or deleting the private development branch and proposes a new parentless public root.
- **Runtime and trust claims stay bounded.** 003 distinguishes headless tests, compile/package and ad-hoc signing from GUI evidence; 004 marks every receiver/focus/capture matrix row NOT RUN and states that a flag is not receiver evidence; 005 is default OFF, has no live tap, and states foreground-application-PID-only authority, manual same-PID page/field INVALID + Stop, and no automatic same-PID enforcement. HackerRank/Firefox claims remain conditional and source-only.
- **Scoped reviews closed the substantive issues.** Engine N-01 and all original findings are closed; runner I-1 and native-context handling are closed; fixture F1–F8 are closed; guidance F01–F10 are closed; claims T5-01–T5-10 are closed; 003 signing is approved as ad-hoc only; 004 P1–P5 are closed; 005 I-1/I-2/I-3 and settling-phase N-01 are closed with a scoped PASS.

## Findings

### Critical

None.

### Important

#### FI-01 — Current public status surfaces still say no measured ASR exists

**Locations:**
- `AGENTS.md:3-5` — “no measured ASR/capture/stealth result”.
- `docs/README.md:12,23,31` — the 2026-10-26 analysis is described as “no measured results”; Spike 001 is “no measured inference result”; the retained spikes “have not established a measured inference…”.
- `docs/requirements.md:77` — OBS-01 treatment says “no independent inference/backend/performance test has run”.
- `docs/requirements.md:114` — “The retained spikes have not established a measured inference, capture, focus or stealth result”.
- `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md:3,13,206,228` — “have produced no measured results”; “Independent inference/backend measurements have not run”; Probe A “has produced no measured inference result”; “No spike has yet produced a measured latency, accuracy, visibility or focus result”.

**What is wrong:** These are current, public-bound index/guidance/requirements statements. They contradict the retained result artifacts (`FINDINGS.md`, `results/EXECUTION.md`, four curated JSON files) and the root `README.md:13-22`, which correctly says ASR measurements exist. The analysis document is internally inconsistent: line 228 says the spike carries both cached-model arms while line 3 says no measured results exist.

**Why it matters:** A public snapshot would contain a false central status claim and would make the evidence trail self-contradictory. This is a documentation-truth and evidence-provenance defect, even though the underlying measurements are sound.

**Minimal fix:** Update these status sentences and index rows to state that Spike 001 has four measured real-model arms and point to `FINDINGS.md` and `results/EXECUTION.md`; state separately that capture/focus/stealth runtime and full-app capability remain unmeasured. In `docs/requirements.md`, update the OBS-01 treatment and the design-status sentence without renumbering IDs or changing requirement decisions. In the analysis document, add a dated measurement-update note and correct the Probe A status, preserving its historical research content. Do **not** rewrite the explicitly historical `docs/analysis/2026-10-25-feasibility.md:194` snapshot or historical worker reports; the docs index already labels that file historical.

#### FI-02 — `FINDINGS.md` natural Spanish hybrid first-stable mean does not match the retained JSON

**Location:** `spikes/001-transcription/FINDINGS.md:89`.

**What is wrong:** The table reports Parakeet hybrid / Spanish first stable text as **2105.1 ms**. The two measured trials in `results/parakeet-hybrid.json` are `2160.008` and `2141.224` ms; their mean is **2150.616 ms**. Every other numeric cell in that table is the correct mean of its two measured trials (verified across all four arms, including both sibling cells in the same row and all final-tail cells); 2105.1 is a single-cell transcription error, not a different convention. The JSON aggregate and per-trial timings are internally consistent.

**Why it matters:** This is a numerical claim in the primary findings document that cannot be reproduced from the retained curated evidence. It is a data-provenance defect. It does not change the WER conclusions, but it weakens trust in the measurement table and should not be published uncorrected.

**Minimal fix:** Correct the value to `2150.6` ms (mean of the two measured trials), or add a precise derivation/reference to the retained JSON. Recheck the table against the four JSONs after editing. Do not change the measured source or rerun inference; this is a report correction only.

### Minor

#### FI-03 — Completed-spike and pending-review status lines are stale

**Locations:**
- `docs/README.md:25-27` — 003 is still “Plan; build/UI behavior not validated”, 004 is “Plan”, 005 is “In progress”, and the links point to `PLAN.md` rather than the retained `README.md`/`FINDINGS.md`.
- `README.md:33`, `spikes/README.md:8`, `spikes/001-transcription/README.md:3`, `spikes/001-transcription/results/README.md:8` (“Planned arms…”), `spikes/001-transcription/review/progress.md:37`, and `spikes/001-transcription/review/final-review-brief.md:3` — final integration review is still “pending”.
- `spikes/001-transcription/README.md:145` — “task reports are added as slices complete”.

**What is wrong:** The current index and status lines do not yet reflect the completed headless/build/signing slices, the completed ASR measurements, or this final review. 003/004/005 remain runtime NOT RUN, which must not be changed, but their implementation/readiness status is stronger than “Plan”/“In progress”.

**Why it matters:** After this report, “final integration review pending” is false, and a public index would understate the reviewed artifacts. This is a status/index refresh, not a capability upgrade.

**Minimal fix:** After the fix wave and scoped re-review, mark the final review complete with a link to this report; update the 003/004/005 rows to “headless/build/signing reviewed; runtime NOT RUN”; point index links at the retained README/FINDINGS entries. Keep every runtime cell NOT RUN and do not imply product readiness.

#### FI-04 — Fixture README’s manifest-inclusive byte total is stale

**Location:** `spikes/001-transcription/fixtures/README.md:54-55`.

**What is wrong:** “914,576 bytes of WAV/reference data” is correct: 914,096 WAV + 480 reference bytes. The parenthetical “919,910 bytes including `manifest.json`” is not: the current `fixtures/manifest.json` is 5,515 bytes, so the total is **920,091** bytes. The 919,910 figure corresponds to an older 5,334-byte manifest and contradicts the committed file.

**Why it matters:** The fixture README is the provenance/verification entry point; a stale total can make a reader believe the manifest has changed unexpectedly or that the documented arithmetic is wrong.

**Minimal fix:** Update the parenthetical to 920,091 bytes (or remove the exact manifest-inclusive number and point to `wc -c`/`--verify-only`). Leave the 914,576 WAV/reference total unchanged.

#### FI-05 — Fixture README quotes an obsolete mixed-fixture conversion string

**Location:** `spikes/001-transcription/fixtures/README.md:121-123`.

**What is wrong:** The README quotes the assembly step as `switch-concat en_us row 518 + es_419 row 322 pcm v1`, while `fixtures/manifest.json:128` and the generator record `switch-concat v1 sources=en_us:518:...;es_419:322:... pcm v1`. The machine-readable provenance was updated for F1, but this prose quotation was not.

**Why it matters:** The same README elsewhere says the source identities are carried in the `conversion.tool` record; the obsolete quote contradicts the current machine record and could confuse a regeneration check.

**Minimal fix:** Quote the current `sources=…` form or refer to `conversion.tool` without restating a literal string that can drift again.

#### FI-06 — `SOURCES.md` companion-permission anchor is under-inclusive

**Location:** `spikes/002-hackerrank-claims/SOURCES.md:28`.

**What is wrong:** The row cites `natively-browser/src/manifest.json` lines 10–25 for optional host permission, MV3 and `activeTab`/`scripting`. Lines 10–25 cover only `optional_host_permissions`; `manifest_version: 3` is at line 2 and `activeTab`/`scripting` are at line 8. The observations are true, but the cited range does not support all of them.

**Why it matters:** The claim trace is a public evidence index; an anchor that does not cover the claim weakens its auditability. This is a minor citation-precision issue, not a claim reversal.

**Minimal fix:** Cite `manifest.json` lines 2, 8 and 10–25 (or 2–25) and keep the observation text unchanged.

## Integration checks performed

- **Freeze/manifest:** recomputed `git rev-parse`, `git ls-files`, `git ls-tree -r -l`, per-file SHA-256, diff byte/line counts and diff SHA-256. All match the supplied freeze. Manifest 205/205; no missing/extra paths; modes only 100644/100755; no tracked weights, apps, dylibs, caches, `.omp/`, keys, databases or build trees.
- **Diff exclusions:** `final-integration.diff` has 205 file headers. `final-source-docs.diff` has 197, excluding exactly the four fixture WAVs and four result JSONs. No excluded path is missing from the tracked tree.
- **Measurements:** loaded all four JSONs with a strict non-finite rejection; checked trial counts/phase, model/library/backend identity, source fingerprints, applied/requested/accepted context, null native-decode values, natural/derived WER and timing means. All checked values match `FINDINGS.md` except `FI-02`.
- **Committed-code identity:** current `run.py`, `backend.py`, `metrics.py`, `policy.py`, `fixtures/manifest_tools.py`, `fixtures/manifest.json` and `engine.lock.json` hashes match the JSON/EXECUTION values and the blobs at `94c895b`; no implementation/test/tool diff exists between that commit and HEAD.
- **Links and commands:** 68 Markdown files, 221 links, 88 external links, zero missing relative targets and zero local link targets that are untracked/ignored. The documented verification and build entry points exist; the 004/005 loopback server argument forms match their parsers; Swift package manifests are dependency-free and consistent with their README commands.
- **Privacy/identity:** `audit_public.py` scanned 205 tracked files with zero findings, and also zero with `--include-untracked` (ignored artifacts excluded). The identity audit with `--expect-email faboster@gmail.com` passed; all 24 local commits are personal-identity only; no tags; no work email in identities. `.omp/`, `.cache/`, `.tools/`, `.build/`, `__pycache__/` and `.ruff_cache/` are ignored, not tracked.
- **Claims boundary:** reviewed the current root/spike READMEs, 002 trace, 003 signing addendum, 004 evidence template and 005 README/FINDINGS. GUI/capture/focus/TCC/browser/HackerRank server-side claims remain NOT RUN; ad-hoc signing is not notarization, Developer ID, Gatekeeper approval or stable TCC; same-PID page/field focus is manual INVALID + Stop, not automatic. No unreported receiver-pixel or runtime success was found.
- **Not run:** no XCTest/Node/unittest suite, Swift build/package, engine verification, fixture fetch, model load, inference, GUI, browser/server, event tap, permission/TCC/Keychain action, or network access. No new bounded probe was necessary.

## Residual disposition ledger

Disposition vocabulary: **Resolved** = scoped fix/review evidence closes the item; **Retain** = consciously accepted residual with a technical reason; **Fix** = actionable finding above. Historical worker reports are retained as records of the revision they describe; their stale counts/status are not treated as current artifacts. No source/test/doc changes outside this report were made.

### Spike 001 — engine (Task 1)

| ID / item | Disposition | Reason and current evidence |
|---|---|---|
| F-01..F-07; N-01 terminal non-final snapshot/text-view lifecycle | Resolved | Scoped fix reviews ADDRESS/PASS; `backend.py:1408-1430` synchronizes snapshot/text-view failures; restart/batch/close tests at `tests/test_backend.py:786-833`. |
| R-01 extension-kind probe is not value acceptance | Retain | `start_stream` probes the requested value and fails closed; info explicitly labels extension-kind evidence; JSON shows requested/applied 3 and accepted null. |
| R-02 documented model default 13 not in `Engine.info` | Retain | Deliberate separation: runner metadata owns documented 13; adapter API default 3 is labelled non-model-default; actual accepted/default remain null. |
| N-02 reported-library mismatch keeps cached module | Retain | Fail-closed at `backend.py:383-399`; fresh process recovers; same-process retry limitation is low severity. Editing `backend.py` now would change measured source hash `5038005…` and decouple results from code unless rerun/re-baselined. |
| R-03 nested key-shape aliases differ | Retain | Runner consumes flat/info keys; no current consumer requires identical nested aliases; measured JSON retains the values. |
| R-04 narrow coverage for absent `ParakeetStreamOptions` / retryable pre-native busy feed | Retain | Code-inspected fail-closed branches; no counterexample; supported measurement path exercised. |
| Unasserted `finished` and batch-after-snapshot variants; close test replacement | Retain | Same failure synchronizer/active-clear path is code-verified; coverage note only; no behavioral gap. |
| Report-path accuracy (`review/.tools/reviews/...` in `task-1-fix-1-review.md:6`, `task-1-fix-2-review.md:7,84`) | Retain | Local-only ignored diff path is misstated in two historical review reports; `review/progress.md:69,76` gives the correct spike-local `.tools/reviews/` location; no public artifact depends on it. |

### Spike 001 — runner (Task 2)

| ID / item | Disposition | Reason and current evidence |
|---|---|---|
| I-1 native R=3 default/confound; M-2 zero-decode; M-3 docstring; M-4 helper; M-5 abort/empty-flush; F01 context keys; F6 metadata | Resolved | Scoped re-review ADDRESSED; current code has R=3 defaults (`run.py:522,2297`), positive/zero decode handling, skip/empty-flush tests, and natural/derived `DEFAULT_LIMITATIONS` (`run.py:1814`). |
| M-1 one-sample replay-origin bias (0.0625 ms) | Retain | Numeric convention is documented in `metrics.py:15-21,518-524` and result replay metadata; no value changed; 0.0625 ms is below the stated timing resolution and does not alter conclusions. Editing `run.py`/`metrics.py` would change measured hashes. |
| M-6 large-file split deferral | Retain | `run.py` remains a coherent single module; explicitly coordinator-authorized; structural split would change measured source hashes and require re-baseline, with no evidence benefit. |
| T2 word “uses” in R=3 limitation (`run.py:82-85`) | Retain | Requested/applied/accepted are separately exposed; all native trials report applied=3; the same limitation immediately says requested is not proof of applied context. Comment-only edit would change `run.py` hash. |
| T2 absent `decode_ms` key explicit test | Retain | Zero/negative/NaN cases are tested; absent key follows the same `_positive_ms_or_none(None)` path; coverage nit, no defect. |
| Accepted/applied/default distinction; fatal-stream and empty-flush behavior | Resolved/verified | JSON per-trial context and `run.py` results retain the distinction; fatal skip and empty flush have focused tests per scoped review. |

### Spike 001 — fixtures and claims (Tasks 3 and 5)

| ID / item | Disposition | Reason and current evidence |
|---|---|---|
| F1 machine-readable two-source provenance; F2 acquisition safety; F3 derived tool; F4 path aliases; F5 false-green escape; F6 aggregate note; F7 table direction; F8 review package | Resolved | Scoped re-review ADDRESSED; manifest/generator/tests agree; license/change/source-derived boundaries verified. |
| T3 conversion quotation | Fix `FI-05` | Current prose quote contradicts `manifest.json:128` and the generator; documentation-only. |
| T3 historical full-suite count 180 vs 181 (`task-2-report.md:66`, `task-3-report.md:289`) | Retain | These are retained execution snapshots of different fixed revisions; the brief explicitly says counts are snapshots, and the canonical final integrated count is 204. Do not rewrite historical reports. |
| T3 license/change notices and source/derived split | Resolved/verified | CC-BY-4.0 NOTICE, attribution, change description, no-endorsement, pinned revision, source/derived labels and mixed/auto documentation are present. |
| T5-01..T5-10 claims fixes | Resolved | Scoped re-review ADDRESSED; HackerRank/Firefox claims remain source-only and conditional. |
| T5 manifest anchor coverage | Fix `FI-06` | Citation range is under-inclusive; observations themselves remain supported. |
| T5 retained review artifact note says `.cache` absent (`task-5-review.md:7`) | Retain | Historical review of record; fix review explains the later retained snapshots; not a current claim about the tree. |
| T5 row 9 “periodic system screenshots” (`README.md:51`) | Retain | True but less specific than the corrected Proctor section; pre-existing row, no regression and no capability overclaim. |

### Spike 001 — guidance, privacy and publication (Task 4)

| ID / item | Disposition | Reason and current evidence |
|---|---|---|
| F-01..F-10 | Resolved | Scoped re-review PASS; scanner/identity tests, current tree guidance and links verified; `FI-01`/`FI-03` cover later status drift. |
| Scanner heuristic and current-tree PASS do not sanitize private ancestors | Retain + publication gate | Documented in AGENTS/README. Current 205-file scan passes; the old development ancestry is not published. The parentless-root plan plus reachable-object audit is the required gate; no claim that a tree scan cleans history. |
| 005 index links absent at `f758f34` | Resolved | Integrated tree has 005; link check finds zero missing/untracked targets. |
| “Only reachable commit touching scanner/test paths is `1605da2`” imprecision | Retain | Historical report sentence; substantive point that old fragments are in the pre-fix blob remains accurate; no current-tree effect. |
| Personal email in `review/progress.md:41` | Retain | Personal attribution is intentional and approved; identity audit accepts `faboster@gmail.com`; no work identity appears in commit identities. |
| Test portability (English Git messages, `commit.gpgsign`) | Retain | Tests pass on this host; no CI portability claim is made. |
| Identity audit lists audited identities | Retain | Intentional human/JSON listing of identities, not secret disclosure; non-echo claim applies to content findings. |
| Old private fragments in development history | Retain under publication boundary | Never push `spike/transcription`; publish a new parentless root from the exact audited tree, retain the private branch unchanged, and do not gc/prune/rewrite. |

### Spike 003 — native shell/UI

| ID / item | Disposition | Reason |
|---|---|---|
| S3-01 retained aggregate shows only assistance provenance/chunk count, not text/alt text (`Sources/EscalierShell/RetainedResultsPanelView.swift:89-94`) | Retain | Data is retained correctly and tests pin it; this is a synthetic inspection-UI completeness gap in an unlaunched prototype, not data loss or a public capability claim. |
| S3-02 menu key equivalents bypass phase gating (`Sources/EscalierShell/AppDelegate.swift:95-105,155-162`) | Retain | GUI/keyboard behaviour is NOT TESTED; the menu is a synthetic route demo, not a product shortcut claim. |
| S3-03 shortcut hint/key equivalent duplicated (`Sources/EscalierCore/Assistance.swift:125-143`) | Retain | Pairing test is a drift-guard improvement; current values match; no observed mismatch. |
| S3-04 source-audit positive control exercises matcher, not file enumeration (`Tests/EscalierCoreTests/SourceAuditTests.swift:46-90`) | Retain | Audit is explicitly heuristic; current enumeration covers the shell/core sources; no missed-file counterexample. |
| S3-05 mid-stream snapshot keeps “streaming” label (`Sources/EscalierCore/ConversationState.swift:203-209`) | Retain | Synthetic in-memory display label; runtime streaming/rendering is NOT TESTED; no retention or capture claim. |
| S3-06 preparation copy promises a live sample (`Sources/EscalierShell/ConversationDetailView.swift:101`) | Retain | Synthetic demo copy; the separate live sample is correctly documented; GUI not launched. |
| S3-07 report says 1100×700 as window size though it is minimum (`review/implementation-report.md:199`; `Sources/EscalierShell/AppDelegate.swift:29,36`) | Retain | Historical worker report; initial 1240×840 vs minimum 1100×700 is a reviewer-baseline detail; no runtime visual claim. |
| S3-SG1 static guard does not apply no-launch/no-policy prohibitions to production package script (`Tests/EscalierCoreTests/PackagingScriptTests.swift:26-30,68-71`) | Retain | Current `tools/package-app.sh` complies (no `open`, `spctl`, `xattr`, `tccutil`, `security`); guard gap for future promotion, no current violation or trust claim. |
| S3-SG2 failure harness checks nonzero statuses rather than exact 42/43 and exact signature counts (`tools/test-package-signing.sh:49-51,61-63,80-84`) | Retain | Coordinator observed genuine ad-hoc signing and strict verification; 42/43 and `entries=11`/`files=0` are observed values, not claimed invariants; no notarization/TCC/launch claim. |
| Runtime GUI/keyboard/focus/scroll/VoiceOver/launch/Dock/TCC | Retain as NOT RUN | Explicitly labelled throughout; this review found no evidence upgrading these. |

### Spike 004 — window/capture/focus

| ID / item | Disposition | Reason |
|---|---|---|
| P1 receiver gate missing bytes/timestamp; P2 treatment-occluded/control-visible; P3 signing/identity description; P4 readback overclaim; P5 fingerprint recipe | Resolved | Scoped fix review ADDRESSED/PASS; current code/tests/docs reproduce the fixes; source 48-file hash `2508c559…` and historical 47-file hash `f7a974ce…` are documented/reproducible. |
| P6 per-mode click-through counters are cumulative | Retain | Runtime matrix is NOT RUN and requires one row per mode; event journal allows reconstruction; fix before runtime evidence, not before a synthetic snapshot. |
| P7 receiver evidence not cleared on peer connection failure | Retain | Runtime NOT RUN; timestamp presence is not freshness; the fix review explicitly leaves this open for pre-runtime hardening. |
| P8 sender setup failure can leave capture running with page stop disabled | Retain | Runtime NOT RUN; browser sharing indicator remains an external stop route; fix before interactive run. |
| P9 static URL guard bypassable by protocol-relative/concatenated URLs | Retain | Audit is an explicitly heuristic static guard; network APIs are separately banned; add tamper coverage before promotion. |
| P10 unused `statSync` imports | Retain | Cosmetic; no behavior or evidence effect. |
| P11 compound `NOT RUN / same-window control possibly N/A` cell (`spikes/004-window-capture-focus/FINDINGS.md:135`) | Retain | Template-only cell; all rows NOT RUN; split into concrete rows during the runtime session. |
| F4-1 `review/implementation-report.md:222` “pre-signing bundle was unsigned” | Retain | Historical report nuance; signing addendum and current README/FINDINGS correctly describe ad-hoc signing; no current capability claim relies on the sentence. |
| F4-2 `spikes/004-window-capture-focus/README.md:107-108` receiver summary omits `bytesReceived`/`timestamp` | Retain | Detailed oracle at `spikes/004-window-capture-focus/README.md:143-148` and code require both; operator summary omission is a minor doc inconsistency, not a false evidence gate. |
| F4-3 signing-pass 48-file hash `27e54adb…` from an uncommitted intermediate tree (`review/implementation-report.md:315-316`) | Retain | Explicitly a signing-pass snapshot; current 48-file and historical 47-file hashes are reproducible; the intermediate value is not used as measurement provenance. |
| F4-4 `/timestamp/` literal audit tripwire (`tools/web-audit.mjs:370-380`) | Retain | Static tripwire only; semantic fail-closed behavior is unit-tested; not cited as standalone evidence. |
| Runtime receiver pixels/focus/click-through/occlusion/TCC/Dock/identity | Retain as NOT RUN | Evidence template and README/FINDINGS keep every cell NOT RUN; no runtime success inferred. |

### Spike 005 — global keyboard routing

| ID / item | Disposition | Reason |
|---|---|---|
| I-1 adapter/callback seam; I-2 foreground-PID scope; I-3 close/drain/fallback; N-01 settling `.off` cleanup | Resolved | Scoped fix-1/fix-2 reviews ADDRESSED; N-01 guard is `.closed \|\| .off` (`Sources/RoutingAdapter/AdapterCoordinator.swift:157-160`), all settling terminal paths schedule exactly one cleanup, no spurious teardown, and fix-2 scoped PASS/quality PASS. |
| S5-01 final stop cause overwritten by drain completion (`Sources/RoutingCore/RoutingEngine.swift:436-446`) | Retain | Preserves bounded drain semantics; runtime R7 evidence NOT RUN; final cause can still be visible transiently. Fix only with runtime evidence design. |
| S5-02 dead teardown drain comment/branch (`Sources/RoutingFixture/TapAdapter.swift:349-354`) | Retain | Cosmetic/unreachable defense; no behavior change. |
| S5-03 native extraction clipping beyond 128 UTF-16 not marked (`Sources/RoutingFixture/TapAdapter.swift:308-330`) | Retain | Explicit limitation; core truncation is bounded and scalar-safe; native `actualStringLength` clipping is NOT IMPLEMENTED and disclosed. |
| S5-04 settling branch lacks absolute-deadline check if timer stalls (`Sources/RoutingCore/RoutingEngine.swift:188-226`) | Retain | Low-risk timer-stall edge; bounded 30 s cap is documented; runtime timing NOT RUN. |
| S5-05 target/mode controls editable while armed | Retain | Changes do not affect the running adapter; UI is a synthetic fixture; runtime NOT RUN. |
| S5-06 fixed mapping (no mapping editor) | Retain | Fixed probe is the stated fixture contract; mapping/budget wiring is tested at the coordinator seam. |
| S5-07 permission gate ANDs Accessibility and listen-event access (`Sources/RoutingFixture/NativeChecks.swift:29`) | Retain | Sufficiency for this tap class is unverified and runtime NOT RUN; classified as an unverified gate, not a bug. |
| S5-08 mask guard scans only first `eventsOfInterest` line (`Tests/RoutingCoreTests/SourceAuditTests.swift:141-148`) | Retain | Heuristic static guard; fixture uses the pinned single-line mask; harden before promotion. |
| S5-09 `decodeURIComponent` malformed path can throw in manual server (`tools/serve-local.mjs:19-29`) | Retain | Manual loopback fixture only; no untrusted input or runtime claim; easy hardening, not publication-blocking. |
| S5-10 `teardownCompleted` set before cleanup; close-gate race (`Sources/RoutingAdapter/AdapterCoordinator.swift:133-148`) | Retain | Close/drain/termination runtime NOT RUN; forced 2.5 s termination fallback exists; earlier/later ordering should use a separate started flag before runtime approval. |
| S5-11 adapter RED log aborted after first test | Retain | Evidence limitation of retained ignored log; core 63-test RED log exists and green 84/0; no code failure. |
| S5-12 publish-order test does not prove publish-before-stop across separate recorders (`Tests/RoutingAdapterTests/AdapterCoordinatorTests.swift:140-154`) | Retain | Production order is inspected (`Sources/RoutingAdapter/AdapterCoordinator.swift:146-148`); test-name overclaim only. |
| S5-13 G-04 “failing foreground/focus checks disarms” wording (`review/preflight-resolutions.md:16`) | Retain | Later binding PID-only clarification, PLAN, README, FINDINGS and report resolve it; “focus” here means native foreground app, not page/field focus. |
| S5-14 process backstop omits `.off` in reported flag | Retain | Cosmetic asymmetry; `.off` terminal paths are already scheduled; no extra teardown or missed cleanup. |
| S5-15 report “No commit” / stale staging statements (`review/implementation-report.md:11-12,45,459,523`) | Retain | Historical worker report written before coordinator commits; current Git state is authoritative and no source claim depends on it. |
| S5-16 RED count 43 vs 434 | Resolved | Current report records 434 in the retained final summary (`review/implementation-report.md:43,176,182`). |
| S5-17 stale terminal snapshot clearing a newer adapter | Resolved | Fix-1 review found `applyPhase` no longer nils the adapter on `.off`/`.closed` snapshots; only `adapterTeardownDidComplete` clears it. |
| S5-18 README teardown order differs from code | Resolved | Fix-1 review confirms README now matches release → publish → stop → notify; actual tap/source ordering is safe. |
| S5-19 callback mapping/budget and native target operations not behavior-tested; Unicode limits | Retain | Coordinator seam tests consume/pass/budget/disabled/teardown; native `CGEvent` mapping and target operations remain static-audited; native Unicode clipping is explicitly NOT IMPLEMENTED/limited. |
| S5-20 exact foreground-PID-only focus/close scope; same-PID page/field focus | Retain as boundary | Native authority is foreground-application PID only; page/tab/editable-field focus and visibility are manual INVALID + immediate Stop; automatic same-PID enforcement is NOT IMPLEMENTED/NOT TESTED; close/termination runtime NOT RUN. |
| S5 runtime R1–R10 | Retain as NOT RUN | No tap, permission, GUI, browser, server or synthetic typing occurred; no runtime suppression/no-bubble/focus claim exists. |

## Recommendations and publication gates

1. **Fix wave is documentation-only.** Apply `FI-01` through `FI-06` without touching `run.py`, `backend.py`, `metrics.py`, `policy.py`, `fixtures/manifest_tools.py`, `fixtures/manifest.json`, `engine.lock.json`, measured tests or result JSON. Any measured-source edit would break the exact source fingerprints and require a fresh run or an explicit byte-equivalence/re-baseline record. This review found no code defect that justifies that cost.
2. **One scoped re-review.** Re-review the six documentation fixes and the updated status text. Confirm no runtime claim was upgraded and every NOT-RUN row remains.
3. **Freeze the exact public tree.** This report is a new review artifact and is not in the frozen 205-file manifest/diff. After the fix wave, add this report and the corrected docs, then regenerate or explicitly attest the 206-file (or final-count) manifest/diff and tree identity. Do not claim the pre-fix 205-file manifest describes the final fix-wave tree.
4. **Publish only a parentless root.** Create a new local `main` root from the exact audited tree, with no parent; push only `refs/heads/main` to `fabzter/escalier`, without force or tags. Keep `spike/transcription` and all private ancestry unchanged. Do not gc, prune, expire reflogs, rewrite or delete history. Audit all objects reachable from the prospective `main` (not the private branch) for content, identities, tree ID and absence of ignored models/caches/session state, then read back remote SHA, visibility, default branch and tree identity.
5. **Keep the evidence classes separate.** Current-tree scanner PASS is not a reachable-history audit. Ad-hoc signing is not notarization, Developer ID, Gatekeeper approval or stable TCC identity. ASR measurements are fixture-level feasibility evidence, not live-call latency, bilingual accuracy, capture invisibility, browser non-delivery or HackerRank server-side evidence. No model, threshold, licence, stealth or assistance policy is selected.
6. **Future work.** Before any runtime approval, address the retained pre-runtime items that matter operationally: 004 P7/P8/P9; 005 close-gate race, same-PID manual Stop discipline, permission/tap behavior, Unicode limits; 003 UI inspection. A controlled R=3/R=13/language-prompt study with independent natural bilingual speech and gold word timing remains the appropriate next ASR step; do not infer a model winner from this slice.

## Final readiness statement

**Ready to publish retained-spike snapshot: With fixes.** The frozen 205-file tree is internally consistent, the ASR measurements are traceable to the committed implementation bytes, the privacy/identity checks pass, and the retained spikes respect their approved boundaries. Publication should wait for the six documentation fixes, the scoped re-review, and the parentless-root/reachable-history gates. It should not be described as product readiness, runtime GUI/capture/keyboard validation, notarization, TCC stability, or a HackerRank invisibility result.
