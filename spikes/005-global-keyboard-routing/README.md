# Spike 005 — global shortcut consumption and synthetic text routing

Status: **opt-in headless/build/static slice implemented; round 1 + round 2 review fixes applied;
dependency-free build and headless tests pass; no live tap, permission grant, GUI launch,
browser/server launch or synthetic runtime typing was performed. All interactive rows are NOT RUN.**

Date: 2026-10-26. This is a retained synthetic feasibility fixture, not a production feature, not a
product validation and not evidence of HackerRank server-side invisibility. Runtime no-bubble
behavior is **not established** by anything in this directory.

Scope and ownership: [PLAN.md](PLAN.md), binding adjudications in
[review/preflight-resolutions.md](review/preflight-resolutions.md), original adversarial report in
[review/preflight.md](review/preflight.md). Implementation evidence:
[review/implementation-report.md](review/implementation-report.md); claim ledger:
[FINDINGS.md](FINDINGS.md).

## Supersession boundary — spike 003 still stands

Spike 003's no-global-hook shell boundary remains in force for 003. **005 is the single explicit
opt-in exception**: fixture-specific, runtime-gated, and it does not validate 003's shell or any
product UI. The coordinator integrates the root/003 cross-reference after the existing owners
finish; this spike does not edit 003 or root files. 005 results do not transfer to 003.

## Question

Can a permitted macOS event interception path consume selected global shortcuts and, in an
explicitly armed text mode, route a known synthetic string to an Escalier-owned in-memory buffer
while an inert local browser page stays focused and receives none of the consumed keyboard/input
events?

Only the headless decision/build/static slice is answered here. Native suppression, browser
non-delivery and focus preservation require the interactive matrix below.

## What is implemented

- **Pure core** (`Sources/RoutingCore`): no AppKit, CoreGraphics, I/O, logging, timers or event
  creation. It owns phase transitions, exact chord matching, physical-key ownership, bounded
  draining, text/action policy, counters and invalidation.
- **Testable adapter seam** (`Sources/RoutingAdapter`): production callback/delivery coordinator,
  idempotent teardown sequencing, and close-path termination gate. It has no AppKit/CoreGraphics;
  headless tests exercise the same production wiring through injected dependencies and a fake
  lifecycle target (consume→nil, pass→original, budget→teardown, disabled→no re-enable,
  teardown idempotence, settling-failure cleanup, close/drain termination).
- **Narrow native adapter** (`Sources/RoutingFixture/TapAdapter.swift`): one dedicated thread and
  run loop, one active session-level event tap created only after an explicit arm call, fixed
  event mask, disabled-notification handling, 10 Hz coalesced UI snapshots, and the native
  enable/disable/invalidate operations driven by the tested coordinator.
- **Non-activating fixture panel** (`Sources/RoutingFixture/AppDelegate.swift`): AppKit
  `NSPanel` with `.nonactivatingPanel`, `becomesKeyOnlyIfNeeded`, floating/accessory behavior.
  Target PID and mode are configured while OFF. No activation call, no prompt, no autostart.
- **Inert browser oracle** (`web/`): visible editable field, fixed selected-key counters, separate
  modifier counters, keydown/keyup/beforeinput/input/composition/focus/blur/visibility/scroll
  counters, precondition readout, reset control, and mandatory OFF positive-control instructions.
  Listeners are capture-phase/passive and never suppress input.
- **Static audits/tools** (`tools/`): dependency-free Node audit with tamper tests and a manual
  loopback-only oracle server. The server and packaging script are never launched by tests or
  builds.
- **Resources/packaging** (`Resources/Info.plist`, `tools/package-app.sh`): bundle identity and a
  local ad-hoc signature for launchability only. Packaging does not launch, install, create or
  trust a certificate, change Gatekeeper/TCC state or grant anything.

## Fixed behavior contracts

| Area | Implemented contract |
|---|---|
| Tap | `.cgSessionEventTap` + `.headInsertEventTap` + `.defaultTap`; mask only keyDown, keyUp, flagsChanged. Disabled-by-timeout/user-input are handled as callback notification types, never as mask bits. Nil tap / failed prerequisite = UNAVAILABLE, never ARMED. |
| Foreground gate | Exact allowed PID from `NSWorkspace` frontmost application, checked before Unicode extraction and on the 10 Hz tick. Event producer/target PID fields are not used as authority. **Scope: this is foreground-application-PID only.** Page/tab/editable-field focus and visibility are separate browser/manual INVALID preconditions requiring immediate manual Stop; they are not detected by AX/DOM surveillance and do not auto-disarm the native tap. Same-PID focus loss is a residual risk recorded before runtime approval. |
| Arm | Explicit call only; requires positive allowed PID, exact foreground match, prompt-free permission readback, secure input off, no held non-modifier key, successful tap creation and a 250 ms settle. Input during settle passes without extraction. |
| Key-up authority | Ownership is a set of physical non-modifier key codes whose initial down was consumed. A matching up is consumed regardless of current modifiers or mode. No repeat count and no modifier tuple participates in up ownership. |
| Shortcut action | One action per initial physical chord down; repeats are consumed without re-firing; the eventual key-up is consumed. Reserved action matching precedes text capture. |
| Modifiers | Match command/shift/control/option plus physical key code. Caps Lock, Fn, numeric-pad, help, device-left/right and unknown bits are ignored. `flagsChanged` always passes and is counted separately. Pure-modifier shortcuts are unsupported and rejected as bindings. |
| Text policy | Printable Unicode appended only after gating. Per-event extraction cap 128 UTF-16 units, retained cap 1024, scalar-boundary truncation, overflow marked. Shifted printable allowed; unregistered command/control/option combinations, unknown controls and empty extraction pass without capture. Backspace removes one extended grapheme; forward Delete is an end-of-buffer no-op; Return/Tab consumed and not inserted; arrows/Home/End/PageUp/PageDown consumed and ignored. US layout only; IME/dead keys/composition are NOT IMPLEMENTED. |
| Drain/stop | Ordinary disarm clears text immediately, accepts no new actions/text, and drains only owned key-ups/repeats for at most 1.5 s, never past the 30 s absolute install deadline. Pending ownership at the deadline is INVALID. A removed/disabled tap does not promise to consume a future key-up. |
| Lifetime | 30 s absolute from tap installation. Stop reasons include user stop, Escape, lifetime, foreground-application-PID/permission/secure-input loss, sleep/session resign, tap disable, adapter error, close and callback-budget violation. Non-viable interruptions mark the case INVALID even without held keys; lifetime expiry with pending ownership is INVALID. No auto-re-enable. |
| Callback budget | Fixed key universe, no logging/I/O/UI mutation/per-event main dispatch; duration measured per callback with fixed counters; over 2 ms marks INVALID and disarms. This is a measured invalidation threshold, not a hard-real-time or no-allocation proof. |
| Teardown | Stop decisions → bounded drain when viable → disable tap → invalidate port → remove/invalidate source → invalidate timers → remove observers → release retained callback context → publish final snapshot → stop run loop → notify completion. One idempotent coordinator path; retained context, never a stack pointer; callback and teardown share the tap run loop. Last-window close waits for teardown completion; a 2.5 s forced termination fallback prevents an indefinite wait if teardown itself is stuck. |
| Privacy | Never extract Unicode for OFF/settling/draining/foreign-PID/modifier-only/reserved/unregistered/unrelated events. Never format or log raw events. No event injection, pasteboard, AX value writes, upload, network, LLM, microphone or persistence. |
| Control surface | Non-activating panel; Stop/Escape/timeout paths; fail-closed foreground-application-PID checks; no activation-policy change from arm and no `activate` call. Clicking the panel is expected to change focus and may disarm; Escape and the 30 s limit are the browser-focus stop paths. Page/field focus is a manual INVALID + immediate Stop condition, not an automatic read. |

## Build and test

Environment observed locally: macOS 27.x arm64, Apple Swift 6.4 (`swift-driver 1.168.6`, target
`arm64-apple-macosx27.0.0`), macOS 14 deployment target, Node v20.20.2. Build output is confined to
this directory's ignored `.build/`; no dependency, package or host installation was performed.

From this directory:

```sh
swift build
swift build -c release
swift test
node --test tools/tests/*.test.mjs
bash tools/package-app.sh
```

Observed final results (2026-10-26):

- `swift test` → **84 tests, 0 failures**, exit 0 (69 core + 15 adapter).
- `swift build -c release` → **Build complete**, exit 0.
- `node --test tools/tests/*.test.mjs` → **12 pass, 0 fail**, exit 0 (6 oracle + 6 packaging).
- `bash tools/package-app.sh` → bundle assembled, ad-hoc signed, strictly verified,
  `Signature=adhoc`, `TeamIdentifier=not set`, exit 0; **not launched**.
- `plutil -lint Resources/Info.plist` → OK; `bash -n tools/package-app.sh` → syntax OK.

RED evidence before implementation, final green evidence, exact guard-tamper outcomes and
limitations are in [review/implementation-report.md](review/implementation-report.md). Logs are under
ignored `.build/logs/`.

## Local ad-hoc packaging

`tools/package-app.sh` builds and assembles `.build/RoutingFixture.app`, lints the plist, signs the
bundle locally ad hoc, and verifies it strictly:

```sh
bash tools/package-app.sh
# ...
# .build/RoutingFixture.app: valid on disk
# .build/RoutingFixture.app: satisfies its Designated Requirement
# Identifier=local.escalier.spike005.keyboard
# Format=app bundle with Mach-O thin (arm64)
# Signature=adhoc
# TeamIdentifier=not set
# Ad-hoc signed and strictly verified ... (not launched; no TCC grant)
```

The exact signing steps are `codesign --force --sign - --timestamp=none "$APP"` followed by
`codesign --verify --strict --verbose=2 "$APP"` and a `Signature=adhoc` assertion with failure
propagation. This is **local ad-hoc signing only**, not Developer ID, not notarized, and **not a
Gatekeeper trust guarantee**. The ad-hoc identity may change across rebuilds, so TCC grant reuse is
**unproven**. No certificate is generated or trusted, no Keychain trust is changed, no
Gatekeeper/TCC state is altered, no `--deep` workaround is used, and the app is not launched.

## Manual oracle server — manual only

No server is started by build, tests, import or the fixture. For the later interactive step only:

```sh
node tools/serve-local.mjs 8765
```

Then open the loopback page in the throwaway browser profile. The page makes no external request,
uses no storage and does not suppress events. Stop the server manually when done.

## Interactive runtime matrix — ALL ROWS NOT RUN

These require separate live human approval immediately before the run, including the exact target
PID/window/page, exact chord and known synthetic text, and any TCC grant. The implementation worker
did not perform any row.

Record OS/build, fixture source and binary fingerprints, browser/build/profile isolation, exact
allowed foreground PID/window/page, TCC code/responsible-process identity and System Settings
entry/pane, permissions before/after, secure-input before/after, chord/text registration, selected
key and input counters, modifier baseline separately, action/text outcomes, elapsed and over-budget
counters, drain outcome, cleanup and normal-input recovery.

| # | Case | Status |
|---|---|---|
| R1 | Launch the ad-hoc-signed packaged fixture; capture visibly OFF; no tap created; preflight reads permission/secure-input state without a prompt. | **NOT RUN** |
| R2 | OFF positive control in the isolated browser profile: same `cmd+shift+K` chord, same page/profile, focused visible field → selected K keydown/up non-zero; known synthetic text → beforeinput/input non-zero. Zero or failed field-focus/visibility precondition means INVALID. | **NOT RUN** |
| R3 | Arm shortcut mode to the exact browser PID; settle; send `cmd+shift+K` → Escalier action count 1, elapsed within limit; browser selected K keydown/up zero; modifiers recorded separately; focus/visibility unchanged. Same-PID page/field focus loss is manual INVALID + immediate Stop, not native automatic disarm. | **NOT RUN** |
| R4 | Armed text mode; send known synthetic text → exact bounded Escalier buffer; browser selected-key/input counters zero; field stays focused; no scroll/focus change. Same-PID residual recorded. | **NOT RUN** |
| R5 | Armed control keys: Return, Tab, Backspace, forward Delete and navigation → consumed per policy; no insertion/focus/scroll change. | **NOT RUN** |
| R6 | Unrelated key and text still reach the page while armed within the allowed PID. | **NOT RUN** |
| R7 | Escape while armed → consumed emergency stop, text cleared, owned key-ups drained within 1.5 s; post-disarm ordinary recovery key (not Escape) reaches the page. | **NOT RUN** |
| R8 | Stop button, foreground-app PID change, permission loss, secure input, tap disable, sleep/session resign, last-window close and 30 s timeout → fail open, bounded teardown/termination wait, case INVALID where required, no auto re-enable. Browser page/field focus loss at the same PID is separately manual INVALID + immediate Stop. | **NOT RUN** |
| R9 | Cleanup: tap/source/timers removed, process exits without a launch agent, normal keyboard delivery restored, permissions/secure-input after-state recorded. | **NOT RUN** |
| R10 | `CGEvent.tapIsEnabled == true`, non-nil tap, maximum callback duration and over-budget counters. | **NOT RUN** |

Every no-delivery case requires the OFF positive control with the same chord, profile and focused
field. Browser/OS-reserved chords without a delivery control are unproven. No local result
establishes HackerRank server-side invisibility.

## Limitations

- No live tap, permission grant, GUI run, browser run, synthetic typing or recipient evidence was
  performed; native suppression and browser non-delivery are **NOT ESTABLISHED**.
- Headless tests prove decisions and adapter wiring only. A listen-only tap would ignore the return
  value; static guards assert the active option, but runtime capability remains a manual row.
- The fixture is US-layout simple Unicode only. IME, dead keys, composition correctness, non-US
  layouts and large native compositions are NOT IMPLEMENTED/NOT PROVEN.
- Modifier events are expected to be delivered to the page even when the non-modifier chord key is
  consumed; that is a baseline, not a leak.
- Chrome/browser accelerators and WindowServer-reserved chords may never reach the renderer; they
  are unproven without a per-chord OFF control.
- Secure input or permission changes may make keystrokes invisible to the tap; the case is INVALID,
  not PASS.
- Packaging uses a local ad-hoc signature for launchability only. It is not Developer ID, not
  notarized and gives no Gatekeeper trust guarantee. The ad-hoc identity can change across rebuilds,
  so TCC attribution/grant reuse is unproven; an unbundled `swift run` binary may instead be
  attributed to the terminal/responsible process. Packaged launch and TCC behavior are NOT TESTED.
- The adapter extracts at most 128 UTF-16 units natively. Core truncation is proven with an injected
  supplier producing more than the limit; a native string longer than 128 units is clipped by the
  native call without an additional native-truncation flag. The synthetic one-key fixture does not
  exercise that case.
- Callback duration includes prompt-free gate reads; the 2 ms threshold is an invalidation rule, not
  an OS real-time guarantee.
- A non-activating panel is configured and statically audited, but focus non-theft is NOT RUN.
- Native focus authority is foreground-application PID only. If focus moves to another window, tab
  or field **inside the same allowed browser process**, the PID does not change and the tap remains
  armed until manual Stop or the 30 s timeout. That is a manual INVALID + immediate Stop condition,
  not an automatic AX/DOM field-focus disarm. No new permissions or surveillance were added; the
  same-PID residual must be recorded before runtime approval.
- Closing the last window requests Stop and delays termination until the bounded drain and owned
  teardown complete; a 2.5 s forced termination fallback exists only to prevent an indefinite wait
  if teardown is stuck. The normal close/termination path is designed but NOT RUN; a forced fallback
  cannot claim clean teardown.
- The browser page is inert and local; it does not test server-side analytics, proctoring, or any
  HackerRank signal.

## Files

- `Package.swift` — dependency-free Swift package.
- `Sources/RoutingCore/` — pure model, key policy, bounded text buffer, routing engine.
- `Sources/RoutingAdapter/` — production callback/delivery coordinator, teardown sequencing and
  termination gate, testable without creating a tap.
- `Sources/RoutingFixture/` — native adapter, prompt-free checks, non-activating panel, entry point.
- `Tests/RoutingCoreTests/` — 69 headless tests plus source/browser static guards.
- `Tests/RoutingAdapterTests/` — 15 headless adapter/close-path behavior tests through the fake
  seam, including settling-failure cleanup regressions.
- `web/` + `tools/oracle-audit.mjs` — inert recipient oracle and its audit.
- `tools/serve-local.mjs`, `tools/package-app.sh` — manual-only server and ad-hoc packaging script.
- `tools/packaging-audit.mjs`, `tools/tests/packaging-static.test.mjs` — packaging/signature guard
  and tamper tests.
- `Resources/Info.plist` — packaged bundle identity.
- `review/` — preflight brief/report, implementation report.
