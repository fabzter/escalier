# Contrarian preflight — spike 005 global shortcut consumption / synthetic stealth typing

Date: 2026-10-26. Reviewer: adversarial preflight (read-only; no implementation, no GUI, no
permission request, no tap installed).
Scope: `spikes/005-global-keyboard-routing/PLAN.md` (all 38 lines), plus the API semantics needed
to judge its contract. Cross-references to `spikes/003-native-shell-ui/PLAN.md` are for the
supersession boundary only. This review does **not** re-audit ASR, Natively, or invent product or
"assistance" exclusions; it does not reopen the 003 findings.

## Verdict

**GO for the headless/build/static slice, CONDITIONAL for anything that installs a tap.**

The plan is pointed in the right direction on the two things that usually go wrong: it names the
passive-vs-active distinction explicitly (PLAN:9) and it gates arming, permissions and runtime
evidence behind live human approval (PLAN:13). There is no architectural dead end, and the
pure-state-machine + narrow-adapter split (PLAN:23, 30) is the right shape for testability.

It is **not** ready to write RED tests as specified. The suppression contract is underspecified in
ways that make a green suite compatible with a leaking or falsely-passing fixture:

- the tap location / options / `eventsOfInterest` mask are never fixed, and placement decides which
  TCC privilege is consumed and whether the disabled-tap notification is even delivered (G-01);
- key-down/key-up bookkeeping is described as tests but the *authority* for the key-up decision and
  the drain timeout are left "to be defined" (PLAN:28), which is exactly where orphan key-ups are
  born (G-02);
- modifier/`flagsChanged` semantics are asserted as "classify explicitly" without deciding the
  suppression rule, and the flag mask used for chord matching will misfire under Caps Lock and the
  device-dependent bits (G-03);
- the armed text path and the control surface are under-constrained in a way that can either inject
  system events or self-disarm the foreground-PID gate (G-04);
- the browser oracle has at least four independent false-pass mechanisms the plan does not close,
  plus one false-*fail* (browsers do deliver `keyup` for modifier keys) (G-05).

Conditions are therefore: **G-01–G-07 must be resolved in PLAN/tests before RED tests are written
or the adapter is built.** G-08–G-12 are required before the interactive runtime step. G-13–G-15 are
cheap amendments and can land with the README. No finding changes the spike's scope, the ownership
split, or the "not a HackerRank signal" boundary, and none of them requires a permission grant now.

| Slice | Disposition |
|---|---|
| Pure routing/state machine + headless tests | **GO** after G-02/G-03/G-10/G-11 are specified (they are test-contract gaps, not design risk). |
| Native active-intercept adapter source + compile/static audit | **GO** after G-01, G-04, G-06, G-07, G-09 are pinned; must compile with **no** tap created outside an explicit arm call. |
| Browser fixture + oracle page | **GO** after G-05 is closed; fixture code is safe to write now, but the pass/fail rules are not. |
| Any live tap, permission grant, synthetic typing run | **NOT RUN / NOT AUTHORIZED here.** G-08, G-12–G-14 are preconditions for that step. |

## Evidence checked

| Check | Result |
|---|---|
| Active tap return semantics | Apple `CGEvent.tapCreate(tap:place:options:eventsOfInterest:callback:userInfo:)`: the callback's return value controls delivery; returning `nil` deletes the event for an active (`kCGEventTapOptionDefault`) tap. PLAN:9 states this correctly. |
| Passive tap cannot suppress | `kCGEventTapOptionListenOnly` taps cannot modify or discard events and the callback return value is **ignored**; Apple notes listen-only is for monitoring only. This confirms the plan's "a passive monitor or listen-only tap is not an implementation of consumption" (PLAN:9) and means a listen-only tap produces a silent zero-suppression fixture, not a hard error. |
| Tap failure mode | `tapCreate` returns `nil` when the tap cannot be created, including missing permission. A missing-permission build therefore looks like "no events matched" unless the code types that as unavailable. |
| Disabled-tap signalling | The tap is disabled by timeout and by user input; the callback receives `kCGEventTapDisabledByTimeout` / `kCGEventTapDisabledByUserInput` and the tap stays disabled until re-enabled. PLAN:15's "do not auto-reenable" is the safe choice and is also the only choice consistent with PLAN:17's no-bypass boundary. |
| Privilege class depends on placement | Session-level modifying taps (`kCGSessionEventTap`) are the documented path for global hotkey suppression under Accessibility; HID-level taps (`kCGHIDEventTap`) demand broader privilege (root/Input Monitoring class) and are not needed to suppress keys for the frontmost app. The plan names neither, so the permission class it wants documented (PLAN:17) is undetermined. |
| Prompt vs readback APIs | `AXIsProcessTrusted()` and `CGPreflightListenEventAccess()` are readback; `AXIsProcessTrustedWithOptions` with the prompt option and `CGRequestListenEventAccess()` request/prompt. "Readback only without prompts until explicit approval" (PLAN:13) is only satisfiable if the implementation is pinned to the preflight/trusted-query variants — the plan does not pin them. |
| No runtime work performed | No tap created, no permission queried, no browser launched, no synthetic text typed, no files outside this report written. |

## Findings

### G-01 — Tap location, options, event mask and permission class are all unpinned (High)

- **Location:** PLAN:9, 13, 17, 30, 31.
- **Issue:** The plan fixes *that* an active tap is needed but never fixes `tap:` placement,
  `place:`, `options:` or `eventsOfInterest:`.
  (a) Placement silently picks the privilege class: `.cgSessionEventTap` + `.default` is the
  Accessibility-class path for suppressing keys destined for the frontmost app; `.cghidEventTap`
  pulls in the broader Input Monitoring/root-class privilege for no benefit at this scope, and a
  review of the plan cannot tell which one a worker will write.
  (b) If `eventsOfInterest` omits `CGEventMaskBit(.tapDisabledByTimeout)` /
  `(.tapDisabledByUserInput)`, the disarm-on-disable branch at PLAN:15 has no trigger and the
  fixture can die mid-case while the status window still says ARMED.
  (c) Per-event recipient identity is treated as available ("allowed foreground PID", PLAN:14):
  keyboard events at these tap points commonly carry no meaningful target PID, so a per-event PID
  gate can either match nothing (mode never engages) or match everything (capture beyond the
  allowed app).
  (d) `tapCreate` returning `nil` is the normal missing-permission outcome; without a typed
  unavailable state this is indistinguishable from "the chord did not fire".
- **Suggested fix:** Pin in the plan and in the adapter: `.cgSessionEventTap`,
  `.headInsertEventTap`, `options: .default`, mask = `keyDown | keyUp | flagsChanged |
  tapDisabledByTimeout | tapDisabledByUserInput`. Gate on the frontmost application recorded via
  `NSWorkspace` (a `didActivateApplicationNotification` observer that disarms on change), **not** on
  `kCGEventTargetUnixProcessID` / `kCGEventSourceUnixProcessID`. Readback with `AXIsProcessTrusted()`
  and `CGPreflightListenEventAccess()` only; the request/prompting variants are forbidden until the
  separate interactive approval. Model `nil` tap as a distinct `.unavailable(reason)` arm result and
  surface it in the control window. Add a test that a `.unavailable` arm never reports ARMED.

### G-02 — Key-up authority, drain window and arm/disarm race are undefined (High)

- **Location:** PLAN:27, 28, 30.
- **Issue:** PLAN:28 says "Define drain/lifecycle behavior and its timeout" — that definiendum is
  the whole correctness core, and it is deferred to the implementer. Three concrete holes:
  (a) **No stated authority for the key-up decision.** If the key-up is matched by re-evaluating
  "is capture armed and does this chord match", then a disarm (Escape, timeout, focus change,
  PID change) between down and up lets the up through while the down was deleted → orphan `keyup`
  in the page. The decision must come from a record written by the consumed key-down.
  (b) **Autorepeat interacts with the drain.** While a consumed key is held, the system emits
  repeat key-downs. If the drain only consumes key-ups, the page sees a stream of repeat `keydown`
  for a key it never saw pressed, then the key-up pairs with them.
  (c) **No arming settle, no revoke path.** If the tap is created at arm time (the only shape
  consistent with PLAN:13), the first keystroke after the click can race the install, and a key
  already held at arm time has no key-down in the record.
- **Suggested fix:** State the invariant in the plan: *a key-up is consumed iff and only if a
  matching key-down was consumed; arm state is never consulted for key-ups.* Concretely, a
  `SuppressedKeys` set keyed by `(keyCode, normalizedFlagMask)` with a count per key: insert on each
  consumed key-down including repeats, decrement/remove on the mid-drain key-up. Drain contract:
  after disarm, keep the tap installed and consuming only (i) key-ups for keys in the set and
  (ii) repeat key-downs for keys in the set, until the set empties or a **pre-registered bounded
  window (e.g. 1.5 s)** elapses; then invalidate the port. If the window expires with keys still in
  the set, consume the eventual up, record `drain_orphans` and mark the case **INVALID**, not PASS.
  Disarm never waits on a key. Add a monotonic post-arm settle interval (record it) before the
  measurement window, and record `keys_held_at_arm` so a held-key case is classified rather than
  silently suppressed or silently passed. Tests must cover: down/up both consumed; down consumed →
  disarm → up consumed + `drain_orphans == 0`; down passed → disarm → up passed; repeat down after
  disarm consumed while the key is in the set.

### G-03 — Modifier/`flagsChanged` rule and flag-mask normalization are missing (High)

- **Location:** PLAN:27 ("Full modifier-only flags must be explicitly classified"), 29, 30.
- **Issue:** The plan demands the classification but does not decide it, and the matcher is
  underspecified in a way that fails in ordinary use.
  (a) Modifier presses surface as `flagsChanged`; deleting that event to "consume" a chord leaves
  the recipient's modifier state latched or desynced. Suppressing `flagsChanged` is not a safe
  implementation of a shortcut.
  (b) A raw `flags` equality test misfires: `.maskAlphaShift` (Caps Lock) adds a bit that breaks
  every chord while Caps Lock is on; the device-dependent left/right bits can appear on some chords;
  `.maskSecondaryFn` and `.maskNumericPad` vary by hardware.
  (c) Pure-modifier chords (`Cmd+Shift` alone, `Fn`) are not provably suppressible and, per (a),
  must not be claimed.
- **Suggested fix:** Pre-register: `flagsChanged` is **never** suppressed; a consumable chord must
  contain at least one non-modifier key; pure-modifier chords are marked UNSUPPORTED. Match on
  `keyCode` + a normalized mask (`.maskCommand | .maskShift | .maskControl | .maskAlternate`, with
  Caps Lock, Fn, numeric-pad and the device-dependent bits explicitly masked out and said so in the
  README). Tests: Caps Lock on still matches; `Cmd+Shift` alone is UNSUPPORTED and unconsumed;
  `flagsChanged` is always passed through and counted separately. Do not infer modifier delivery from
  chord delivery — the page will still see modifier state changes for un-suppressed modifier keys,
  and that belongs in the report as an expected baseline, not a leak.

### G-04 — Armed text path and control surface can inject events or self-disarm the PID gate (High)

- **Location:** PLAN:7, 11, 13, 14, 23, 29, 30.
- **Issue:** Two distinct hazards in one contract.
  (a) "Route a known synthetic string to an Escalier-owned in-memory text field" (PLAN:7) does not
  forbid the obvious wrong implementation: posting `CGEvent`s. `CGEvent.post(tap:)`,
  `CGEventPostToPid`, `CGEvent.keyboardSetUnicodeString`, `AXUIElement` value writes and pasteboard
  round-trips would all "work" while violating PLAN:28's "no event injection" and destroying the
  meaning of the oracle (the page would be tested against the OS, not against Escalier).
  (b) The visible control window that shows status and the received-text readout must not become key
  or frontmost: with the arm gate keyed to the allowed foreground PID, focusing Escalier disarms the
  mode, so the operator cannot look at the readout while armed — or, if the gate is loose instead,
  it was never a gate.
- **Suggested fix:** State that the armed text path is a **pure in-memory buffer append** performed
  by the state machine on the tap thread's decision; the adapter is allowed to consume or pass, and
  nothing else. Add a static audit that fails on `CGEventPost`, `CGEvent.post`, `postToPid`,
  `keyboardSetUnicodeString`, `AXUIElementSetAttributeValue`, `NSPasteboard` writes, and
  `CGEventCreateKeyboardEvent` in `Sources/**`. Require the control/readout surface to be a
  non-activating panel that never becomes key (`NSPanel` with
  `.nonactivatingPanel` + `becomesKeyOnlyIfNeeded`), and add a headless test asserting the panel
  configuration is non-activating and that no arm path sets activation policy or calls `activate`.
  Note in the README that clicking the Stop button *is expected* to deactivate/disarm: the reachable
  stop paths from browser-focus are Escape and the 30 s timeout.

### G-05 — Browser oracle has four false-pass paths and one false-fail the plan does not close (High)

- **Location:** PLAN:23, 32, 34–36.
- **Issue:** "The browser page must not call `preventDefault` for the test chords/text" closes only
  one of five ways a zero-delivery result means nothing:
  (a) **Browser-level accelerators.** Chrome handles most `Cmd`+letter chords in the browser process;
  the renderer never sees them whether or not Escalier suppresses anything. A zero count is then a
  property of Chrome, not of the tap.
  (b) **Precondition-free zero.** If the page never had focus/visibility, or the fixture tab is not
  the active tab, zero counts are trivially satisfied.
  (c) **Listener shape.** Any page handler that returns early, or a `keypress`-only oracle, changes
  what "no delivery" means; counters must be registered at the window in the capture phase with
  `{capture: true, passive: true}` and the static audit must reject `preventDefault`,
  `stopPropagation`, `stopImmediatePropagation` and inline `on*` handlers in the fixture.
  (d) **Input oracle without an editable target.** `beforeinput`/`input` are only meaningful with the
  test field focused; `activeElement` drift makes the input counters meaningless.
  (e) **False fail:** browsers dispatch `keydown`/`keyup` for modifier keys derived from
  `flagsChanged`. A "the page received zero key events" criterion will fail a *correct*
  implementation for the `Cmd`/`Shift` it never suppressed, inviting a "fix" that suppresses
  `flagsChanged` (see G-03) or corrupts the pass criterion.
- **Suggested fix:** Add to the plan's oracle contract: (i) every consumed-chord case is paired with a
  **capture-OFF negative control using the same chord, same profile, same page** that must produce a
  non-zero count — no control, no case; (ii) preconditions must be asserted immediately before each
  case (`document.hasFocus()`, `document.visibilityState === 'visible'`,
  `document.activeElement === field`, expected frontmost PID) and a failed precondition is
  **INVALID**, never PASS; (iii) pass criterion is scoped to the chord's non-modifier key
  (`keydown`/`keyup` for that keyCode == 0) with modifier `keydown`/`keyup`/`flagsChanged`-derived
  counts recorded as an expected baseline, not as failure; (iv) counters for
  `keydown/keyup/beforeinput/input/compositionstart/focus/blur/visibilitychange` plus the test
  field's `value` length; (v) the post-disarm recovery control must not reuse `Escape` if the case
  pre-registers Escape as consumed.

### G-06 — Callback budget, tap death and UI coupling are asserted but not bounded (High)

- **Location:** PLAN:15, 30, 31.
- **Issue:** "callback work bounded/nonblocking; UI updates scheduled safely outside callback" has no
  invariant and no failure handling. A session-level tap sits in the input path for the whole
  session: a slow callback stalls input for every app, and the system disables the tap. Per-event
  `DispatchQueue.main.async` grows a queue without bound if the main thread is busy (which the
  SwiftUI re-render itself can cause), which both burns the budget and produces a fresh
  disabled-by-timeout. Because PLAN:15 forbids auto-re-enable, the result is a dead tap with an
  ARMED-looking status window and a case that silently measures nothing.
- **Suggested fix:** Make it an invariant: the tap callback does O(1) work, no allocation, no
  logging, no locks (atomics only), and never calls into AppKit/SwiftUI. Counters are plain
  preallocated integers; the UI samples them on a coalesced timer (≤10 Hz). On either disabled
  event: disarm, record `tap_disabled(reason)`, mark the case INVALID, and do not re-enable (per
  PLAN:15). Add a headless test that the "disabled" branch disarms and cannot return to ARMED
  without a fresh arm call, and a static guard that the hot path contains no `print`/`os_log`/
  `DispatchQueue.main.async`.

### G-07 — Privacy rule is about retention, not about touching key content (High)

- **Location:** PLAN:16, 31.
- **Issue:** "Discard non-target/non-armed events immediately without copying/logging text" is
  correct but not enforceable as written. Two ordinary Swift lines defeat it: reading the unicode
  string for any event (`CGEvent.keyboardGetUnicodeString`, `NSEvent.characters`) and logging the
  event object (`String(describing: event)`, `print(event)`, `CFShow`) — Core Graphics' event
  description renders the unicode payload. A debug-level log left on during a run is a raw
  global-key log on disk, which is exactly what the plan says it will not produce.
- **Suggested fix:** Constrain the hot path to `keyCode`, `flags`, the autorepeat field and a
  monotonic timestamp delta; ban unicode-string extraction and event-description formatting outside
  the armed branch, via a static audit allowlist over the adapter sources. Logging is counters and
  state transitions only, and only for the allowed PID. Record in the README that a running
  Accessibility-authorized tap is a keylogger-capable process by construction, which is the reason
  for the 30 s cap and the visible status.

### G-08 — Teardown ordering, ownership and use-after-free are unspecified (Medium)

- **Location:** PLAN:15, 30.
- **Issue:** "clean removal on close/error" does not fix the order. A modifying tap holds a
  `CFMachPort`, a run-loop source and an `Unmanaged` context pointer; releasing the context before
  the port is invalidated (or invalidating while the callback is in flight on the tap thread) is a
  use-after-free in the input path — the worst place to have one. Multiple exit paths
  (Escape, timeout, focus/PID change, window close, error, `deinit`) invite divergent cleanup.
- **Suggested fix:** One idempotent `teardown(reason)` used by every exit path, with fixed order:
  stop accepting new decisions → drain per G-02 → `CGEvent.tapEnable(false)` (state only) →
  `CFMachPortInvalidate` → remove the run-loop source → stop the tap run loop → release the context
  box. The context is a retained class instance, not a stack pointer or unretained capture. Tests:
  double teardown is a no-op; teardown from every trigger reaches the same terminal state; buffer is
  cleared and counters frozen.

### G-09 — Injected-protocol tests cannot prove native suppression (Medium)

- **Location:** PLAN:30, 32.
- **Issue:** "Test adapters via injected protocol rather than install a live hook" is right, but a
  protocol-level test can only prove the *decision* to return `nil`. It cannot distinguish an active
  tap from a listen-only one, and Apple documents that a listen-only tap ignores the return value —
  so a fixture that passes 100% of its headless tests can suppress nothing. "Verify control flow can
  return nil for consumed events and original event for pass-through (not a listen-only monitor)"
  is not achievable headlessly as stated.
- **Suggested fix:** Split the claim: (i) headless tests own the decision logic; (ii) a static guard
  asserts the literal `.default` options, the presence of a `nil`-returning branch, and the absence
  of `.listenOnly` anywhere in `Sources/**`; (iii) the runtime step adds a capability row — tap
  non-`nil` at `.cgSessionEventTap`, `CGEvent.tapIsEnabled == true`, and the manual matrix's positive
  suppression control. Document explicitly that no headless test result is evidence of suppression.

### G-10 — Shortcut action firing is ambiguous under autorepeat (Medium)

- **Location:** PLAN:29, 36.
- **Issue:** "one Escalier action" per consumed shortcut is the acceptance criterion, but a held chord
  generates repeat key-downs. If the action fires per consumed key-down, the action counter reads
  1+N and the matrix is uninterpretable; if it fires once, autorepeat consumed-keys still must be
  tracked for the drain.
- **Suggested fix:** Pre-register "exactly one action per physical chord press, repeats counted
  separately", implement as fire-on-first-down (`autorepeat == false`) with repeats consumed but not
  re-fired, and test: held chord → `actions == 1`, `repeats_consumed >= 0`.

### G-11 — Synthetic text policy table and buffer limits are not enumerated (Medium)

- **Location:** PLAN:29, 31.
- **Issue:** "delete/backspace/return/tab/arrow policy and buffer limits" is a list of open questions.
  Each has two outcomes that produce different oracle expectations (consumed-and-applied vs
  passed-through), and the character mapping assumes a layout. `Return` and `Tab` also carry page
  behaviour (submit, focus move) that must not fire while armed; arrows and `Page Down` scroll.
- **Suggested fix:** Write the table before implementation: max buffer length (e.g. 128 chars) with
  drop + `truncated` flag, never growth; printable chars appended; `Backspace`/`Delete` edit the
  buffer and are consumed; `Return`/`Tab` consumed and **not** inserted (no newline/tab in buffer);
  arrows/Home/End/PageUp/PageDown consumed and ignored, with the page's scroll counter asserted
  unchanged; all other keys passed through and not inserted. Record that the character map assumes a
  US layout (`kCGKeyboardEventKeyboardType`) and that dead keys/IME are NOT IMPLEMENTED rather than
  inferred from unicode extraction.

### G-12 — Disarm triggers do not cover all documented disable paths (Medium)

- **Location:** PLAN:15, 17.
- **Issue:** The list (Escape, focus/PID change, tap-disable, timeout, user stop) omits
  `kCGEventTapDisabledByUserInput` explicitly, permission revocation mid-run (a session tap keeps
  working or stops depending on the change), screen lock / fast-user-switch, and display sleep. In
  each case the safe outcome is the same (fail open, disarm, invalidate the case), but only if the
  branch exists.
- **Suggested fix:** Treat *every* `tapDisabled*` type plus any `NSWorkspace` session-resign/lock
  notification as the same disarm-and-invalidate path, and record the reason enum. Add a headless
  test per reason. Document that fail-open means ordinary delivery resumes and the case is INVALID,
  not PASS.

### G-13 — Secure input and reserved chords must be measured preconditions, not caveats (Medium)

- **Location:** PLAN:17, 32, 36.
- **Issue:** "Secure input ... unsupported/limited unless tested" is honest, but the failure mode is a
  false pass: while Secure Event Input is enabled (e.g. a terminal with secure keyboard entry, a
  password field anywhere, the login window) keystrokes may not reach the tap at all, so zero browser
  events proves nothing. Likewise, some chords (WindowServer-level ones) are not deliverable or not
  suppressible from a session tap, so "suppressed" and "never arrived" are indistinguishable without a
  control.
- **Suggested fix:** Read secure-input state before and after every case (readback only, no
  `EnableSecureEventInput`/disable call), and mark the case INVALID if it is on. Constrain the
  pre-registered chord set to chords that (i) the browser page actually receives with capture OFF —
  proven per-chord by the G-05 negative control — and (ii) are not WindowServer-reserved. Keep the
  "no universal no-leak claim" statement and extend it to "no claim for chords without a recorded
  negative control".

### G-14 — TCC identity for an unbundled `swift run` fixture is not noted (Low)

- **Location:** PLAN:17, 34.
- **Issue:** Accessibility/Input Monitoring grants are attributed to a code identity (or, for an
  unbundled binary launched from a shell, to the responsible process such as the terminal). A worker
  debugging "tap is always `nil`" can spend the session re-granting a permission that is being
  attributed elsewhere, and the runtime report ("permissions before/after") is meaningless without
  recording *which* identity was granted.
- **Suggested fix:** Add to the runtime template: how the fixture is launched (bundle vs `swift run`
  from which terminal), the responsible process identity, and the exact System Settings pane/entry
  observed. If unbundled, state that the grant may apply to the launcher and that packaged-app
  behaviour is NOT TESTED.

### G-15 — 003's blanket hook ban needs an explicit, scoped supersession note (Low)

- **Location:** PLAN:3, 21; contrast `spikes/003-native-shell-ui/review/preflight.md` N-06.
- **Issue:** 003's review established a blanket prohibition on global monitors/taps with a source
  audit. Spike 005 legitimately supersedes it, but only for this directory and only opt-in. Nothing in
  005 requires the boundary to be recorded where 003's audit (and any future reader) will look, so a
  correct 005 can look like a violation, or the supersession can be read as applying to 003's shell.
- **Suggested fix:** Coordinator adds one cross-reference line to 003's README/review records: the ban
  stands for 003; 005 is the single opt-in exception, runtime-gated, and 005 results do not validate
  003's shell. 005's README repeats the "fixture-specific, not product validation, not a HackerRank
  signal" statement already implied by PLAN:36.

## Pre-implementation conditions

- [ ] **G-01:** pin placement/options/mask, frontmost-app gating, prompt-free readback APIs and the
  `.unavailable` arm state in PLAN.
- [ ] **G-02:** write the key-up-authority invariant and the bounded drain contract (timeout,
  repeat handling, `drain_orphans`, arm settle, INVALID classification).
- [ ] **G-03:** decide and record the `flagsChanged` / modifier / flag-normalization rule.
- [ ] **G-04:** forbid event injection by name in the plan and add the static-audit symbol list;
  require a non-activating control/readout surface.
- [ ] **G-05:** add the per-chord capture-OFF negative control, precondition assertions, scoped pass
  criterion, counter set and capture-phase/no-`preventDefault` static check.
- [ ] **G-06/G-07:** state the callback budget invariant and the hot-path privacy allowlist, with
  static guards.
- [ ] **G-10/G-11:** pre-register action-firing semantics and the text/control-key policy table.
- [ ] **Before interactive runtime only:** G-08, G-12, G-13, G-14.
- [ ] **With the README:** G-09's claim split, G-15's cross-reference.

No finding requires a live tap, a permission grant, a GUI launch, a browser, or a real interview
page at this gate. Runtime no-bubble behaviour remains NOT RUN and NOT ESTABLISHED.
