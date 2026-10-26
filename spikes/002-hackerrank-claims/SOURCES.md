# Public-source evidence index

Companion to [README.md](README.md). This is the compact, readable index; raw fetched snapshots
are retained in this checkout under the git-ignored `.cache/evidence/` and `.cache/source/`
directories (verified present 2026-10-26). No raw HTML or third-party implementation is tracked.
All sources below are public; no invitation, private page, credential, or `.omp` state is included.

Pins: main `b9287ec2f24bf0ea5250625286f97248052055e9` (committed 2026-10-25); release `v2.9.2`
`b439c1f07f6d2d77cbca64fc0533765bd19fe7f7` (lightweight tag resolves directly to the commit;
committed 2026-10-05). Public web pages fetched 2026-10-26; they are unversioned.

## Pinned source checks

| Check | Location | Observation |
|---|---|---|
| README HackerRank heading and "works undetected" list | main `README.md` lines 330–350 | "Undetectable on LeetCode, HackerRank & CoderPad"; "Works undetected on: … HackerRank"; proctoring exclusion immediately below. Same text at `v2.9.2`. |
| README stealth inventory | main `README.md` lines 177–185, 189 | Every window private; "Nothing it opens leaks"; no Dock/taskbar/tray; process disguise; Windows typing; analytics/crash off; best-effort caveat. |
| README FAQ | main `README.md` lines 1147–1169 | "In the meeting apps we test, yes"; macOS 15.4+ caveat; HackerRank answered by screenshot + OCR; dedicated-proctoring exclusion. Same text at `v2.9.2` with shifted lines. |
| Content-protection limit | `electron/audio/__tests__/OverlayContentProtectionFollowsUndetectable.test.mjs` lines 17–20 | Flag "only sets NSWindowSharingNone"; macOS 15+ SCK ignores it; test is "not a claim about SCK." |
| Native sharing-type limit | `native-module/src/stealth_window.rs` lines 160–186 | Same macOS 15+ SCK framebuffer limitation; effective on macOS ≤14, older Zoom/Loom, `screencap`, OBS without SCK, native screenshot APIs. |
| Auxiliary-window sweep | `native-module/src/capture_exclusion.rs` lines 1–23 | App-owned non-BrowserWindow windows only; sweep, not hook; measured picker had `kCGWindowSharingState` 1 while launcher read 0. |
| Nonactivating/focus setup | `electron/WindowHelper.ts` lines 889–914; 1196–1217 | macOS `type: 'panel'`, Windows `WS_EX_NOACTIVATE`, content protection gated by mode; tray/taskbar handling. |
| Dock policy | `electron/utils/macDockPolicy.ts` lines 1–32 | One normal-mode tile, none undetectable; measured through Accessibility API per header. |
| Network policy | `electron/main.ts` lines 9428–9494 | Remote sinks/outbox/funnel/model scheduler/Hindsight stop; queued events retained; explicit actions and provider traffic remain. |
| Process-name module unwired | `native-module/src/process_name.rs`; `native-module/src/lib.rs` lines 23–29 | File exists; `lib.rs` declares `stealth_window`/`capture_exclusion`, not `process_name`. |
| Release/main identity | main and `v2.9.2` `scripts/disguise-name.cjs`; `package.json` lines | Main: `productName: Natively`, appId `com.apple.corespeechd` (`package.json` 141/144). Release: build `productName: corespeechd` (line 143), Windows `executableName: audiodg` (line 260). Revert `293db92` (2026-10-13). |
| HackerRank content registry | `natively-browser/src/capture/registry/registry.default.json` line 140 | HackerRank `codingProblem` extractor, host/url patterns, selectors, sample/constraint hints. |
| Companion host permission | `natively-browser/src/manifest.json` lines 2, 8, 10–25 | Optional `https://www.hackerrank.com/*` host permission; MV3; `activeTab`/`scripting` permissions. |
| Tab classifier | `natively-browser/src/capture/classifier/tab-classifier.ts` line 49 | `hackerrank` in problem-title keywords; generic URL/title tokens. |
| Page crop | `electron/services/screen/BrowserPageCrop.ts` lines 1–15 | Full-screen capture crop; only a retry after an assessment refusal; background HackerRank tab motivating case. |
| Refusal retry | `electron/llm/AnswerValidator.ts` lines 776–804 | Detects "live HackerRank test" refusal wording and points at retry. |
| Window-title guard | `electron/utils/windowTitleGuard.ts` lines 1–6 | Window title kept neutral in undetectable mode; generic proctor-enumeration rationale. |

## Quoted public fragments

Short fragments only; full snapshots are in the ignored `.cache/evidence/`.

| Source | Fragment / result |
|---|---|
| Natively Supported Apps (`https://heynatively.com/supportedapps`) | HackerRank listed "Screen Hidden"; coding/assessment "run in a browser, so what matters is screen capture and OCR rather than any platform API"; "Nothing is added to Zoom, to your browser, or to the meeting"; "No plugin to install". |
| Natively Undetectable Interview AI (`https://heynatively.com/undetectable-interview-ai`) | "It still runs as a normal process, so software that lists running apps can see it"; overlay "excluded from the screen-capture output"; what it cannot hide includes process-list software and a cloud provider connection. |
| Natively FAQ (`https://heynatively.com/docs/faq`) | "Against screen-share capture and task-manager process scans, it is built not to be"; not against humans/webcam/locked-down machines; Zoom hardware-accelerated exception. |
| Natively blog, 2026-03-04/modified 2026-10-22 (`https://heynatively.com/blog/is-ai-interview-assistant-detectable`) | HackerRank/Codility/Karat "may run proctoring software that scans running processes, detects window-focus switching, or requires a locked-down browser"; cloud AI traffic visible; "no tool can promise 100% undetectability." |
| HackerRank Interview Integrity Signals (`https://support.hackerrank.com/articles/5161582600-interview-integrity-signals`) | Copy-paste, window resize, tab switching, multi-monitor; page is under `Interview (Legacy)` breadcrumb but article body does not state an experience qualifier. |
| HackerRank Observation Mode (`https://support.hackerrank.com/articles/1263202297-observation-mode-in-interviews`) | "This article applies to the legacy Interview experience"; real-time screen-activity observation similar to screen sharing. |
| HackerRank Proctor Mode (`https://support.hackerrank.com/articles/5663779659-proctor-mode`) | Screen-sharing access; "share their entire screen"; screenshots every 15 s, 5 s around violations; unauthorized tools include "Specialized browser extensions or invisible overlay applications that assist in answering coding questions"; test/AI add-on. |
| HackerRank Desktop App Mode (`https://support.hackerrank.com/articles/5973590014-hackerrank-desktop-app-mode`) | Prevents remote access, screen sharing, screenshots; blocks other apps; full-screen; multiple-monitor/mirroring checks; closes other programs including invisible cheating tools; test/AI add-on. |
| HackerRank browser recommendations (`https://candidatesupport.hackerrank.com/articles/8455316478-browser-recommendations-for-hackerrank-interviews`) | Firefox: Legacy supported, New not supported; Chrome/Edge: both supported. |

## Code search

Exact query used on 2026-10-26:

```text
gh api -X GET search/code -H 'Accept: application/vnd.github.text-match+json' \
  -f q='hackerrank repo:Natively-AI-assistant/natively-cluely-ai-assistant'
```

Result: `total_count: 27`, `incomplete_results: false`. The search ran against the repository
default branch `172bfbfb81e792a4bc7a78096ec010971051b8ba` (9 commits ahead of the inspected pin;
`b9287ec...172bfbf` compare: ahead_by 9, behind_by 0). Hit paths:

```text
README.md
electron/llm/codingShape.ts
natively-browser/src/extract.ts
electron/llm/AnswerValidator.ts
electron/llm/codingContract.ts
natively-browser/src/math-text.ts
natively-browser/src/formula-sheet.ts
electron/services/pageCaptureFallback.ts
electron/MeetingPersistence.ts
electron/llm/codingPromptSignals.ts
electron/llm/answerPlannerPatterns.ts
electron/llm/customContextClassifier.ts
electron/services/screen/BrowserPageCrop.ts
natively-browser/src/capture/extractors/dom-helpers.ts
electron/services/meeting/MeetingSummaryV3.ts
natively-browser/src/manifest.json
natively-browser/src/capture/classifier/tab-classifier.ts
natively-browser/src/capture/registry/registry.default.json
natively-browser/src/__tests__/math-text.test.mjs
natively-browser/src/__tests__/formula-image.test.mjs
electron/services/__tests__/BrowserPageCrop2026_10_25.test.mjs
natively-browser/src/__tests__/registry.test.mjs
natively-browser/src/__tests__/permissions.test.mjs
electron/llm/__tests__/CodexHeldOutputStall2026_10_25.test.mjs
electron/llm/__tests__/CodingTemplateContract2026_08_18.test.mjs
electron/services/meeting/__tests__/MeetingTitleInNotesCall2026_10_18.test.mjs
electron/services/__tests__/PageCaptureUnreadableFormulas2026_10_24.test.mjs
```

Re-fetched at pin `b9287ec` (stored under ignored `.cache/source/`; README snapshots under
`.cache/evidence/`): `README.md`, `electron/llm/codingShape.ts`, `natively-browser/src/extract.ts`,
`electron/llm/AnswerValidator.ts`, `electron/services/pageCaptureFallback.ts`,
`electron/llm/codingPromptSignals.ts`, `electron/services/screen/BrowserPageCrop.ts`,
`natively-browser/src/manifest.json`, `natively-browser/src/capture/classifier/tab-classifier.ts`,
`natively-browser/src/capture/registry/registry.default.json`. The remaining hits were inspected
through the search text matches only (including `dom-helpers.ts`, `math-text.ts`,
`formula-sheet.ts`, `codingContract.ts`, the test files, and meeting-title examples); no
stealth/window/process file appears in the hit list. This is a bounded search, not proof of absence
in history, binaries, private branches, or every large generated file.
