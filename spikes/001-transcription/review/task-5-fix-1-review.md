# Task 5 fix round 1 — scoped re-review

Date: 2026-10-26. Scope: original findings T5-01…T5-10 and new breakage in the fix diff
`c8b6b1a..eb8db06` (`spikes/001-transcription/.tools/reviews/task-5-fix-1.diff`). Read-only: no edits
to implementation or working state; no runtime, GUI, capture, microphone, interview, inference, or
network fetch. Verification used the retained ignored snapshots under
`spikes/002-hackerrank-claims/.cache/` plus the pinned text already in the repository.

## Verdicts

**Spec compliance: PASS.** The fix keeps the deliverable inside the brief: the README remains a
bounded claim trace, `SOURCES.md` is a new compact evidence index inside the owned
`spikes/002-hackerrank-claims/**` slice, and no product exclusion or assistance prohibition was
added. The retained `review/task-5-review.md` is outside the brief's literal write slice but is an
unedited review copy, declared in the report and consistent with the task-3 fix-round precedent
(Out-of-Scope note 1).

**Research quality: PASS.** Both medium defects and all eight low findings are corrected against
the retained public snapshots. The core conclusion is unchanged and remains properly bounded: no
HackerRank-specific stealth branch; generic window/identity/network mechanisms plus HackerRank
content support; vendor material is not receiver proof. One Minor citation-range nit was introduced
in the new index (New Breakage).

## Finding verdicts

| ID | Verdict | Evidence |
|---|---|---|
| **T5-01** legacy scope | **ADDRESSED** | `spikes/002-hackerrank-claims/README.md:109-113` now limits the explicit legacy statement to Observation Mode and records the integrity-signals breadcrumb/body distinction; repeated in the two bullets at `README.md:117-125` and the unresolved bullet at `README.md:304-310`. Cached `web-support.hackerrank.com_articles_5161582600-interview-integrity-signals.txt` shows `All Collections›Interview›Interview (Legacy)›Interview Integrity` but no legacy banner in the article body; the Observation Mode snapshot says "This article applies to the legacy Interview experience." Report row `task-5-report.md:169` matches. |
| **T5-02** Proctor overlay category | **ADDRESSED** | `README.md:126-135` now quotes "Specialized browser extensions or invisible overlay applications that assist in answering coding questions", entire-screen sharing, and the 15 s/5 s cadence; `README.md:145-153` frames it as captured-pixel content analysis, not capture-API proof, and labels Proctor and Desktop App Mode "(AI add-on, test control)". The cached Proctor Mode page contains all four facts verbatim: "share their entire screen", "screenshots every 15 seconds", "reduces the capture interval to five seconds" on window/full-screen activity, and the overlay category; it also says the feature is part of the AI Add-on and available only for tests created after the July 2025 release. Test-mode applicability remains caveated at `README.md:304-310`. Report row `task-5-report.md:170` matches. |
| **T5-03** vendor contradictions | **ADDRESSED** | New `README.md:163-185` section plus finding 8 at `README.md:280-287` flag all three contradictions: browser presence vs the companion MV3 extension, process-list visibility vs the FAQ/README process claims, and the capture guarantee vs the repo test and framebuffer caveat. Cached snapshots verify each quoted fragment; the companion manifest requests `activeTab`/`scripting` and optional `https://www.hackerrank.com/*`; pinned README line 182 contains "a process list shows a system service"; the content-protection test line 20 says "not a claim about SCK"; Supported Apps says the framebuffer path "captures everything". The section correctly treats these as product statements at different layers, not a capability record. |
| **T5-04** citation precision | **ADDRESSED** | `README.md` sources now use full paths and blob/line anchors: tab classifier path and `#L49`, main `package.json#L141-L144`, release macOS `#L140-L143`, release Windows `#L260`, `BrowserPageCrop.ts#L1-L15`, `AnswerValidator.ts#L776-L804`, `windowTitleGuard.ts#L1-L6`, `capture_exclusion.rs#L1-L23`; report range corrected at `task-5-report.md:53-55` ("lines 1–23", notes at 19–23). Spot checks: classifier line 49 contains `hackerrank`; release `package.json` line 260 is `executableName: audiodg`; `capture_exclusion.rs` lines 19–23 are the macOS/Windows implementation notes; the three former tree links are now blob links. No `tree/<sha>/electron` citation remains in the owned README. |
| **T5-05** lightweight tag | **ADDRESSED** | `README.md:17-18` says the tag ref resolves directly to the commit (lightweight tag); `SOURCES.md:7-9` repeats it; report method and self-review updated at `task-5-report.md:32-33` and `:150`. Cached `tag-v2.9.2.json` has `"object": {"type": "commit", "sha": "b439c1f…"}`. The pin and commit date 2026-10-05 are correct. |
| **T5-06** ST mapping | **ADDRESSED** | `README.md:54-58` now includes notification/prompt suppression ST-04 and click-through ST-08 and lists ST-04 and ST-08 in the touched rows. This matches the prior inventory at `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md:137` (ST-04) and `:141` (ST-08). |
| **T5-07** Spike 004 over-assignment | **ADDRESSED** | `README.md:189-193` says matrix rows marked outside 004 require separate coordinator approval; `README.md:222` splits executable/process identity out and notes 004 forbids process-name injection; `README.md:224` moves the network probe outside 004 and removes microphone/STT/live audio; `README.md:226` restates the boundary. `spikes/004-window-capture-focus/PLAN.md:11` permits only an owned generic display-title experiment and forbids process-name injection; `:14` excludes microphone and live audio. Title/AX/tooltip rows stay assigned to 004. |
| **T5-08** product-exclusion wording | **ADDRESSED** | `README.md:296-298` replaces "not designed for locked-down proctoring" with "no demonstrated capability under locked-down proctoring; any product-scope decision remains open." The claim boundary is kept without deciding product scope. Report row `task-5-report.md:176` matches. No other new exclusionary wording was introduced. |
| **T5-09** evidence retention | **ADDRESSED** | Tracked `spikes/002-hackerrank-claims/SOURCES.md` now provides URL/pin/line/short-fragment evidence and a code-search index without raw HTML. The ignored snapshots are present in this checkout under `.cache/evidence/` and `.cache/source/`; the report explains the earlier virtual-view miss and corrects the changed-path note (`task-5-report.md:15-19`, `:177`). The review package also exists at `spikes/001-transcription/.tools/reviews/task-5.diff`. |
| **T5-10** search reproducibility | **ADDRESSED** | `SOURCES.md:50-61` records the exact `gh api` query, `total_count: 27`, `incomplete_results: false`, default-branch head `172bfbfb81e792a4bc7a78096ec010971051b8ba`, and the ahead/behind relation; the 27 listed hit paths match the cached search JSON exactly (verified by set comparison, no missing/extra paths). `SOURCES.md:93-102` records the ten files re-fetched at the pin, README under `.cache/evidence/`, and the bounded-absence caveat. `README.md:21-23` carries the same qualification ("nine commits ahead"). |

## Checks run

- Compared the new README quotes against the cached HackerRank Proctor Mode, Desktop App Mode,
  Interview Integrity Signals, and Observation Mode snapshots; all quoted phrases are present with
  the stated applicability labels.
- Compared the contradiction quotes against cached Supported Apps, Undetectable, FAQ, pinned main
  README, manifest, and content-protection test; all match.
- Re-read the cached tag ref, commit metadata, `package.json` (main and release), `lib.rs`,
  `capture_exclusion.rs`, `tab-classifier.ts`, `manifest.json`, and the relevant anchor ranges.
- Compared all 27 code-search hit paths in `SOURCES.md` against the cached search JSON and the
  compare payload (`ahead_by: 9`, `behind_by: 0`).
- Re-read Spike 004 `PLAN.md:11,14` and the prior ST-04/ST-08 rows before accepting those fixes.

## New breakage in the fix diff

- **Minor — `SOURCES.md:28` anchor is under-inclusive.** The row "Companion host permission" cites
  `natively-browser/src/manifest.json` lines 10–25 for three observations, but lines 10–25 cover only
  `optional_host_permissions`. `manifest_version: 3` is at line 2 and `activeTab`/`scripting` are at
  line 8. The observations are true; only the range is wrong. Minimal fix: cite
  `manifest.json` lines 2–25 (or `lines 2, 8, 10–25`). This was introduced by the new index, not
  present before the fix.
- No Critical or Important breakage. No finding's correction regressed another finding, and no
  source claim was upgraded to receiver evidence.

## Out-of-scope observations

1. `spikes/001-transcription/review/task-5-review.md` sits outside the brief's literal write slice
   (`spikes/002-hackerrank-claims/**` plus `review/task-5-report.md`). It is a verbatim review copy,
   declared as unedited in the report, and matches the task-3 fix-round pattern. Non-blocking;
   controller should ledger/accept it.
2. The retained review's artifact note (`task-5-review.md:7`) still says `.cache` is absent, which is
   now contradicted by the retained snapshots. It is intentionally preserved as the review of
   record and the report explains the discrepancy; non-blocking.
3. `README.md:51` (claim-table row 9) still summarizes Proctor Mode as "periodic system screenshots".
   That is true but less specific than the corrected `README.md:126-135`; it is an untouched
   pre-existing row, not a regression.

## Verdict

**Fix round: All findings addressed, no new Critical/Important breakage.** T5-01…T5-10 are
ADDRESSED. The only new defect is the Minor `SOURCES.md:28` line range.
