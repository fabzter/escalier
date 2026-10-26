# Task 5 report — Natively/HackerRank claim trace

Status: **complete (public-source research only)**. No runtime testing, interview access, GUI,
microphone, capture, inference, commits, or subagents. Files are within the task-5 ownership slice.

## Files changed

- `spikes/002-hackerrank-claims/README.md` — bounded claim trace, claim table, HackerRank-specific
  absence, invisible-vs-disguised classification, proposed synthetic matrix, limitations, sources.
- `spikes/002-hackerrank-claims/SOURCES.md` — compact public-source evidence index (URL/pin/line/
  fragment, exact code-search query and hit paths).
- `spikes/001-transcription/review/task-5-report.md` — this report.
- `spikes/001-transcription/review/task-5-review.md` — independent review copy retained as received;
  not edited.
- Local audit snapshots under `spikes/002-hackerrank-claims/.cache/` (verified present in this
  checkout and ignored by `.gitignore`): fetched READMEs, selected pinned source files, GitHub
  tree/search/tag/commit metadata, and public HackerRank/Natively page snapshots. Not intended for
  publication. The independent review's virtual artifact view did not see these ignored snapshots;
  the real checkout does, and `SOURCES.md` is the tracked index.

No other task-owned files were edited.

## Question and method

Trace what public features/evidence actually support Natively's "stealth on HackerRank" claim,
separating (a) generic window/capture/focus/input mechanisms, (b) identity disguise and network
quieting, (c) genuinely HackerRank-specific implementation, and (d) marketing/unverified claims.

Method: read the task brief, current SPEC global constraints, and preflight resolutions; reused the
existing 15-ST inventory rather than repeating the audit; pinned Natively main
`b9287ec2f24bf0ea5250625286f97248052055e9` and release `v2.9.2`
`b439c1f07f6d2d77cbca64fc0533765bd19fe7f7` (tag ref resolves directly to this commit — lightweight
tag; commit date verified); fetched the public README,
selected source, package/build identity files, and the content-protection test; fetched public
Natively docs/blog and HackerRank support pages on 2026-10-26; ran a bounded GitHub code search for
`hackerrank` and checked the relevant files at the pin. The exact search query, 27 hit paths, and
re-fetched subset are recorded in `spikes/002-hackerrank-claims/SOURCES.md#code-search`. No
interview page or invitation was opened.

## Exact public source checks

- Natively main README, lines 177–185, 189, 330–350, 1147–1169: claims "Works undetected on …
  HackerRank", "Undetectable on LeetCode, HackerRank & CoderPad", every window private, no
  Dock/taskbar/tray, system-level process disguise, Windows focus-preserving typing, analytics/crash
  off; also best-effort caveat, dedicated-proctoring exclusion, and the macOS 15.4+ modern-capture
  caveat. Release README has the same stealth/HackerRank text.
- Natively content-protection test
  `electron/audio/__tests__/OverlayContentProtectionFollowsUndetectable.test.mjs`, lines 17–20:
  the flag "only sets NSWindowSharingNone"; on macOS 15+, SCK (Zoom 5.16+, Teams, Chrome
  `getDisplayMedia` → Meet) ignores it; the test is "not a claim about SCK."
- `native-module/src/stealth_window.rs`, lines 160–186: same modern-SCK limitation; legacy
  CoreGraphics/older builds/`screencap`/OBS-without-SCK remain effective.
- `native-module/src/capture_exclusion.rs`, lines 1–23: app-owned auxiliary windows swept as
  best-effort; not a hook; not other applications' streams; `kCGWindowSharingState` measurement of
  a file picker; the macOS/Windows implementation notes are at lines 19–23.
- `electron/WindowHelper.ts`, lines 889–914: nonactivating macOS panel/Windows no-activate,
  content protection gated by mode; lines 1196–1217 tray/taskbar behavior.
- `electron/utils/macDockPolicy.ts`, lines 1–32: Dock policy measured through the Accessibility
  API; normal one tile, undetectable none.
- `electron/main.ts`, lines 9428–9494: undetectable drops remote analytics sinks and stops
  periodic egress, but explicit user actions and provider/LLM traffic remain; queued events are
  retained.
- `native-module/src/process_name.rs` and `native-module/src/lib.rs`, lines 23–29: main declares
  `stealth_window` and `capture_exclusion`, not `process_name`; the process-name SPI is unwired.
- `scripts/disguise-name.cjs` at main and `v2.9.2`; `package.json` at both revisions: release
  used build `productName: corespeechd` and Windows build `executableName: audiodg` (release
  `package.json` line 260); main reverted to `Natively`, retains `appId: com.apple.corespeechd`.
  Revert commit `293db92` (2026-10-13) matches.
- `natively-browser/src/capture/registry/registry.default.json`, line 140; manifest lines 10–25;
  `natively-browser/src/capture/classifier/tab-classifier.ts`, line 49: HackerRank-specific
  content registry, host permission, and title keyword. `natively-browser/src/extract.ts`,
  `natively-browser/src/capture/extractors/dom-helpers.ts`, `natively-browser/src/math-text.ts`,
  `natively-browser/src/formula-sheet.ts`, and `electron/services/pageCaptureFallback.ts` handle
  HackerRank sample I/O, nested statements, and formulas.
- `electron/services/screen/BrowserPageCrop.ts`, lines 1–15: full-screen capture crop used only as
  an assessment-refusal retry, motivated by a background HackerRank tab.
- `electron/llm/AnswerValidator.ts`, lines 776–804: detects "live HackerRank test" refusals and
  permits a retry; answer-pipeline behavior, not stealth.
- Natively docs: "Undetectable Interview AI" (what it hides / what it cannot hide), "Supported
  Apps" (HackerRank listed "Screen Hidden"; Zoom hardware/framebuffer, remote desktop, locked-down
  machine limits), FAQ (built not detectable against screen-share capture and task-manager process
  scans, not humans/webcam/locked-down machines), and the blog (HackerRank et al. may run
  process/focus proctoring; cloud network traffic is detectable; no tool guarantees 100%).
- HackerRank docs: browser matrix; Interview Integrity Signals (tab switching, window resize,
  copy-paste, multi-monitor; filed under Interview (Legacy) but article body does not state an
  experience qualifier); Observation Mode (explicitly legacy); Proctor Mode (screen-sharing access,
  entire-screen sharing, 15 s/5 s screenshot analysis, full-screen/tab monitoring, webcam,
  copy-paste, and an unauthorized-tool list that names invisible overlay applications); Desktop App
  Mode (blocks other apps, prevents screen sharing/screenshots, full-screen, closes other programs
  including invisible-cheating tools).

## Findings

1. **No HackerRank-specific stealth implementation found.** The HackerRank-aware runtime branches
   found are content extraction/OCR (registry, manifest, extractors, formulas), tab
   classification, page crop, and assessment-refusal retry. Capture exclusion, nonactivation,
   Dock/tray hiding, process aliases, and network quieting are generic macOS/Windows mechanisms.
2. **The headline overgeneralizes.** Natively's own test/source says `NSWindowSharingNone` is not a
   claim about modern SCK; Natively's docs say framebuffer capture, remote desktop, and locked-down
   machines are outside the guarantee. The "HackerRank — Screen Hidden" row is a compatibility
   statement, not receiver evidence.
3. **HackerRank's public modes add channels the generic mechanism does not answer.** Proctor Mode
   prompts candidates to share their entire screen, captures screenshots every 15 s (5 s around
   window-switching/full-screen violations), and explicitly lists "Specialized browser extensions
   or invisible overlay applications that assist in answering coding questions" among unauthorized
   tools. That is content analysis of captured pixels, not proof of the capture API — a truly
   excluded overlay would not appear — but it directly contradicts a blanket "Screen Hidden"
   reading. Desktop App Mode blocks apps and screenshots and closes tools in the invisible-cheating
   category. Natively explicitly excludes dedicated proctoring/lockdown. No public
   HackerRank-specific stealth test artifact was found in this bounded trace.
4. **Process disguise is release-specific and partial.** v2.9.2 had `corespeechd`/`audiodg` aliases;
   main reverted them but still carries the README claim. `process_name.rs` is unwired and the
   bundle id remains `com.apple.corespeechd`. Runtime Terminal/Activity Monitor aliases are not
   proof against path/signature/process-list inspection.
5. **Network quieting is background-only.** Hosted LLM/STT traffic and explicit user actions remain;
   local Ollama + on-device STT is the only configuration matching "no AI traffic."
6. **Evidence quality is the gap.** Public tests are static/source-contract or state models, not
   independent receiver pixels. The docs' limitations are stronger than the marketing table.
7. **Natively's public material contradicts itself at the claim boundary.** Supported Apps says
   "Nothing is added to … your browser" while the companion MV3 extension requests optional
   HackerRank host permission and `scripting`; the Undetectable page says the app "still runs as a
   normal process, so software that lists running apps can see it" while the FAQ claims task-manager
   process-scan invisibility and the README claims a system-service process name; the Undetectable
   page says the overlay is "excluded from the screen-capture output" (table: "Invisible — excluded
   from screen capture") while the repo test says that is "not a claim about SCK" and the Supported
   Apps page says framebuffer capture "captures everything".
   These are product statements at different layers, not a capability record.

## Unresolved evidence / limitations

- The reference invitation's configured HackerRank experience/mode is unknown and was not accessed.
  It is an interview scenario; Proctor/Desktop App Mode are assessment/test controls, so their
  applicability to that interview is not established. Observation Mode is explicitly legacy.
  Interview Integrity Signals is filed under `Interview (Legacy)` but its article body does not
  state an experience qualifier, so its scope is not settled. Both are closer public channels than
  the test controls, but the configured/New experience may differ.
- Natively docs/blog are unversioned; pinned README/source was used for source claims, but website
  statements are dated by fetch only.
- Code search ran on default branch `172bfbf` (ahead of the inspected pin) and is not an exhaustive
  history/binary/private-code audit. Relevant files were re-fetched at the pin.
- No runtime test: process-name behavior in main, actual focus/key-window effects, and receiver
  pixels remain unmeasured. HackerRank Proctor/Desktop App behavior is documented by HackerRank,
  not independently observed.
- The proposed matrix is local/synthetic only; it cannot establish undisclosed server-side signals
  or a real HackerRank session. No method to defeat detection is provided.

## Self-review

- Checked all cited README/source line anchors against the fetched pinned files; verified that
  `refs/tags/v2.9.2` resolves directly to the pin (lightweight tag) and both commit dates.
- Kept claims scoped to public-source evidence; no runtime or HackerRank-server claim.
- Distinguished app-owned auxiliary-window exclusion from another application's capture stream;
  distinguished release build aliases from main runtime aliases.
- No private invitation identifiers, credentials, work email, absolute home/cache paths, or
  personal data in the README or this report; no raw third-party source or HTML is intended for
  commit (ignored `.cache`).
- Did not add a product exclusion or assistance prohibition; the note only bounds public claims
  and proposes local synthetic measurement. It does not provide a method to defeat detection.
- Did not modify other workers' files, stage, commit, publish, or spawn agents.

## Review round 1 fixes

The independent review was copied unchanged to `review/task-5-review.md` as the review of record.
Its findings were checked against the cached public pages and pinned source before editing; the
medium items were adopted where the public text supports them.

| Finding | Verification check and result | Resolution |
|---|---|---|
| T5-01 legacy qualifier | Re-read the fetched Interview Integrity Signals page: the breadcrumb says `Interview (Legacy)`, but the article body has no "applies to legacy" banner. Observation Mode's body explicitly says it applies to the legacy Interview experience. | README and report now say Observation Mode is explicitly legacy; integrity-signals body scope is unstated, while noting the breadcrumb. |
| T5-02 Proctor overlay category | Re-read the fetched Proctor Mode page: "The system prompts candidates to share their entire screen"; "captures screenshots every 15 seconds"; "five seconds" after violations; unauthorized tools include "Specialized browser extensions or invisible overlay applications that assist in answering coding questions." | Added the exact category, entire-screen sharing, and 15 s/5 s cadence to the README/report, with the content-analysis caveat and test-mode applicability caveat. |
| T5-03 internal contradictions | Checked the fetched pages: Supported Apps says "Nothing is added to Zoom, to your browser, or to the meeting" and "No plugin to install"; the manifest requests optional HackerRank host permission and `scripting`. Undetectable says "still runs as a normal process, so software that lists running apps can see it"; FAQ claims task-manager process-scan invisibility. Undetectable says the overlay is "excluded from the screen-capture output" (table: "Invisible — excluded from screen capture"); the repo test says "not a claim about SCK"; Supported Apps says framebuffer sharing "captures everything." | Added an internal-contradictions subsection and finding; kept the existing conclusion. |
| T5-04 citation precision | Checked full paths and line numbers: tab classifier is `natively-browser/src/capture/classifier/tab-classifier.ts:49`; release `package.json` Windows executable is line 260; `capture_exclusion.rs` implementation notes are lines 19–23. | Replaced tree links with blob/line anchors, added full paths and the release line-260 link; corrected the report range. |
| T5-05 lightweight tag | Checked `git/ref/tags/v2.9.2`: object type is `commit` (not an annotated tag object); it points directly to `b439c1f`. | Changed "tag object checked/verified" to "tag ref resolves directly to the commit (lightweight tag)" in README, report and self-review. |
| T5-06 ST map | Re-read the prior ST table: ST-04 is notification/prompt suppression and the "Nothing it opens leaks" claim includes notifications; ST-08 is click-through. | Added ST-04 and ST-08 to the touched-row mapping. |
| T5-07 004 scope | Re-read `spikes/004-window-capture-focus/PLAN.md`: 004 allows a generic owned display-title experiment but forbids process-name injection; it excludes microphone/live audio and does not define a network probe. | Split identity into title/AX/tooltip (004) vs executable/process (outside 004); marked network/STT outside 004; added explicit approval note. |
| T5-08 wording risk | Re-read the brief's "no additional product exclusion" constraint and the owner direction to record unsupported gaps. | Replaced "not designed for locked-down proctoring" with "no demonstrated capability under locked-down proctoring; any product-scope decision remains open." |
| T5-09 evidence retention | Verified the actual ignored `.cache/evidence/` and `.cache/source/` snapshots exist in this checkout; the review's virtual view did not see them. The spike-local review package also exists at `spikes/001-transcription/.tools/reviews/task-5.diff` (ignored, not root `.tools/`). | Retained `SOURCES.md` as the tracked compact index and corrected the report's file/changed-path note; raw HTML remains untracked. |
| T5-10 search reproducibility | Re-checked the API result (`total_count: 27`, `incomplete_results: false`) and default-branch head (`172bfbf`, 9 ahead of pin, 0 behind). | Recorded the exact query, all 27 hit paths, and the re-fetched subset in `SOURCES.md#code-search`. |

Changed paths in this round: `spikes/002-hackerrank-claims/README.md`,
`spikes/002-hackerrank-claims/SOURCES.md` (new), `spikes/001-transcription/review/task-5-report.md`,
and `spikes/001-transcription/review/task-5-review.md` (independent review copy only).

Remaining uncertainties: HackerRank's screenshot capture API and the configured interview mode are
still not publicly specified; the SCK-to-HackerRank link is a risk inference, not a measured
result. The integrity-signals article body scope remains unstated (breadcrumb only). No runtime or
receiver-pixel evidence was added. The code search default branch is ahead of the pin; the
re-fetched subset is recorded, and the absence claim remains bounded.
