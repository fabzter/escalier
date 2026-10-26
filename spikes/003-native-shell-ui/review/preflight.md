# Contrarian preflight — native shell and capture/focus spikes

Date: 2026-10-26. Reviewer: adversarial preflight (read-only; no implementation).
Scope: `spikes/003-native-shell-ui/PLAN.md`, `spikes/004-window-capture-focus/PLAN.md`,
`docs/requirements.md`, `docs/decisions/0001-native-macos-and-omp-rpc.md`, and the
scoped research in `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md`.
This review does not redo or reopen the ASR preflight/findings.

## Verdict

**GO for the currently authorized headless/compile/static slice; CONDITIONAL GO for
interactive GUI/capture evidence.**

There is no architectural dead end. The native toolchain exists on this machine, both
spikes are synthetic and public-API-only as scoped, and keeping 003/004 independent is
sound. The plans deliberately gate GUI/capture/manual-permission work, so the fixture
and presentation code can proceed now. Remaining conditions are:

- N-01 is an ownership clarification, not an architecture blocker; without it the first
  build step is ambiguous.
- 004's oracle and marker composition (N-02–N-05) must be fixed before any runtime
  receiver-pixel/focus claim is accepted; they do not block building the fixture or its
  static/headless tests.
- 003's FR-05 stability test is one-sided and several bounded-outcome deliverables have
  no test (N-06–N-09); fix those before RED tests are written.

Fix N-01 and the 003 test/safety items before dispatch. Treat 004's runtime-oracle
findings as acceptance gates for the later interactive evidence step, not as blockers
for the current headless/compile/static implementation. No finding changes the shell
choice, the parallel split, or the approved scope.

| Plan | Disposition |
|---|---|
| 003 native shell/UI | **GO for headless/compile/static implementation after N-01 plus the N-06–N-09 plan amendments.** The synthetic/scope boundary is sound; no production, latency, stealth or OMP-policy claim follows. |
| 004 capture/focus | **GO for headless/static/compile implementation after N-01 clarification.** N-02–N-05 and N-11–N-14 are required before interactive runtime evidence, not before fixture code; runtime stealth remains NOT RUN/NOT ESTABLISHED. |

## Evidence checked

| Check | Result |
|---|---|
| Local build toolchain | Xcode at `/Applications/Xcode.app/Contents/Developer`; Swift 6.4 (`swift-driver 1.168.6`); macOS 27.0 SDK. Python 3.13.0, Node 20.20.2, Chrome 156.0.8078.48, Firefox 158.0.1 are also present. Build feasibility is not the blocker; ownership/contract is. |
| Ignore rules | Root `.gitignore` already ignores `.cache/`, `.tools/`, `.build/`, `build/`, and `*.app/`; build outputs can stay project-local. |
| Apple API semantics | `NSWindow.SharingType.none` is documented as "a legacy constant that macOS no longer uses"; the docs say not to use it to hide/omit content. `.readOnly` means contents can be read but not modified. `.accessory` corresponds to `LSUIElement = 1` in the bundle's `Info.plist`. |
| Browser API semantics | `getDisplayMedia()` requires a secure context and transient activation; user permission cannot be persisted. `RTCPeerConnection.ontrack` is the receiver-side track event; a direct `srcObject` assignment of the capture `MediaStream` is local preview, not transport evidence. |
| Plan/requirement trace | 003 covers parts of FR-02/05/06/07/11/15/16; 004 covers a bounded subset of NFR-05/06. Neither claims runtime stealth or full NFR-06 coverage. Firefox remains conditional. |
| Runtime tests | None run in this preflight: no GUI launch, capture, permission prompt, model inference, real interview, or private-file access. No ASR work was repeated. |

## Findings

### N-01 — Build/test manifest and bundle files are outside worker ownership (Critical)

- **Location:** 003 PLAN:13 (File ownership); 004 PLAN:18; both bounded outcomes and
  sequences.
- **Issue:** Both spikes promise a native build and headless tests, but the owned paths
  are only `README.md`, `Sources/**`, `Tests/**`, `tools/**`, and the implementation
  report. `Sources/**` plus `Tests/**` do not define a SwiftPM package; `swift test`
  cannot run without a `Package.swift` at the package root. A custom `swiftc` harness is
  possible, but neither the command nor test discovery is specified. 004's
  accessory/Dock/identity cells may also need an `Info.plist` or `.app` bundle, which no
  one owns. A strict worker cannot tell whether it may create them: a manifest at the
  package root is outside ownership, and the plan does not specify a `tools/`-nested
  package or a custom runner.
- **Suggested fix:** Add `Package.swift` (and any `Resources/**`, `Info.plist`, or
  `tools/build-app.sh`) to each worker's owned paths, choose SwiftPM or a `tools/`-owned
  `swiftc` runner, and record exact build/test commands and artifact paths. If 004 is
  not packaged, mark packaged-app/Dock/identity behavior NOT TESTED. Keep `.build/`
  ignored.

### N-02 — Receiver evidence is not transport-bound (High)

- **Location:** 004 PLAN:12, 14, 26, 30; sequence steps 2 and 4.
- **Issue:** The plan correctly says "a sender preview alone is not receiver evidence,"
  but it does not require a receiver transport. A second `<video>` whose `srcObject` is
  set to the `getDisplayMedia` `MediaStream` is a local preview; a `MediaStream` cannot
  be cloned through `BroadcastChannel`. "In-memory channel where possible" is therefore
  ambiguous, and the findings template has no receiver `getStats` or frame fields. An
  implementation could satisfy the prose and still produce no receiver evidence.
- **Suggested fix:** Require sender `getDisplayMedia` → `RTCPeerConnection.addTrack`;
  receiver `<video>` fed only by `pc.ontrack`; record inbound-rtp `framesDecoded` /
  `bytesReceived`, video dimensions and frame timestamps; sample marker pixels from the
  receiver video via canvas. Keep the sender preview in a separate element. Fail the
  cell if receiver stats are absent. No external signaling or STUN/TURN servers.

### N-03 — Marker/control composition cannot separate exclusion from source absence (High)

- **Location:** 004 PLAN:9–10, 26; analysis §4 (single selected window vs entire display).
- **Issue:** The "protected" marker window and "unprotected" control marker are separate
  AppKit windows. If the browser captures a single window (the browser or the fixture),
  neither marker is in the source; observing both absent is not evidence of a sharing
  flag. A single selected browser window cannot be assumed to include a separate AppKit
  marker window; only entire-display capture (or an explicitly verified child-window
  composition) can test a cross-window overlay, and only if the markers are frontmost
  and onscreen. The plan does not define the selected source per cell, matching
  geometry, z-order, occlusion, or a per-cell positive control. The control can be
  absent for reasons unrelated to `sharingType`.
- **Suggested fix:** Pre-register a matrix with two otherwise-identical marker windows
  differing only in `sharingType` (same size, level, alpha and window style), placed so
  both are unoccluded in the same capture frame, with the control positively observed in
  the treatment cell. Record bounds/level/onscreen/z-order. Mark single-window cells N/A
  for cross-window exclusion, not "protected." Add known-positive and known-negative
  controls (marker inside vs outside the selected source).

### N-04 — Behavioral oracles missing for nonactivation, click-through and accessory policy (High)

- **Location:** 004 PLAN:9–10, 26; sequence step 5.
- **Issue:** `ignoresMouseEvents`, `styleMask.contains(.nonactivatingPanel)`, and
  `NSApp.activationPolicy()` are local/requested state. They do not prove clicks reach
  the underlying browser, that the browser keeps page focus, or that a normal panel
  steals focus. The plan does not fix the foreground/activation state, so "normal vs
  nonactivating" cells may not be comparable. A page focus/blur log is page-observable
  only; it is not OS-level focus or a HackerRank signal.
- **Suggested fix:** Define a fixed sequence and record pre/post `NSApp.isActive`,
  frontmost bundle ID, `NSApp.keyWindow`/`mainWindow`, panel `isKeyWindow`, `styleMask`,
  `level`, `collectionBehavior`, `hidesOnDeactivate`, `becomesKeyOnlyIfNeeded`, and
  `isFloatingPanel`. For click-through, use an inert browser button under the panel and
  record click counts with `ignoresMouseEvents` true vs false. Log page `window.focus` /
  `blur`, `document.visibilityState`, and `document.hasFocus()` with timestamps, and
  label them page-observable.

### N-05 — Full-display/audio/TCC safety protocol is incomplete (High)

- **Location:** 004 PLAN:12–14, 26, 30.
- **Issue:** Entire-display capture records every visible window, notification and
  private screen content, not just the fixture. The plan bans private files but not
  private screen content; it has no clean-desktop rule, no frame-minimization/export
  rule, and no audio constraint. `getDisplayMedia` can request audio; screen-recording
  TCC is a persistent grant. "The user grants" is stated, but the exact human-only
  protocol and evidence-retention boundary are not.
- **Suggested fix:** Require video-only (`audio: false`, assert zero audio tracks), a
  dedicated clean Space/display containing only the fixture and browser, notifications
  off, no full-frame recording or persistence, and marker-ROI sampling only. Keep a
  visible, always-reachable control window to close panels. Record TCC state before and
  after; the human selects the source and grants permission; the agent must never
  automate the native picker or a TCC dialog. Document the persistent grant and
  revocation.

### N-06 — Global shortcuts/event taps are not prohibited in 003 (High)

- **Location:** 003 PLAN:9, 18.
- **Issue:** "Shortcuts can demonstrate distinct actions" has no local-only constraint.
  A global monitor/event tap is a plausible way to build a keyboard-driven shell; it
  requires Accessibility/Input Monitoring, intercepts other applications' keys, and
  violates the synthetic/no-permissions boundary. The plan's "permissions status MOCK"
  makes an accidental real permission request especially confusing.
- **Suggested fix:** Require in-app SwiftUI keyboard shortcuts/menu key equivalents only;
  explicitly ban `NSEvent.addGlobalMonitorForEvents`, CGEvent taps, and Accessibility/
  Input Monitoring; add a source audit and a README statement. A passing action-router
  test is not shortcut validation; mark real keyboard handling NOT TESTED.

### N-07 — Stable-reference test is one-sided; explicit navigation is untested (High)

- **Location:** 003 PLAN:18; FR-05.
- **Issue:** "Stable selected reference when another candidate arrives" passes if
  selection never changes. It does not test explicit next/previous navigation, a visible
  new-candidate indicator, selected-candidate removal, or that candidate arrival does not
  steal scroll/reading position. A frozen panel satisfies the test but fails FR-05
  contextual navigation.
- **Suggested fix:** Add paired tests: (a) arrival preserves the selected stable
  ID/range; (b) explicit navigation changes selection and clears the new indicator;
  (c) selected-candidate removal yields an explicit unresolved state, with no silent
  jump; (d) candidate count/list is visible. If scroll stability is claimed, test a pure
  scroll-anchor state or label it NOT TESTED.

### N-08 — Bounded-outcome claims without tests: action routing, phase, image, mock status (High)

- **Location:** 003 PLAN:7, 18; FR-06/07/10.
- **Issue:** "Distinct action routing" does not enumerate the FR-07 actions or assert
  unique/non-empty handlers; "preparation/conversation navigation" has no phase-
  transition test; the "complete local image/diagram placeholder" has no image/
  provenance test; and the central "MOCK/NOT CONNECTED" labels are not asserted. A
  green suite could omit deliverables while passing the listed tests.
- **Suggested fix:** Define the exact five actions (or explicitly mark omitted ones not
  covered) and test unique route/handler IDs. Test an explicit preparation→live
  transition and per-phase content. Test that the image item is non-streaming,
  local/synthetic, and has a text alternative. Put model/tool/skill/input/permissions/
  OMP statuses in pure enums and test that every surface renders MOCK or NOT CONNECTED.
  Mark visual/keyboard/focus behavior NOT TESTED.

### N-09 — Retained-result and per-conversation state are underdefined (Medium)

- **Location:** 003 PLAN:7, 18; FR-15/Q-07.
- **Issue:** "Retained-result selection/delete isolation" does not define what a result
  contains (transcript, retrieval/search log, assistance) or whether deletion removes
  all copies; it can pass by deleting one array row. Separately, per-conversation
  model/tool/skill selections, reference state, streaming history and retained results
  could be independent demo widgets with no switching test. This is also where the
  prototype risks scope creep: FR-15's real persistence/deletion boundaries are
  explicitly unresolved.
- **Suggested fix:** Define a minimal `ConversationState` aggregate and a retained-result
  aggregate; test that switching conversations isolates selections, reference state,
  streaming history and retained results; test that delete removes only the selected
  aggregate and leaves sibling conversations/source excerpts intact. Show "synthetic —
  no disk data" and do not persist. If scope is tight, defer retained-result/delete with
  an explicit NOT IMPLEMENTED rather than demoing destructive semantics.

### N-10 — `.none` is a legacy flag, not a protection guarantee; naming/claim (Medium)

- **Location:** 004 PLAN:9–10, 26, 30; Apple `NSWindow.SharingType` docs.
- **Issue:** Apple's current docs call `.none` "a legacy constant that macOS no longer
  uses" and explicitly say not to use it to hide or omit content; `.readOnly` means
  contents can be read but not modified, so it is a positive control, not a privacy
  setting. The plan's "protected-marker panel" and "protected/control" findings labels
  presuppose the treatment works. The plan's "do not infer remote pixels from a flag"
  rule is correct but undermined by the naming.
- **Suggested fix:** Rename to `sharing-none` / `sharing-readOnly`; pre-register expected
  observations; claim only "observed/not observed in receiver frames under this cell";
  cite the Apple caveat; do not use "protected" in result labels unless the receiver
  evidence supports it.

### N-11 — Lifecycle/policy transition readback is missing (Medium)

- **Location:** 004 PLAN:10, 26; analysis ST-01/ST-02.
- **Issue:** The plan reads back window policy but does not script show/hide/restore,
  activate/deactivate, accessory-policy switch, or a lazily created surface. A flag set
  at creation can reset, and a re-shown window can lose policy; a single readback would
  miss it. The reference inventory explicitly calls for reassert/readback after lifecycle
  transitions.
- **Suggested fix:** Add a scripted sequence (create → show → hide → show →
  activate/deactivate → accessory switch → re-show) with requested/observed readback
  after each; include a lazily created surface; record unknown when not observable.
  Runtime remains interactive/NOT RUN in a worker.

### N-12 — Evidence/report schema is incomplete for reproducibility (Medium)

- **Location:** 004 PLAN:26.
- **Issue:** "Exact OS/browser/source/window-policy" is a start, but the template omits
  OS build, browser build, screen-recording permission state, display ID/arrangement/
  scale, window level/`collectionBehavior`/onscreen/z-order, selected source dimensions,
  audio-track count, receiver `getStats`, marker frame timestamps, and fixture build/
  revision. Without these, results are not comparable across cells or reproducible.
- **Suggested fix:** Define the report schema before implementation; require every field
  or an explicit unknown; one row per source/surface/config; include exact commands and
  artifact paths; store only marker crops/hashes, not full frames.

### N-13 — "Representative auxiliary surface" and display-title "disguise" are underdefined (Medium)

- **Location:** 004 PLAN:9–11.
- **Issue:** "A representative auxiliary surface" has no class/level/style/size or
  rationale, so it cannot be reproduced or mapped to ST-03/ST-06/ST-07/ST-10. A generic
  `NSWindow.title` does not change bundle/process identity and may not be what a browser
  picker shows; "disguise experiment" has no defined observation surface. Accessory/Dock
  behavior may differ for an unbundled fixture vs a packaged `LSUIElement` app (see
  N-01).
- **Suggested fix:** Name one public-API surface and its exact configuration, record it
  as a separate row, and state it does not represent all auxiliary surfaces. Label the
  title test "window-title visibility only"; keep runtime identity/Dock/Cmd-Tab/process
  name NOT IMPLEMENTED or fixture-only; if accessory policy is tested, record bundle/
  `Info.plist` context and mark packaged-app validation separate. No impersonation.

### N-14 — Static/secure-context/audio checks are not in browser-fixture acceptance (Medium)

- **Location:** 004 PLAN:12, 14, 23–24.
- **Issue:** "No external servers or uploads" and "no microphone/live audio" are prose.
  A CDN, STUN/TURN URL, `getUserMedia`, or `audio: true` could slip into `web/**`; the
  runtime test only checks pixels. `getDisplayMedia` also requires a secure context and
  transient activation; `file://` or a script-triggered call fails, and the 127.0.0.1
  server is necessary but not stated as an acceptance check.
- **Suggested fix:** Add a static fixture audit that allowlists only
  `http://127.0.0.1:<port>` / `http://localhost:<port>` URLs and flags every other
  `http(s)`, `ws(s)`, `stun:`, `turn:`, `getUserMedia`, `audio: true` occurrence; at
  runtime assert
  `window.isSecureContext` and `stream.getAudioTracks().length === 0`, record
  `navigator.userActivation?.isActive` where available, and require the
  `getDisplayMedia` call to occur inside a user-gesture handler; no auto-call; document
  the start-server command and no external requests.

### N-15 — Fixture/shell claim transfer is not bounded (Low)

- **Location:** 003 PLAN:23; 004 PLAN:3, 30.
- **Issue:** 004's disposable fixture and 003's low-fidelity shell are independent.
  Neither plan requires the reports to state that 004 capture/focus results do not
  validate 003's shell, or that 003's UI has no stealth behavior. Future synthesis could
  combine them into an unsupported claim.
- **Suggested fix:** Require both READMEs/reports to carry a "fixture/prototype-specific;
  not production validation" statement; 004 records the exact fixture window
  configuration; 003 states no capture/stealth claim; if integration is later, add a
  mapping table, not shared code.

### N-16 — 004 has no independent review gate (Low)

- **Location:** 004 PLAN:28–30, contrasted with 003 PLAN:23.
- **Issue:** 003 requires an independent spec/quality review after implementation and
  explicitly distinguishes unit-tested presentation logic, compile-checked API use and
  untested UI behavior. 004's success boundary has no equivalent review gate, so a
  report could retain a receiver-pixel or focus claim that no independent reviewer
  checked against the evidence rules.
- **Suggested fix:** Adopt 003's review gate for 004: independent review of the harness,
  configuration tests, static checks, runtime matrix and claim wording; require explicit
  tested/untested labels; accept no important open defect silently.

## Pre-dispatch conditions

- [ ] **N-01 (both):** clarify `Package.swift`/resources/bundle and test-harness
  ownership in the plan or dispatch note. This is the only build-contract ambiguity.
- [ ] **N-06–N-08 (003):** add the global-shortcut prohibition and the missing
  stable-reference/navigation, action-routing, phase, image and mock-status tests before
  RED tests are written.
- [ ] **N-09 (003):** decide the `ConversationState`/retained-result contract or defer
  retained-result deletion explicitly before that test is written.
- [ ] **N-10/N-13 (004):** cheap plan/README wording: rename the `.none` treatment,
  define one auxiliary surface, and bound the display-title/accessory/Dock claims.

## Before interactive runtime (not before fixture code)

- [ ] **N-02–N-05 (004):** require a real receiver transport and objective receiver-pixel
  oracle, a marker/control composition matrix with a per-cell positive control,
  behavioral oracles for nonactivation/click-through/accessory, and the
  video-only/clean-desktop/human-permission protocol.
- [ ] **N-11/N-12/N-14 (004):** add lifecycle readback, the full report schema, and the
  static/secure-context/no-audio checks.

## At report time

- [ ] **N-15/N-16:** add the non-transferability statements and the independent review
  gate before the implementation reports are accepted.

## Minimum 004 runtime matrix (after amendments)

1. **Entire display, browser frontmost:** both otherwise-identical marker windows
   frontmost; `.readOnly` control observed, `.none` treatment measured; overlap and
   non-overlap; receiver `getStats` and frame timestamps.
2. **Selected browser window:** both markers outside the selected source; report
   N/A/control-absent, never "protected."
3. **Selected fixture window:** marker inside the source; positive control; same-window
   treatment/control if possible.
4. **Occluded/behind control:** both markers behind the browser; both absent; record
   occlusion as the reason.
5. **Focus:** browser active, normal panel vs nonactivating panel; app active/inactive
   controls; pre/post key-window and frontmost-app readback.
6. **Click-through:** inert browser button under the panel, `ignoresMouseEvents` true vs
   false; click counts, no real actions.
7. **Lifecycle:** show/hide/activate/deactivate/accessory switch; policy readback after
   each.
8. **Audio/privacy:** zero audio tracks, no external requests, secure context, no
   full-frame retention.

If timeboxed, complete rows 1, 3, 5 and 8 first and mark every unexercised cell NOT RUN;
do not present a partial matrix as full coverage.

## Already sound — do not "fix" away

- 003's synthetic-only boundary: no real files/vault/private history, OMP/LLM, audio/
  capture, networking or persistent deletion. GUI visual/keyboard/focus behavior is
  explicitly NOT TESTED; build success is not a UI pass; no Natively code or identity.
- 004's public-API-only boundary: no private APIs, TCC bypass, process-name injection,
  impersonation or permission-prompt suppression; source selection is human/manual; no
  external servers/uploads; window vs entire-display is distinguished; a sender preview
  is not treated as receiver evidence; Firefox is conditional; no real interview page.
- Independent `Sources/Tests/tools` under the two directories is intentional. No shared
  implementation is required; compare findings later, not code.
- The local toolchain and ignored build paths make both builds feasible. The blocker is
  the contract, not Xcode.
- No ASR preflight/finding is reopened by this review; 001's resolutions stand.

## Out of scope / not findings

- 004 does not test tab sharing, HackerRank server-side integrity signals, or the full
  NFR-06 matrix. Do not infer full NFR-06 coverage from this spike. A synthetic
  Chrome/Firefox capture result also does not establish HackerRank support; the public
  matrix lists Firefox as not supported for the New Interview Experience.
- 003 is not an OMP/LLM/audio/capture implementation. Mock labels are required, but no
  runtime capability follows from the prototype.
- No GUI/capture/permission test was run in this preflight. The reviewer did not launch
  either app or trigger `getDisplayMedia`.
