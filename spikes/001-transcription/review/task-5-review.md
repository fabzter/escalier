# Task 5 review — Natively/HackerRank claim trace

Date: 2026-10-26. Independent task-scoped review. Read-only: no runtime test, GUI, capture, microphone, interview access, inference or state-changing commands.

Inputs: [brief](task-5-brief.md), [preflight resolutions](preflight-resolutions.md), [task-5 report](task-5-report.md), [spike 002 README](../../002-hackerrank-claims/README.md), SPEC global constraints, the prior 15-ST inventory in [the existing research](../../../docs/analysis/2026-10-26-live-asr-and-browser-privacy.md#5-natively-stealth-parity-inventory), Spike 004's plan, requirements, docs index and the public HackerRank/Natively pages.

Artifact note: the assigned `.tools/reviews/task-5.diff` is not present in the checkout, and `.tools/` is git-ignored. The spike-002 `.cache/` snapshots named by the report are also absent and ignored. This review is therefore artifact-based (README + report) plus independent re-fetches of the pinned public sources; it is not a hunk-by-hunk diff review.

## Verdicts

**Spec compliance: PASS.** The deliverable is complete and within the approved scope. It supplies the bounded question/method, dated and pinned revisions, a claim-to-mechanism/evidence/limitation table, an invisible-versus-disguised classification, a genuinely-HackerRank-specific section with an honest absence, a proposed synthetic matrix, limitations, and a report with status, checks, unresolved evidence and self-review. It does not redo the 15-ST audit, access the invitation, run runtime tests, copy code, publish, or add a new product/assistance prohibition. Findings below are research-quality corrections, not scope violations.

**Research quality: REVISE — otherwise strong.** The central analysis is sound and materially better than the vendor marketing: the HackerRank claim is correctly decomposed into generic window/identity/network mechanisms plus a HackerRank-specific content/answer pipeline; the main/release drift and the unwired `process_name.rs` are correctly reported; the SCK limitation is taken from Natively's own source/test rather than asserted; the trace does not promise universal undetectability. Two medium corrections are needed before this note is treated as the authoritative claim record: the Interview Integrity Signals page is assigned to the Legacy interview experience without support from the cited page, and HackerRank's most directly relevant public statement — Proctor Mode screenshot analysis targeting "invisible overlay applications" — is omitted. The trace also misses that Natively's own docs contradict one another about process-list invisibility and browser plugins; that is the strongest available "marketing vs source" evidence. The core conclusion does not change.

## Spec checklist

| Brief requirement | Status | Note |
|---|---|---|
| Only `spikes/002-hackerrank-claims/**` + `review/task-5-report.md` | PASS | Only the README and report exist in the owned paths; no cross-edits observed. `.cache` is absent, so its retention claim cannot be checked. |
| Build on the 15-ST inventory; no full re-audit | PASS | ST mapping matches the prior table; see T5-06 for one omitted row. |
| Distinguish (a) generic capture/focus/input, (b) disguise/quieting, (c) HackerRank-specific, (d) marketing/unverified | PASS | The G/H/M table and the invisible-vs-disguised table do this cleanly. |
| Pinned main + release, dated public pages | PASS | `b9287ec` (2026-10-25) and `b439c1f` (2026-10-05) verified; tag is lightweight (T5-05). |
| Public claim → mechanism → evidence → limitation | PASS | Ten-row table with explicit limits; no source claim converted into receiver proof. |
| Invisible vs disguised classification | PASS | Correctly conditional on capture backend and separates cosmetic identity from executable/path identity. |
| Genuinely HackerRank-specific finding (including absence) | PASS | Absence in stealth code is supported by the files checked; see T5-02 for a missing platform-side channel. |
| Proposed synthetic capture/focus matrix, not run | PASS | Clear acceptance boundary (independent receiver pixels); scope handoff needs T5-07. |
| Exact revisions/path/line evidence where practical | PASS with notes | Sampled line anchors are accurate; some paths/links imprecise (T5-04) and the code search is not reproducible (T5-10). |
| No code copying | PASS | Short quotes/comments only; no implementation blocks. |
| No runtime/interview/GUI claim or implicit testing claim | PASS | Explicitly "research only"; Spike 004 cited as proposed, not run. |
| No new product exclusion or assistance prohibition | PASS with wording risk | "not designed for locked-down proctoring" could harden into a scope decision (T5-08). |
| Public hygiene | PASS | No private home paths, work email, signed URLs, invitation identifiers or `.omp` state in the owned files. |
| Report structure/self-review | PASS | All requested sections present; the `.cache` file inventory is stale (T5-09). |

## Verification ledger (independent checks)

| Check | Result |
|---|---|
| Main `b9287ec` commit date/message | 2026-10-25, verified. |
| `v2.9.2` `b439c1f` commit date; tag ref | 2026-10-05; `refs/tags/v2.9.2` points directly to the commit (lightweight tag). |
| Revert commit `293db92` | 2026-10-13, verified; message confirms `productName`/`executableName` revert and appId retention. |
| README claims/anchors (`#L177-L185`, `#L189`, `#L330-L350`, `#L1149`, `#L1169`) | Exact quotes verified at main; same HackerRank/stealth text at `v2.9.2`. |
| Content-protection test / `stealth_window.rs` SCK note | Verified: "only sets NSWindowSharingNone"; macOS 15+ SCK ignores it; legacy paths remain effective. |
| `capture_exclusion.rs` sweep vs hook | Verified; app-owned windows only; measured file picker `kCGWindowSharingState` vs launcher. |
| `WindowHelper.ts` nonactivation/input + tray behavior | Verified: macOS panel, Windows `WS_EX_NOACTIVATE`, `WH_KEYBOARD_LL`/CGEventTap comments; tray/taskbar comment. |
| 500 ms protection loop | Verified in `main.ts`/stealth-protection wiring, not inside `WindowHelper.setContentProtection`; substance correct. |
| `macDockPolicy.ts` Accessibility measurement | Verified in the header comment; source comments, not independent measurement. |
| `main.ts` network quieting block | Verified: remote sinks dropped, outbox/funnel/model scheduler/Hindsight stopped, queued events retained, explicit actions/provider traffic remain. |
| `process_name.rs` unwired | Verified: file exists (macOS-only SPI); `lib.rs` declares `stealth_window` and `capture_exclusion`, not `process_name`. |
| Build identity | Main `productName: Natively`, appId `com.apple.corespeechd`; `v2.9.2` `productName: corespeechd`, Windows `executableName: audiodg`; `disguise-name.cjs` comments match. |
| HackerRank-specific content files | Registry HackerRank entry at file line 140; manifest optional host permission; `tab-classifier.ts` line 49 keyword; `extract.ts`, `dom-helpers.ts`, `math-text.ts`, `formula-sheet.ts`, `pageCaptureFallback.ts`, `main.ts` formula comments all contain HackerRank references. |
| Absence in stealth code | No `hackerrank` matches in `stealth_window.rs`, `capture_exclusion.rs`, `process_name.rs`, `WindowHelper.ts`, `service-worker.ts`, `electron/llm/prompts.ts` or CHANGELOG. Supports the bounded absence claim. |
| Natively public docs | Supported Apps lists HackerRank "Screen Hidden" and says coding platforms need capture/OCR, not a platform API; Undetectable page states process-list and locked-down limits; FAQ states the task-manager/process-scan claim; blog states no 100% guarantee. |
| HackerRank docs | Browser matrix (prior evidence), Interview Integrity Signals, Observation Mode, Proctor Mode, Desktop App Mode checked. Proctor/Desktop are AI Add-on/test controls. |
| Hygiene | No private paths, work email, signed URLs, invitation/calendar identifiers or `.omp` state in the owned files; the HackerRank links are support/docs URLs, not invitation-shaped. |

## Findings

| ID | Severity | Location | Issue | Fix |
|---|---|---|---|---|
| **T5-01** | **Medium** | README "HackerRank's public monitoring modes" preamble (`README.md:107-112`) and unresolved bullet (`:247-251`); report exact checks (`task-5-report.md:73-77`) | The trace says HackerRank's pages place **both** Interview Integrity Signals and Observation Mode under the Legacy interview experience. Only Observation Mode says that. The fetched Interview Integrity Signals page carries no legacy banner; it describes "Interviews"/"Interview report" and lists supported question types without an experience qualifier. As written, the applicability caveat can wrongly narrow a channel that may also apply to the configured/New experience. | State that Observation Mode is explicitly documented as legacy; record the integrity-signals page's experience scope as **unstated** (or cite a source that establishes it). Do not use "Legacy" to bound this channel without that citation. |
| **T5-02** | **Medium** | README Proctor Mode bullet (`README.md:122-126`) and consequences #2 (`:137-141`); report Finding 3 (`task-5-report.md:89-93`) | HackerRank's Proctor Mode page explicitly says screenshot analysis detects **"Specialized browser extensions or invisible overlay applications that assist in answering coding questions"**, that candidates are prompted to share their **entire screen**, and that screenshots are captured every 15 s (5 s around violations). The trace says only "periodic system screenshots" and never quotes the direct invisible-overlay category. That is the most HackerRank-specific public statement about this product class and should be central to the platform-side limitation. | Quote the overlay-detection category; add full-screen sharing and cadence; explain that a truly excluded overlay would not appear in the screenshots (so this is content analysis, not proof of the capture API), but it directly contradicts a blanket "Screen Hidden" reading. Keep the Test-mode applicability caveat. |
| **T5-03** | **Medium** | README rows 3/5/9 (`README.md:44-50`) and Findings (`:195-232`); report Findings 2/4/6 (`task-5-report.md:85-101`) | The trace quotes Natively sources separately but does not flag that they contradict one another: (a) Supported Apps says "Nothing is added to Zoom, to your browser, or to the meeting", while the companion MV3 extension requests optional `https://www.hackerrank.com/*` host permission; (b) the Undetectable page says "It still runs as a normal process, so software that lists running apps can see it", while the FAQ says it is built not to be detectable "against … task-manager process scans" and the README says "a process list shows a system service"; (c) the Undetectable page's "overlay is excluded from screen capture" is stronger than the test/source's "not a claim about SCK". | Add a short "internal contradictions" subsection. Use it as evidence that the compatibility/marketing table is a product statement, not a capability record. This strengthens, rather than changes, the existing conclusion. |
| **T5-04** | Low | README Sources (`README.md:265-297`); report exact checks (`task-5-report.md:54-70`) | Citation precision: `tab-classifier.ts` is cited without its full path (`natively-browser/src/capture/classifier/tab-classifier.ts`, line 49); `BrowserPageCrop.ts`, `AnswerValidator.ts` and `windowTitleGuard.ts` are linked via `.../tree/<sha>/electron` rather than blob/line anchors; the `v2.9.2` `win.executableName: audiodg` evidence is at `package.json` file line 260, outside the linked `#L140-L143` range; `capture_exclusion.rs` "26-29" does not point at the macOS/Windows implementation lines (19-23). | Use full paths and blob line anchors for every cited file; add the `audiodg` line anchor; correct the `capture_exclusion` range. |
| **T5-05** | Low | README scope/method (`README.md:17-18`); report method/self-review (`task-5-report.md:24-27`, `:122`) | "tag object checked/verified" is inaccurate: `refs/tags/v2.9.2` resolves directly to commit `b439c1f` (lightweight tag, object type `commit`). An annotated tag would have a tag object. | Say "tag ref resolves to `b439c1f`; commit date 2026-10-05 verified". The pin itself is correct. |
| **T5-06** | Low | README inventory mapping (`README.md:53-58`) | The touched-row mapping lists ST-01/02/03/05/06/07/09/10/11/12/14 but omits **ST-04** (notification/prompt suppression), although the quoted "Nothing it opens leaks" claim explicitly includes notifications. ST-08 (click-through) is also arguably touched by the focus/input claim. | Add ST-04 (and optionally ST-08), or explain why notifications/click-through are outside the claim mapping. |
| **T5-07** | Low | README proposed matrix (`README.md:151-193`) vs `spikes/004-window-capture-focus/PLAN.md:10-14`, `:24-26` | The trace says execution belongs to Spike 004, but two proposed dimensions exceed 004's approved bounded outcome: build-time/runtime alias identity comparison (004 says build-time identity is a documented future comparison and forbids process-name injection) and hosted/on-device **STT** network rows (004 excludes microphone/live audio). A reader may treat those as planned 004 cases. | Mark those rows "outside 004's current bounded outcome; requires separate approval", or narrow them to what 004 can observe (window title/AX/tooltip; background vs hosted-LLM egress without STT). |
| **T5-08** | Low | README "Implication for Escalier claims" (`README.md:234-243`) | "not designed for locked-down proctoring" can harden into a new product exclusion. The brief says no additional product exclusion; the owner direction is to record unsupported gaps, not decide scope here. | Rephrase as "no demonstrated capability under locked-down proctoring; the mechanism is outside window-level exclusion; decision open". Keep the claim boundary without deciding product scope. |
| **T5-09** | Low | Report "Files changed" (`task-5-report.md:6-15`); README method (`README.md:19-25`) | The report lists `.cache/` snapshots as changed files, but the directory is absent and git-ignored. Line-anchored evidence therefore cannot be re-checked from retained local artifacts; this review had to re-fetch the public sources. (The missing `.tools/reviews/task-5.diff` is a coordinator/harness issue, not a worker defect.) | Retain a small text evidence index (public URL + pinned SHA + line + short quoted fragment; no raw HTML) or state that `.cache` was transient/removed. |
| **T5-10** | Low | README method (`README.md:22-25`) | The "27 hits" code search is not reproducible: no query URL, hit list, or per-hit inspection status. The bounded absence claim partly rests on it. | Record the exact query, the hit paths, and which were re-fetched at the pin; or reproduce with a local pinned checkout/search and list the paths. |

No high-severity findings. The core conclusion — no HackerRank-specific stealth branch; the public claim is a generalization from generic window/identity/network mechanisms plus HackerRank content support; the vendor's own limits exclude modern capture, process-list software and locked-down proctoring — is supported.

## Cross-task checks

| Check | Result |
|---|---|
| Prior 15-ST inventory (`docs/analysis/2026-10-26-live-asr-and-browser-privacy.md` §5) | Consistent on pins, limits and the release/main identity delta. Mapping omits ST-04 (T5-06); ST-15 dependency is correctly stated. |
| Revision pins across research, spike 002, docs | All use `b9287ec` / `b439c1f`; dates verified. No contradictory pin. |
| Runtime status across docs | Research §5 says reference evidence / NOT IMPLEMENTED; spike 002 says research only; docs index says planned/in progress. No claim of a measured result anywhere. |
| Docs index / root README status | They still describe Spike 002 as "Planned/in progress" / "bounded public-source claim trace" while the report marks it complete. This is a coordinator integration update, not a task-5 file. |
| Spike 004 handoff | 004 exists and covers the synthetic AppKit/browser fixture and manual matrix, but not identity aliases or STT/audio. The trace's matrix over-assigns those rows to 004 (T5-07). |
| Task 4 public-artifact scanner | The owned files contain no private home paths, work email/domain, signed-URL credentials, provider secrets or invitation-shaped links. The only "invitation" reference is generic and carries no identifier. Recommend running the scanner on the new files before commit. |
| Requirements (NFR-05/NFR-06) | The trace keeps HackerRank modes as separate dimensions and does not claim universal undetectability. The only tension is the "not designed for locked-down proctoring" wording (T5-08). |
| Ownership / cross-edits | Only `spikes/002-hackerrank-claims/README.md` and `review/task-5-report.md` are present in the owned paths. No evidence of edits to ASR, shell, or capture workers; diff-level confirmation was impossible without the review package. |
| No conflict with ASR tasks | Task 5 does not touch ASR code, fixtures, tests or results; no shared state. |

## Strengths

- The G/H/M decomposition is the right analytical frame and is applied consistently; the trace does not let a generic window flag stand in for a HackerRank capability.
- Main/release drift is handled precisely: released aliases, reverted main, retained appId, and the unwired `process_name.rs` are all correct.
- The SCK limitation is sourced from Natively's own test and native comment, including the useful "macOS 15.4+" README vs "macOS 15+" source discrepancy.
- The HackerRank-specific list (registry, manifest permission, extraction/formulas, tab classifier, page crop, refusal retry) is supported; the honest absence in stealth/capture/process code is credible.
- Proctor/Desktop App Mode are correctly treated as test-mode controls, not as the reference interview's established configuration; the trace does not conflate mode documentation with a measured HackerRank result.
- The proposed matrix has a real acceptance boundary (independent receiver pixels; selected-window vs full-display; requested vs observed state; no sender preview) and refuses to supply an evasion method.
- Public hygiene and evidence labelling are strong; no private data, no runtime claim, no universal undetectability claim.

## Review limitations

- No runtime, GUI, capture, microphone or interview test was performed; none is claimed.
- The assigned diff package and the `.cache` snapshots were absent, so source checks were sampled and re-fetched from public URLs rather than verified against retained local artifacts.
- The 27-hit code search was not re-run (GitHub search is auth/branch/time dependent); the files most relevant to the claim were checked directly at the pin.
- Public Natively/HackerRank pages are unversioned; checks are as of 2026-10-26.
- The full 15-ST inventory was not re-audited, per the brief.
