# Spike 005 — global shortcut consumption and synthetic stealth typing

Owner explicitly requested on 2026-10-26: add global keyboard capture tests so selected shortcuts and deliberate stealth typing do not bubble into the browser interview. This authorizes a separate opt-in synthetic fixture, superseding the earlier blanket exclusion of global hooks for future work. Spike 003 itself remains a hook-free shell prototype; this spike tests the integration boundary. No real HackerRank session or other assessment is accessed.

## Question and evidence

Can a permitted macOS event interception path consume selected global shortcuts and, in an explicitly armed text mode, route a known synthetic string to an Escalier-owned in-memory text field while an inert local browser page stays focused and receives none of the consumed keyboard/input events?

Official API research: Apple's [Monitoring Events](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/EventOverview/MonitoringEvents/MonitoringEvents.html) says NSEvent global monitors cannot modify/prevent delivery. [CGEvent.tapCreate](https://developer.apple.com/documentation/coregraphics/cgevent/tapcreate(tap:place:options:eventsofinterest:callback:userinfo:)) provides an event-tap callback where returning nil can suppress an event. A passive monitor or listen-only tap is not an implementation of consumption. Exact permission/secure-input/system-reserved limitations must be documented, not assumed solved.

## Non-negotiable safety and scope

- Capture OFF at startup; never request permission, install/enable an event tap or launch a GUI from tests/build/import. Implementation/build/headless tests are authorized now. Live hook installation, exact target/chords, synthetic test text and permission grants require live human approval immediately before runtime.
- Runtime scope: dedicated synthetic browser fixture, preferably a throwaway browser process/profile with an explicit allowed foreground PID. No background capture outside that PID, no real interview page, private text or password/secure-input testing. Do not use the user's general browsing session as a global keylogging target.
- Visible control window/status, explicit arm/disarm, short default maximum session (30 seconds), emergency stop (Escape), foreground-application focus/PID-change disarm, tap-disable/timeout disarm and clean removal on close/error. Do not auto-reenable a disabled tap. No launch agent, persistence or autostart. Same-PID page/field focus loss is a separate manual INVALID/Stop condition, not implemented native automatic disarm; see the binding focus-scope clarification.
- Discard non-target/non-armed events immediately without copying/logging text. Armed fixture text lives in a bounded in-memory buffer and clears on stop/close. Retained reports contain known synthetic string/outcome and event counters only, no raw unrelated keys, timestamps revealing unrelated activity, or private data. No network/upload/LLM/microphone or host install.
- No automatic permission grants or security bypass. Document Accessibility/Input Monitoring requirements from official docs, readback only without prompts until explicit approval. Secure input, unavailable taps, system-reserved shortcuts, keyboard layouts, dead keys, IME/composition and OS interception are unsupported/limited unless tested. No universal no-leak claim.

## File ownership / architecture

Worker owns all implementation/build/resources/tests/README/FINDINGS and implementation report within this directory, including Package.swift/Info.plist if needed. Coordinator owns PLAN and independent review/progress. No cross-editing 003/004 or root files; link them instead. No commits or subagents. Build outputs stay ignored .build/.tools, no third-party dependencies or system installs. Author files with write/edit tools.

Keep a pure routing/state machine separate from the narrow native event-tap adapter and SwiftUI/AppKit fixture. Browser oracle is an inert local page with independent counters/logs for keydown, keyup, beforeinput, input, focus/blur/visibility and an editable test field. A local-only server is manual; no server/browser autostart, external assets/signaling/requests or event injection. The browser page must not call preventDefault for the test chords/text, otherwise zero delivery is a false pass.

## RED → GREEN test and implementation sequence

1. Tests first for OFF pass-through/no text retention; exact key+modifier matching; unrelated keys preserved; armed text capture gated by allowed foreground PID; repeated keydowns/autorepeat; consumed keyDown/keyUp pairing; mode transition while keys held; focus loss, timeout, tap-disabled/user stop, errors and cleanup. Full modifier-only flags must be explicitly classified, not silently called invisible. Emergency Escape stops mode and records whether it is consumed; pre-register that behavior.
2. Test no orphan keyup leakage for consumed keydowns across disarm transitions, while unrelated keyups pass through. No indefinite key suppression after a mode change. Define drain/lifecycle behavior and its timeout. No event injection or replay of consumed text.
3. Test Unicode synthetic input, delete/backspace/return/tab/arrow policy and buffer limits. Do not infer IME/dead-key correctness from CGEvent Unicode extraction; explicitly mark unimplemented cases. Route reserved shortcut actions separately from text capture so shortcut text is not inserted.
4. Implement minimal native active-intercept adapter with callback work bounded/nonblocking; UI updates scheduled safely outside callback. Verify control flow can return nil for consumed events and original event for pass-through (not a listen-only monitor). Use public APIs and documented struct/pointer lifetimes. Test adapters via injected protocol rather than install a live hook in automation.
5. Build dependency-free native fixture and run headless state/adapter/static tests. Static audit ensures no permission prompt/autostart, no global raw-key disk logging/upload, bounded lifetime and browser page does not swallow the events being measured. Tamper-test guard assertions where added. Record exact commands and outputs.
6. Retain findings/manual matrix: passthrough baseline; selected shortcut down+up absent browser but one Escalier action; unrelated shortcut/text still reaches page; armed synthetic typing reaches only Escalier buffer; focus stays in page; stop/timeout/focus change restores normal delivery; unavailable/disabled tap clearly reported. Actual runtime cases are NOT RUN until interactive approval and recipient evidence.

## Runtime acceptance template (later)

Record OS/build, fixture source/binary hashes, browser/build/profile isolation, exact allowed PID/window/page, permissions before/after, selected shortcut mapping, mode/timeout, synthetic test string, Escalier action/text count, recipient keydown/keyup/beforeinput/input deltas, focus/visibility deltas, and cleanup/normal-input restoration. Pair every no-event case with a positive passthrough control. Modifier events/OS-reserved behavior are separate observations. Never claim lack of undisclosed HackerRank server-side signals from this local test.

Independent spec + quality review is required before runtime or publication. UI prototype and hook fixture results do not automatically validate each other; integration later needs explicit mapping and the same recipient no-bubble oracle.
