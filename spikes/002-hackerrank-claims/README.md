# Natively/HackerRank claim trace

Bounded public-source trace, 2026-10-26. Status: **research only — no runtime test, no interview
access, no receiver-pixel evidence.** This answers a narrow question: what public features and
source-level evidence support Natively's claim to be stealthy on HackerRank, and where does that
claim outrun the implementation or its own published limits?

The 15-group inventory in
[the existing research](../../docs/analysis/2026-10-26-live-asr-and-browser-privacy.md#5-natively-stealth-parity-inventory)
is authoritative prior work. This note does not repeat that audit. It traces the HackerRank claim
to the pinned Natively revisions, separates generic stealth mechanics from HackerRank-specific
code, and records the honest gaps.

## Scope and method

- Natively inspected main: `b9287ec2f24bf0ea5250625286f97248052055e9` (committed 2026-10-25).
- Released `v2.9.2`: `b439c1f07f6d2d77cbca64fc0533765bd19fe7f7` (tag ref resolves directly to
  this commit — lightweight tag; commit date 2026-10-05 verified).
- Public README, Natively docs/blog, and HackerRank support pages were fetched on 2026-10-26.
  README claims are pinned by revision and line; public web pages are dated by fetch date because
  they are unversioned.
- A bounded GitHub code search for `hackerrank` (repository default branch `172bfbfb81e7`, nine
  commits ahead of the inspected pin; 27 hits) was used to find platform-specific strings. The exact
  query, hit paths, and which files were re-fetched at the pin are recorded in
  [SOURCES.md](SOURCES.md#code-search). This is a search, not proof of absence in history,
  binaries, private branches, or every large generated file.
- HackerRank's public documentation was used for platform behavior. No invitation, interview page,
  assessment, GUI, microphone, call, or live session was accessed. The private invitation's
  configured experience remains unknown.

The question is deliberately claim-focused, not an evasion guide. Public source and documentation
can establish mechanisms and published limits; they cannot establish undisclosed server-side
detection or receiver pixels.

## Claim-to-mechanism trace

Abbreviations: **G** = generic mechanism, **H** = HackerRank-specific mechanism, **M** = marketing
or unverified generalization. Classification is about what the evidence supports, not whether the
product works.

| # | Public claim (pinned/dated source) | Mechanism found | Class | Evidence limit |
|---|---|---|---|---|
| 1 | "Works undetected on: … HackerRank"; "Undetectable on LeetCode, HackerRank & CoderPad" — README main `#L330-L350`, same at `v2.9.2`; the supported-apps page also lists HackerRank as "Screen Hidden" in its coding/assessment table | No HackerRank-specific stealth branch. The claim resolves to the generic window/identity/network mechanisms below. HackerRank appears in capture/OCR and answer-pipeline code, not in capture-exclusion or process-disguise code. | **M** | A platform-wide "undetected" conclusion is not established by a window flag. Natively's own test says the flag is not a claim about ScreenCaptureKit (SCK), and its docs except locked-down machines and process-list software. "Screen Hidden" in a compatibility table is a product statement, not a receiver-pixel result. |
| 2 | "Screenshot + OCR … works on LeetCode, HackerRank, CoderPad" — README `#L344-L348`, FAQ `#L1163-L1165` | Browser companion registry entry for `hackerrank.com` with `codingProblem` extractor, host patterns `/challenges/` and `/test/`, HackerRank selectors, sample/constraint hints; optional host permission in the MV3 manifest; HackerRank-specific extraction of sample I/O, nested `.problem-statement`, and formula handling. | **H (content), not stealth** | Establishes that HackerRank page content can be read and sent to the answer pipeline. It says nothing about whether the assistant or its overlay is visible to HackerRank, a browser capture, a proctor, or a network observer. |
| 3 | "Every Natively window is marked private, so Google Meet, Teams, QuickTime and Zoom (with window filtering) leave it out"; "Nothing it opens leaks" — README `#L177-L180` | `WindowHelper.setContentProtection()` calls `win.setContentProtection(enable)`; a 500 ms idempotent re-assertion loop; native `stealth_window.rs` also sets `NSWindowSharingNone`; `capture_exclusion.rs` sweeps all other top-level windows owned by the app (file pickers, message boxes, tooltips, `<select>` popups, context menus). | **G, invisible only on capture paths that honor the flag** | The native source says macOS 15+ SCK "IGNORES this flag" and captures from the compositor framebuffer; it remains effective on macOS ≤14, older Zoom, older Loom, `screencap`, OBS without SCK, and most native screenshot APIs. The sweep is not a hook and covers only windows owned by the app, not another application's stream. The source gates protection on undetectable mode; normal mode is intentionally visible in captures. |
| 4 | "No Dock icon, no taskbar button, no tray icon" — README `#L181` | `macDockPolicy.ts` enforces one normal-mode tile and none in undetectable mode; `main.ts` destroys the tray and removes the Windows taskbar button while undetectable. The policy was measured through the macOS Accessibility API, per its comments. | **G, invisible on those OS surfaces** | Hides OS chrome, not pixels, window titles, process names, accessibility trees, menu items owned by other apps, or a remote receiver. No public receiver-pixel artifact was found in this trace. |
| 5 | "A system-level process disguise on macOS and Windows … a process list shows a system service" — README `#L182` | Release `v2.9.2` configured build `productName: corespeechd` and Windows `build.win.executableName: audiodg`; its `disguise-name.cjs` comments describe the aliases as real system processes chosen to pass a "known system process?" check. Main reverted both to `Natively` (commit `293db92`, 2026-10-13) while keeping `appId: com.apple.corespeechd`; main's comment explicitly frames the trade as the executable basename not reading as "Natively" to a "proctoring scanner". Main's `process_name.rs` exists but is not declared in `native-module/src/lib.rs`; runtime `disguiseAppName.ts` sets `process.title`/`app.setName` to Terminal/System Settings/Activity Monitor. | **G, disguised and version-specific** | The full on-disk alias claim is supported for the released build, not for main. Runtime aliases are a display/menu/title disguise, not proof against Activity Monitor, `proc_pidpath`, code-signature inspection, executable-path enumeration, or a process scanner that looks beyond the basename. The `com.apple.corespeechd` bundle id remains in main. |
| 6 | "Type without losing focus (Windows)" — README `#L184` | `StealthKeyboardManager` routes keys through a Windows low-level hook (and a macOS event tap); the overlay uses a nonactivating panel/`WS_EX_NOACTIVATE` treatment. | **G, input/focus** | Windows-specific public claim; no HackerRank test. Secure Event Input, IME behavior, accessibility permission, and exact focus transitions need independent testing. A nonactivating window can still change which window is key; that is not the same as leaving the browser's focus state untouched. |
| 7 | "Third-party analytics and crash reporting switch off for as long as Undetectable mode is on" — README `#L185`; "quiet on the network" | `main.ts` drops PostHog/Axiom/Sentry sinks, stops the usage outbox, funnel telemetry, model-discovery scheduler, and local/Cloud sync while undetectable. Queued events are retained locally. | **G, quieting — partial** | Explicit user actions, manual update/download, calendar connect, and product traffic (LLM answers) remain; STT is not swapped. With a cloud provider or hosted STT, network traffic still exists. The blog itself says cloud AI traffic is a detection vector. Only local Ollama plus on-device STT gives the "no AI traffic" story. |
| 8 | "Tested against screen share detection in Zoom, Teams, and Google Meet" — README `#L1149` | No public receiver-pixel or independent capture test artifact found. The inspected stealth tests assert source/state contracts or UI state; the content-protection test explicitly says it is "not a claim about SCK". Natively's docs/supported-apps page instead admits modern framebuffer capture, remote desktop, webcam, and locked-down machines as limits. | **M / unverified** | Source comments and internal tests are not independent measurements. This trace found no public evidence that a separate receiver actually saw no pixels in each named app, on the relevant macOS version and capture path. |
| 9 | "Not designed to bypass dedicated proctoring … Pearson VUE, ProctorU, Respondus Lockdown Browser" — README `#L189`, `#L350`, `#L1169` | Explicit scope limit repeated in the README and docs. Natively's FAQ says it is built not to be detectable "against screen-share capture and task-manager process scans", but not against a human, webcam proctor, or locked-down machine it does not control. The supported-apps page lists remote desktop as visible and a locked-down proctoring machine as "not applicable". | **scope limit, honest** | This is the strongest public limitation and it materially bounds the HackerRank claim. HackerRank's own public modes include more than ordinary window sharing: Proctor Mode requests screen-sharing access and periodic system screenshots; Desktop App Mode blocks other applications and screenshots. |
| 10 | HackerRank-specific product behavior beyond OCR | `BrowserPageCrop.ts` crops the browser chrome (including a background "HackerRank Test Login" tab) only as a retry after an assessment refusal; `AnswerValidator.ts` detects a "live HackerRank test" refusal and permits a retry. Browser registry/manifest and tab-classifier entries are content routing. | **H (answer pipeline), not stealth** | These branches address reading the prompt and obtaining an answer after a model refusal. They do not hide the app, alter HackerRank telemetry, or counter Proctor/Desktop App monitoring. The crop is best-effort and never modifies the original capture. |

Inventory mapping (prior 15-ST rows, not re-audited): capture policy and re-assertion ST-01/ST-02;
auxiliary windows ST-03; notification/prompt suppression ST-04; Dock/tray ST-05/ST-06;
nonactivation/click-through ST-07/ST-08; input ST-09; title/tooltip ST-10; runtime/build identity
ST-11/ST-12; own screenshots ST-13; network quieting ST-14; outside-control surfaces ST-15. The
HackerRank claim touches ST-01/02/03/04/05/06/07/08/09/10/11/12/14 and depends on which of ST-15's
external surfaces — proctor capture, webcam, locked-down OS — is active.

## What is genuinely HackerRank-specific

The bounded search found HackerRank-aware code in these areas only:

- **Browser companion extraction:** `natively-browser/src/capture/registry/registry.default.json`
  has an explicit HackerRank entry (`hostPatterns`, `urlPatterns`, `codingProblem` extractor,
  statement/code selectors, sample and constraint hints). `natively-browser/src/manifest.json`
  requests optional host permission for `https://www.hackerrank.com/*`.
- **Extraction and page handling:** `natively-browser/src/extract.ts`,
  `natively-browser/src/capture/extractors/dom-helpers.ts`,
  `natively-browser/src/math-text.ts`, `natively-browser/src/formula-sheet.ts`, and
  `electron/services/pageCaptureFallback.ts` contain HackerRank-specific comments and handling for
  sample I/O, nested problem statements, MathJax/SVG formulas, and page-capture fallback.
- **Tab classification:** `natively-browser/src/capture/classifier/tab-classifier.ts` includes
  `hackerrank` as a problem-title keyword and generic coding/assessment URL tokens.
- **Screenshot crop:** `electron/services/screen/BrowserPageCrop.ts` describes a background
  HackerRank tab as the motivating case for cropping browser chrome after a refusal.
- **Refusal retry:** `electron/llm/AnswerValidator.ts` and tests treat "live HackerRank test" as an
  assessment-refusal phrase.

**Honest absence:** this trace found no HackerRank-specific capture-exclusion, window-hiding,
process-disguise, focus, network-quieting, or anti-proctoring branch. The public "undetected on
HackerRank" claim is therefore a generalization from generic macOS/Windows stealth, plus the
content-reading feature. Natively's own supported-apps page says coding/assessment platforms "run
in a browser, so what matters is screen capture and OCR rather than any platform API" — which is
content support, not a HackerRank integration. That is not the same as platform-specific evasion,
and the public documentation itself says the product is not designed for dedicated
proctoring/lockdown.

## Invisible vs disguised

| Capability | Better description | What is actually hidden | What remains observable |
|---|---|---|---|
| Window content protection | **Conditionally invisible** | App windows on capture paths that honor `NSWindowSharingNone`/content protection; app-owned auxiliary windows during the sweep. | Modern SCK/framebuffer capture, remote desktop, other apps' streams, a camera, and any receiver that does not honor the flag. |
| Dock/taskbar/tray | **Hidden OS surface** | Dock tile, taskbar button, tray icon while undetectable. | Process list, window list, accessibility tree, menu-bar items, screen pixels, title/identity. |
| Runtime app/process name | **Disguised** | Menu name, `process.title`, some displayed identity. | Executable path/name, bundle id, code signature, LaunchServices records, process scanners with more than a basename check. |
| Build-time identity aliases | **Disguised, release-specific** | Released `v2.9.2` executable/helper basenames (`corespeechd`, `audiodg`). | Main is back to `Natively`; display name, bundle id, signature, resources, and any historical/OS records can still differ. |
| Network quieting | **Quieted, not invisible** | Background analytics/crash reporting, usage outbox dispatch, funnel, discovery, sync. | Provider/LLM/STT traffic with hosted services, explicit user actions, queued local events that drain later, DNS/TLS metadata. |
| HackerRank OCR/extraction | **Content feature** | Nothing about assistant presence. | The assistant still has to run, capture, display, and communicate; the platform can observe whatever its own mode observes. |

Natively's own docs state the boundary directly: "What it cannot hide: … software that lists
running processes, such as some proctoring tools and lockdown browsers; and, with a cloud provider,
the connection to that provider." That is a published limitation: the window-hiding mechanism is
not a complete HackerRank-detection answer.

## HackerRank's public monitoring modes

These are the platform-side facts that bound any "undetected on HackerRank" statement. They are
public documentation, not a claim that every session enables every mode. Observation Mode's page
explicitly says it applies to the legacy Interview experience. The Interview Integrity Signals page
is filed under the `Interview (Legacy)` collection/breadcrumb, but its article body does not carry
the same banner, so its experience scope is not explicitly stated; the New Interview Experience and
a given company's configuration may differ. Proctor/Desktop App Mode are Test/Screen controls. The
browser matrix (Firefox: Legacy supported, New unsupported; Chrome/Edge: both) is compatibility
context, not evidence of which capture backend is active.

- **Interview integrity signals (filed under Interview (Legacy); article body does not state an
  experience qualifier):** HackerRank documents grouped alerts for multiple copy-paste actions,
  frequent window resizing, and repeated tab switching; the detailed list also includes "Out of
  Interview" tab switching, copy/paste, window resize, and multi-monitor setup (Chrome only for the
  display-access check).
- **Observation Mode (explicitly legacy interview):** real-time observation of the candidate's
  screen activity, described as similar to screen sharing, focused on actions inside the HackerRank
  interview interface. It does not follow that this is an OS-wide framebuffer capture, but it is a
  platform-side observation channel.
- **Proctor Mode (AI add-on, test control):** candidates grant webcam, multiple-monitor check,
  screen-sharing access, and full-screen mode. HackerRank says screen sharing is used to monitor
  screen activity and verify no unauthorized applications/resources. Screenshot analysis prompts
  candidates to share their **entire screen**, captures screenshots every 15 s (tightening to 5 s
  around window-switching/full-screen violations), and its unauthorized-tool list explicitly
  includes "Specialized browser extensions or invisible overlay applications that assist in
  answering coding questions." Tab switching/full-screen exit, copy-paste, webcam, and multi-monitor
  events are also monitored.
- **Desktop App Mode (AI add-on, test control):** native Windows/macOS test client; prevents
  remote access, screen sharing, and screenshots; blocks other applications; enforces full-screen;
  checks for multiple monitors and screen mirroring; application monitoring detects and closes other
  programs, including tools it names as invisible cheating tools; webcam/gaze checks are available.
  This is a locked-down machine environment, which Natively's own supported-apps page marks "not
  applicable".

Consequences for the claim:

1. The generic window-hiding mechanism is not a HackerRank-specific countermeasure. It is one
   input to whether a browser or proctor's capture sees the overlay.
2. HackerRank Proctor Mode's entire-screen sharing and 15 s/5 s screenshot analysis are the closest
   public analogue to a receiver, and its unauthorized-tool list explicitly names "Specialized
   browser extensions or invisible overlay applications that assist in answering coding questions."
   That is content analysis of captured pixels, not proof of the capture API: a truly excluded
   overlay would not appear in those screenshots. It does, however, directly contradict a blanket
   "Screen Hidden" reading. Natively's own source says the exclusion flag is not a claim about the
   modern SCK path used by Chrome `getDisplayMedia` and current Zoom/Teams; HackerRank's public docs
   do not name the capture API it uses, so applying that limitation to HackerRank is a risk
   inference, not a measured HackerRank result.
3. Desktop App Mode is outside the product's stated scope. Its application monitoring and
   screenshot/blocking controls are a different category from window-level exclusion.
4. HackerRank's behavioral signals (tab switch, window resize, copy-paste, multi-monitor) are not
   addressed by hiding a window. A nonactivating overlay may avoid *some* app-switch behavior, but
   that is a design hypothesis, not a measured result, and clicking/typing into the overlay can
   change the key window in ways that need a focus-event test.
5. No public source in this trace shows Natively testing against a HackerRank session, Proctor
   Mode, Desktop App Mode, or a HackerRank-style periodic screenshot receiver.

### Internal contradictions in Natively's public material

Three vendor statements are not mutually consistent, and they show why the compatibility table
cannot be treated as a capability record:

- **Browser presence:** the Supported Apps page says "Nothing is added to Zoom, to your browser, or
  to the meeting" and "No plugin to install". The repository includes a companion MV3 extension
  with `activeTab`/`scripting` permissions and an optional
  `https://www.hackerrank.com/*` host permission. It is an opt-in browser addition for page
  capture, not a video-call integration, but it is still a browser extension.
- **Process-list visibility:** the Undetectable page says Natively "still runs as a normal process,
  so software that lists running apps can see it". The FAQ says it is built not to be detectable
  "against … task-manager process scans", and the README says a process list shows a system
  service. Release `v2.9.2` had build-time aliases; main reverted them. These statements can be
  reconciled only by naming the build, observer, and process-name source.
- **Capture guarantee:** the Undetectable page says the overlay is "excluded from the screen-capture
  output" and its comparison table says "Invisible — excluded from screen capture". The repository's
  own test says the flag is "not a claim about SCK", and the Supported Apps page says Zoom's
  hardware-accelerated/framebuffer sharing "captures everything".

The trace therefore uses the pinned source/test for mechanism evidence and the docs for published
limits, not as receiver proof. The contradictions strengthen the existing conclusion; they do not
change it.

## Proposed synthetic capture/focus matrix

This is a proposal, not a run. Execution for the synthetic AppKit/browser cases belongs to
[Spike 004](../004-window-capture-focus/PLAN.md), which already owns the synthetic AppKit fixture,
local browser page, and manual permission-gated runtime matrix. This trace adds claim-oriented
cases; it does not claim any of them has passed. Rows marked **outside 004** are not in its current
`PLAN.md` and require separate coordinator approval; they must not be read as planned 004 work.

### Fixtures and observers

- **Sender:** synthetic Escalier window with a clearly labelled private-marker panel and a
  separate unprotected control marker; optional auxiliary surface (tooltip/dialog/popover).
- **Receiver:** a second local browser/process or a local recorder that displays actual received
  frames. A sender preview is not evidence.
- **Focus probe:** local static page logging `focus`, `blur`, `visibilitychange`, and
  `document.hasFocus()` before/after clicking and typing into the overlay.
- **OS probe:** window list/sharing state, `NSWorkspace` frontmost application, and
  menu/Dock/taskbar state. Process list/executable path is observational only and belongs to the
  outside-004 identity row. Read back requested versus observed values.
- **Network probe (outside 004):** local proxy/log for background and provider traffic; no external
  service, microphone, or live audio. 004 excludes audio/STT, so this requires separate approval.
- **No real HackerRank page, invitation, assessment, or server-side signal is used.** HackerRank
  Proctor Mode and Desktop App Mode cannot be reproduced by a local synthetic page; they remain
  documentation-only limitations.

### Matrix

| Dimension | Cases | Observation that counts |
|---|---|---|
| Capture source | Selected window; entire display | Receiver pixels show private marker vs control marker. Selected-window and full-display results are separate. |
| Capture backend | Legacy CoreGraphics/window capture; modern SCK; Chrome `getDisplayMedia`; Firefox capture; Zoom window-filtered vs hardware/framebuffer; QuickTime/Meet/Teams where available | Which path honors the flag; do not generalize one path to another. |
| Surface | Overlay, launcher, settings, notes, model selector, file picker, tooltip/`<select>`, notification, menu bar/Dock/taskbar | Each surface separately; auxiliary sweep is not a hook. |
| Mode/lifecycle | Normal; undetectable; launch with undetectable on; toggle off/on; show/hide; screenshot restore; meeting start/stop | Requested and re-asserted state after each transition; leaked window or tile. |
| Focus/input | Click overlay; type into overlay; submit/Escape; click back to browser; IME/Secure Input where available | Browser focus/blur/visibility log; global frontmost app; key-window identity; no assumption that nonactivating means unchanged page focus. |
| Identity: title/AX/tooltip (004) | Generic owned display title; window title; accessibility label; tooltip | What each observer actually sees in the title/AX/menu/tooltip layers. |
| Identity: executable/process (outside 004) | Release-style aliases vs main runtime aliases; process name/path; bundle id; signature | What each observer sees in process/path/signature layers; requires a separately approved build/process experiment (004 forbids process-name injection). |
| OS/version | macOS ≤14 vs 15+; Windows 10 pre-2004 vs 2004+; supported/unsupported Linux | Backend-specific result; no cross-OS inference. |
| Network (outside 004) | Background idle vs hosted-LLM egress; queued-event drain after toggle off. No microphone, STT, or live audio. | Egress during background idle vs active answer; requires a separately approved network probe. |

Rows marked **outside 004** are proposals for a future approved probe, not deliverables of Spike 004.

### Acceptance boundary

A row is only evidence if the independent receiver sees the private marker absent while the
control marker is present, with the exact OS/browser/capture path recorded. A requested flag, a
sender preview, a source-level assertion, or a passing unit test is **not** receiver evidence.
No row may use a real interview or an undisclosed HackerRank signal. This matrix is not an
instruction to evade a proctoring system; it measures whether the stated mechanisms are visible
to a local capture path.

## Findings

1. **The HackerRank claim is composite, and only the content/answer-pipeline half is
   HackerRank-specific.** The product can read HackerRank problem pages through a companion
   registry/extractor. Its stealth story is generic macOS/Windows window policy, OS-chrome hiding,
   process/title aliases, and partial network quieting. No HackerRank-specific invisibility
   implementation was found.
2. **Public evidence narrows "invisible" more than the headline does.** Natively's own test says
   `NSWindowSharingNone` is not a claim about SCK; the native source says macOS 15+ SCK ignores the
   flag; the docs say Zoom hardware-accelerated/framebuffer capture grabs everything, remote
   desktop is visible, and a locked-down proctoring machine is not applicable. The README's
   "macOS 15.4+" caveat is consistent in direction, though it differs from the source comment's
   "macOS 15+". The supported-apps page's "HackerRank — Screen Hidden" row is therefore a
   compatibility statement about window-based capture, not a guarantee across HackerRank modes.
   Natively does publish a broad best-effort caveat and a dedicated-proctoring exclusion; a warning
   follows the HackerRank list, but the HackerRank-named heading/table itself does not repeat those
   caveats.
3. **HackerRank's public modes add channels the claim does not address.** Proctor Mode prompts
   candidates to share their entire screen, captures screenshots every 15 s (5 s around violations),
   and explicitly lists "Specialized browser extensions or invisible overlay applications that
   assist in answering coding questions" as unauthorized tools. That is content analysis of
   captured pixels, not proof of the capture API, but it directly contradicts a blanket "Screen
   Hidden" reading. Integrity signals cover tab switching, window resize, copy-paste, and
   multi-monitor; Desktop App Mode blocks other apps and screenshots and closes tools in the
   invisible-cheating category. This is platform-specific verification, not something the generic
   window flag answers.
4. **The process-disguise claim is release-specific and only partial.** `v2.9.2` shipped
   `corespeechd`/`audiodg` aliases; main reverted them but still carries the README claim, with
   `process_name.rs` unwired and `com.apple.corespeechd` left as the bundle id. The main build's
   runtime aliases are not evidence against a process list that checks paths, signatures, or
   LaunchServices records.
5. **Network quieting is background-only.** Third-party analytics/crash sinks and scheduled egress
   stop; hosted LLM/STT traffic and explicit user actions remain. The local Ollama + on-device STT
   configuration is the only one matching the "no AI traffic" marketing story. HackerRank-side
   network monitoring would see provider traffic if a hosted model is used.
6. **Evidence quality is the main gap.** The inspected stealth tests are source/state/UI contract
   checks or behavioural models; there is no public receiver-pixel or HackerRank-specific capture
   artifact. The docs' explicit limits are stronger evidence than the "works undetected on
   HackerRank" table.
7. **This is not proof of HackerRank detection or non-detection.** It is a claim trace: public
   mechanisms, public limits, and the absence of platform-specific stealth code. A synthetic
   capture/focus run could establish local receiver behavior; it cannot establish undisclosed
   server-side behavior or a real HackerRank session.
8. **Natively's own public material contradicts itself at the claim boundary.** The Supported Apps
   page says nothing is added to the browser, but the companion MV3 extension requests optional
   HackerRank host permission. The Undetectable page says software that lists running apps can see
   it, while the FAQ claims task-manager process-scan invisibility and the README claims a
   system-service process name. The Undetectable page says the overlay is excluded from the
   screen-capture output (table: "Invisible — excluded from screen capture"), while the repo test
   says that is not a claim about SCK and the Supported Apps page says framebuffer capture captures
   everything. These are product statements at different layers, not a capability record.

### Implication for Escalier claims

Keep three claims separate: (1) **capture-dependent window hiding** (works only where the OS,
browser, or capture app honors the exclusion flag), (2) **cosmetic identity disguise** (not
process/path/signature invisibility), and (3) **HackerRank content support** (OCR/extraction, not
stealth). Do not collapse them into "undetected on HackerRank". That phrase would require
receiver-pixel evidence in the specific HackerRank capture mode and a statement about Proctor and
Desktop App Mode. The narrower, defensible wording is: "hidden from window-based capture where the
capture path honors the exclusion flag; disguised where not; no demonstrated capability under
locked-down proctoring; any product-scope decision remains open." The proposed synthetic matrix is
the evidence gate for the first clause.

## Unresolved evidence / limitations

- Which HackerRank experience/mode the reference invitation uses is unknown and was not accessed.
  The browser matrix (Firefox: Legacy supported, New unsupported; Chrome/Edge: both supported) is a
  compatibility fact, not proof of legacy or modern capture. The reference scenario is an interview;
  Proctor/Desktop App Mode are assessment/test controls, so their applicability to that interview is
  not established. Observation Mode is explicitly legacy. Interview Integrity Signals is filed under
  `Interview (Legacy)` but its article body does not state an experience qualifier, so its scope is
  not settled. Both are closer public channels than the test controls, but the configured/New
  experience may differ.
- Natively website/docs are unversioned and may describe a released build rather than main. Claims
  were tied to pinned README/source where possible; docs quotes are dated by fetch, not by release.
- The code search ran on a default branch ahead of the inspected pin; the relevant files were
  re-fetched at the pin, but this is not an exhaustive binary/historical/private audit.
- No runtime test was performed: no GUI, capture, permission prompt, microphone, call, or model
  inference. Process-name behavior in main, focus effects of the nonactivating panel, and actual
  receiver pixels remain unmeasured.
- HackerRank Proctor/Desktop App behavior is documented by HackerRank, not independently tested
  here. The exact capture backend used by HackerRank, browser version, and enterprise policy can
  change the result.
- The trace deliberately does not provide a method to defeat undisclosed or server-side signals.
  The proposed matrix measures local visibility and focus only.

## Sources

Compact evidence index: [SOURCES.md](SOURCES.md) (public URL/pin/line/fragment plus the exact code
search and hit paths; raw snapshots stay in ignored `.cache/`).

Pinned Natively sources (fetched 2026-10-26):

- Main README: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/README.md>
- Released README: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b439c1f07f6d2d77cbca64fc0533765bd19fe7f7/README.md>
- Main `scripts/disguise-name.cjs`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/scripts/disguise-name.cjs>
- `v2.9.2` `scripts/disguise-name.cjs`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b439c1f07f6d2d77cbca64fc0533765bd19fe7f7/scripts/disguise-name.cjs>
- Main build identity: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/package.json#L141-L144>
- `v2.9.2` macOS build identity: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b439c1f07f6d2d77cbca64fc0533765bd19fe7f7/package.json#L140-L143>
- `v2.9.2` Windows executable identity: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b439c1f07f6d2d77cbca64fc0533765bd19fe7f7/package.json#L260>
- Main `native-module/src/stealth_window.rs`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/native-module/src/stealth_window.rs#L160-L186>
- Main `native-module/src/capture_exclusion.rs`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/native-module/src/capture_exclusion.rs#L1-L23>
- Main `electron/WindowHelper.ts`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/WindowHelper.ts#L889-L914>
- Main `electron/utils/stealthProtection.ts`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/utils/stealthProtection.ts#L1-L30>
- Main `electron/utils/macDockPolicy.ts`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/utils/macDockPolicy.ts#L1-L32>
- Main `electron/main.ts` (network block): <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/main.ts#L9428-L9494>
- Main content-protection test: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/audio/__tests__/OverlayContentProtectionFollowsUndetectable.test.mjs>
- Main HackerRank registry/entry: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/natively-browser/src/capture/registry/registry.default.json#L140>
- Main companion manifest: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/natively-browser/src/manifest.json#L10-L25>
- Main HackerRank tab classifier: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/natively-browser/src/capture/classifier/tab-classifier.ts#L49>
- Main `electron/services/screen/BrowserPageCrop.ts`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/services/screen/BrowserPageCrop.ts#L1-L15>
- Main `electron/llm/AnswerValidator.ts`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/llm/AnswerValidator.ts#L776-L804>
- Main `electron/utils/windowTitleGuard.ts`: <https://github.com/Natively-AI-assistant/natively-cluely-ai-assistant/blob/b9287ec2f24bf0ea5250625286f97248052055e9/electron/utils/windowTitleGuard.ts#L1-L6>

Natively public docs/blog (accessed 2026-10-26):

- "Undetectable Interview AI" — <https://heynatively.com/undetectable-interview-ai>
- "Supported Apps" — <https://heynatively.com/supportedapps>
- "Frequently asked questions" — <https://heynatively.com/docs/faq>
- "Is an AI Interview Assistant Detectable?" (published 2026-03-04; modified 2026-10-22) —
  <https://heynatively.com/blog/is-ai-interview-assistant-detectable>
- "Live Interview Assistant" — <https://heynatively.com/live-interview-assistant>

HackerRank public documentation (accessed 2026-10-26):

- Browser recommendations — <https://candidatesupport.hackerrank.com/articles/8455316478-browser-recommendations-for-hackerrank-interviews>
- Interview integrity signals — <https://support.hackerrank.com/articles/5161582600-interview-integrity-signals>
- Observation Mode — <https://support.hackerrank.com/articles/1263202297-observation-mode-in-interviews>
- Proctor Mode — <https://support.hackerrank.com/articles/5663779659-proctor-mode>
- Desktop App Mode — <https://support.hackerrank.com/articles/5973590014-hackerrank-desktop-app-mode>

Related local work:

- Prior inventory and platform context: [existing research §5](../../docs/analysis/2026-10-26-live-asr-and-browser-privacy.md#5-natively-stealth-parity-inventory)
- Synthetic capture/focus plan (proposed execution): [Spike 004 PLAN](../004-window-capture-focus/PLAN.md)
