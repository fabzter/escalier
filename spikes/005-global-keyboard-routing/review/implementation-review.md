# Spike 005 — independent implementation review

Scope: `spikes/005-global-keyboard-routing` only, diff `a79f12e..77903f6` (33 files, +5467).
Inputs read: `PLAN.md`; binding amended contracts in `review/preflight-resolutions.md`;
`review/implementation-report.md`; `review/preflight.md` (provenance only); the full committed
source/tests/tools/README/FINDINGS; retained `.build/logs/` evidence. Coordinator's 68/0 XCTest,
12/0 Node, packaging/strict-verify, and 181-file scan results are treated as independently
established; I did not rerun the suites or launch the fixture. No tap, permission, GUI, browser,
server or synthetic typing was performed in this review.

Verdicts:

- **Spec compliance: ❌ Issues found (Important, no Critical).** The binding safety, privacy,
  active-tap, ownership, drain, oracle and packaging contracts are implemented. Two contract
  obligations are not met as written: the plan's injected-protocol adapter tests, and a
  page/field-level focus-change disarm (only foreground-app/PID focus is checked). The close path
  also relies on process exit rather than completing the idempotent teardown.
- **Task quality: Needs fixes (narrow).** Architecture is strong and the core is unusually
  well-tested, but the native callback/teardown wiring is only statically audited, and two
  status/teardown lifecycle edges should be fixed before a runtime attempt.
- **Runtime: ALL ROWS NOT RUN / NOT ESTABLISHED** — by design and correctly disclosed.

## Binding basis applied

The review used the assignment's verbatim constraints and the preflight resolutions. In particular:
capture OFF at startup and no permission/tap/GUI from tests/build/import; visible control/status,
explicit arm/disarm, 30 s maximum, Escape emergency stop, focus/PID-change and tap-disable disarm,
no auto-reenable, no persistence; discard non-armed events without text copying/logging, bounded
buffer cleared on stop/close; no injection/replay; browser page must not `preventDefault` the
measured events. Resolutions: physical-keycode ownership set; flags/key-up not ownership authority;
disabled notifications are callback notification types, not mask bits; 1.5 s drain capped by 30 s
from installation; 128 UTF-16 per extraction / 1024 retained with lazy-gated extraction; 2 ms is an
invalidation threshold, not a hard-real-time claim; modifiers pass and are counted separately; OFF
positive control with the same chord/profile/page/focused field; runtime all NOT RUN.

## Contract matrix

| Contract | Result | Evidence |
|---|---|---|
| OFF at startup; no arm/tap in startup/build/test/import | PASS (static/headless) | `AppDelegate.swift:16-23`; `SourceAuditTests.swift:144-152`; `Package.swift:25-28`; tests import only `RoutingCore` |
| Prompt-free permission/secure-input readback; no request APIs | PASS (static) | `NativeChecks.swift:10-31`; forbidden-token guard `SourceAuditTests.swift:82-97` |
| Active session tap pinned; mask only keyDown/keyUp/flagsChanged; nil/failed install ≠ ARMED | PASS (static + core tests) | `TapAdapter.swift:111-177`; `SourceAuditTests.swift:99-129`; `OffAndArmingTests.swift:87-105` |
| Disabled notifications handled as notification types, not mask bits; no auto-reenable | PASS | `TapAdapter.swift:266-279`; `RoutingEngine.swift:464-487`; `SourceAuditTests.swift:122-129` (one-line mask guard) |
| Ownership = physical non-modifier keycode set; up removes regardless of flags/mode; owned repeats consumed; unowned repeat passes + invalidates | PASS (core) | `RoutingEngine.swift:288-318`, `425-461`; `ShortcutTests.swift:5-30`, `76-95`; `OffAndArmingTests.swift:153-176` |
| 250 ms settle; input during settle passes without extraction; preconditions rechecked | PASS (core) | `RoutingEngine.swift:188-226`; `OffAndArmingTests.swift:107-152` |
| Ordinary disarm clears text immediately, refuses new text/actions, 1.5 s owned-only drain, 30 s absolute cap, pending = INVALID | PASS (core) | `RoutingEngine.swift:537-567`, `753-768`; `DrainAndLifetimeTests.swift:4-84` |
| Modifier matching only cmd/shift/ctrl/opt + keycode; Caps/Fn/numpad/device ignored; flagsChanged always passes; modifier-only unsupported | PASS (core/static) | `Model.swift:28-62`; `ShortcutTests.swift:30-65`, `96-105` |
| Text path: no injection/pasteboard/AX writes; bounded 128/1024 scalar-safe; Backspace/Delete/Return/Tab/arrows policy; unknown/unsupported pass | PASS (core/static) | `TextBuffer.swift:27-89`; `RoutingEngine.swift:342-407`; `TextPolicyTests.swift`; `SourceAuditTests.swift:67-97` |
| Gate before Unicode extraction; lazy supplier not called outside allowed branch | PASS (core) | `RoutingEngine.swift:242-270`, `379-407`; `GateAndPrivacyTests.swift:5-27`; supplier-call counters throughout |
| Callback bounded, same owned run loop, no I/O/log/UI/per-event main dispatch; 10 Hz snapshots; >2 ms invalidates/disarms | PASS (source inspection + core tests) | `TapAdapter.swift:262-306`, `401-406`; `RoutingEngine.swift:607-639`; `CallbackAndStatusTests.swift`; `SourceAuditTests.swift:131-142` |
| One idempotent teardown; disable/invalidate, remove source, stop timers, release retained context, stop run loop | PASS with review notes | `TapAdapter.swift:335-392`; see lifecycle notes |
| Tap disable, permission/secure-input/foreground loss, sleep/session-resign, adapter error, lifetime expiry disarm and fail open; no auto-reenable | PASS (core/static) | `RoutingEngine.swift:464-487`, `569-603`, `719-751`; `TapAdapter.swift:179-208`; `DrainAndLifetimeTests.swift:89-204` |
| Focus/PID-change disarm | **PARTIAL** | Only foreground-app PID (`NativeChecks.swift:10-11,26-31`); no page/field focus authority in engine/adapter |
| Browser oracle: no preventDefault/stopPropagation, passive capture listeners, editable field, required counters, OFF positive control, recovery key | PASS (static) | `web/index.html`; `web/oracle.mjs:1-138`; `SourceAuditTests.swift:171-206`; Node oracle audit + 4 tamper tests |
| No global no-leak or HackerRank-server claim | PASS | `README.md:7-9,164-166,196-197`; `FINDINGS.md:` status/boundary; report limitations |
| Ad-hoc sign + strict verify only; no `--deep`, trust/TCC/Keychain changes, launch | PASS | `tools/package-app.sh`; `tools/packaging-audit.mjs`; log `Signature=adhoc`, `TeamIdentifier=not set`; 5 packaging tamper tests |
| 003 boundary linked; no cross-spike edits; runtime rows NOT RUN | PASS | `README.md:17-22`; diff name list all under 005; `README.md` runtime matrix; report matrix |

## Callback and state-lifecycle review

What I checked in `TapAdapter.process` and the engine transition graph:

- Consume/pass return semantics are correct on inspection: `.consume` returns `nil`
  (`TapAdapter.swift:302-304`), every other decision returns the original event
  (`:305`); unsupported event types pass (`:277-279`). This is the right active-tap shape, but it is
  **not exercised by any test** (see I-1).
- Callback work is bounded and single-run-loop: event construction, pure engine decision, lazy
  Unicode, duration counters, teardown block scheduling; no I/O, logging, UI mutation or per-event
  main-queue dispatch (`TapAdapter.swift:262-306`). 10 Hz snapshots come from the timer
  (`:243-248`; `RoutingEngine` config 0.1 s).
- Ownership and drain are correctly split from flags: key-up removal is by keycode
  (`RoutingEngine.swift:288-296`, `431-448`); repeats of owned keys do not re-fire/extract
  (`:298-303`, `454-457`).
- Disabled-tap handling closes the case, marks pending ownership as INVALID when present, fails
  open for the current event, and schedules teardown without re-enabling
  (`RoutingEngine.swift:464-487`; `TapAdapter.swift:298-300`).
- Teardown is one idempotent function on the tap run loop: disarm-if-needed, disable/invalidate tap,
  remove/invalidate source, invalidate timers, remove observers, release the retained context, then
  stop the run loop (`TapAdapter.swift:335-392`). Callback-triggered teardown is queued as a run-loop
  block, so the retained context is not released under an in-flight callback (`:335-343`;
  report:246-251). No stack context pointer; same executor. This part is sound.
- The "bounded drain if still viable" line in teardown (`TapAdapter.swift:349-354`) is effectively
  dead: `.adapterError` is a non-viable stop (`RoutingEngine.swift:593-602`), so `disarm` closes
  immediately and the following `.draining` tick cannot run. Normal drain-before-teardown is covered
  by the engine and tests; the teardown comment should not imply a drain that cannot happen.
- Final stop cause is lossy: when the last owned key-up completes, `handleDraining` overwrites the
  stored reason with `.drainComplete` (`RoutingEngine.swift:436-446`), and `finishDrainDeadline`
  does the same (`:753-768`). An Escape/user stop is visible only in the transient decision/status;
  the final snapshot says `drainComplete`. This weakens R7 evidence unless the UI is observed during
  the drain; keep a separate drain-outcome field or emergency-stop counter.
- Terminal-status race: `pump()` publishes a closed snapshot before scheduling teardown
  (`TapAdapter.swift:243-247`), and `completeTeardown` publishes again (`:388`). `AppDelegate`
  treats any `.closed`/`.off` snapshot as "clear the adapter" (`AppDelegate.swift:214-224`), with no
  adapter identity in `onStatus`. A terminal snapshot from an old adapter can therefore clear a
  newer adapter if a user re-arms in the narrow interval; the new tap would then continue without a
  UI Stop control. Practically unlikely, but the fix is cheap (capture a per-adapter token and
  ignore stale snapshots).
- Close path: last-window close returns `true` from termination
  (`AppDelegate.swift:25-35`); Stop is requested asynchronously but the process exits without waiting
  for `completeTeardown`. The OS removes the tap with the process, so there is no lingering hook, but
  the documented idempotent teardown and drain classification are not completed; this matches the
  documented limitation (`README.md:193-195`) but is weaker than "clean removal on close/error" as
  written.

## Native adapter / oracle gap

The split is the right one, but the test coverage is asymmetric:

- `Package.swift:25-28` gives the test target only `RoutingCore`; no test can instantiate or call
  `TapAdapter.process`, `pump`, `stop`, `scheduleTeardown` or `completeTeardown`.
- The adapter guarantees are checked by string boundaries/required tokens, not behavior:
  `SourceAuditTests.swift:99-120` (required literals), `:122-129` (one mask line), `:131-142`
  (forbidden tokens inside the callback region). These are useful regression guards and the
  tamper run genuinely fails (`.build/logs/guard-tamper.log`: 4 failures), but they cannot prove
  "consume → nil, pass → original, budget → teardown, disabled → no re-enable, teardown is
  idempotent". PLAN step 4 explicitly required adapter tests through an injected protocol rather
  than a live hook; that requirement is unmet.
- The browser oracle is an inert static page. The Node audit proves the page's source shape, not
  real-browser delivery. It has the right counters, passive capture listeners, no suppression, an
  editable field, preconditions and mandatory OFF positive-control/recovery instructions
  (`web/index.html`; `web/oracle.mjs`). The false-pass protections are correctly delegated to the
  manual run sheet and marked INVALID on zero/failed preconditions, but none of it has run.

## Strengths

- Clean pure-core/native-adapter separation with an explicit gate before any Unicode supplier call;
  the lazy-supplier tests are exactly the right evidence class for the no-extraction branches.
- Correct binding resolutions implemented, not mechanically copied: disabled notifications are
  notification types rather than mask bits; physical-keycode ownership (not repeat counts or
  modifier tuples); finite drain capped by the absolute install deadline; 2 ms as invalidation
  threshold; modifier delivery separated and passed.
- Strong privacy posture: no injection, pasteboard, AX writes, logging, persistent state, network,
  launch agent or auto-reenable; source guards plus real tamper evidence.
- Honest claim boundary: active-vs-listen-only, browser non-delivery, focus preservation, TCC,
  secure input, native clipping, IME/dead keys, close drain and callback timing are all explicitly
  NOT RUN/NOT ESTABLISHED; no global no-leak or HackerRank-server claim.
- The oracle closes the main false-pass holes (passive capture, no preventDefault, editable field,
  selected-key vs modifier separation, same-chord OFF control, recovery key).

## Issues

### Critical (Must Fix)

None. I found no current code path that injects/replays events, logs raw text, auto-re-enables a tap,
persists/autostarts, or silently converts a runtime failure into PASS. The runtime claims are
withheld.

### Important (Should Fix)

1. **No headless adapter/callback test seam (plan-required).** `Package.swift:25-28`; adapter
   `TapAdapter.swift:262-306`; guards only `SourceAuditTests.swift:99-152`. PLAN step 4 and G-09
   require adapter decisions to be tested through an injected protocol, and the report's G-09 row /
   README:172 imply adapter wiring is covered. It is not: consume→nil, pass→original, budget→
   teardown, disabled→no re-enable, and teardown idempotence are untested behavior. Fix by extracting
   a protocol/test seam for the callback decision + teardown scheduling (fake tap/clock/status), or
   explicitly amend the contract and report that only static guards cover the adapter.
2. **"Focus-change disarm" is only app-level PID.** `NativeChecks.swift:10-11,26-31` and
   `RoutingEngine.swift:688-694` gate on `NSWorkspace.frontmostApplication`. If the binding's focus
   requirement includes loss of focus inside the allowed browser process/page field, it is not
   implemented; the browser oracle detects blur and the run sheet makes it INVALID, but the engine
   keeps the tap armed until Stop/timeout. Either add a prompt-free AX/CGWindow focused-window check
   or state explicitly in README/report that only foreground-app focus is detected and page-field
   focus loss is a manual INVALID condition.
3. **Close/error clean-removal contract is not fully executed.** `AppDelegate.swift:25-35` requests
   Stop on last-window close and returns `true` for immediate termination; `completeTeardown`
   (`TapAdapter.swift:345-392`) may not run and the drain cannot be classified. Process exit removes
   the tap, so there is no persistence, but this is weaker than "clean removal on close/error" and
   is only documented as NOT RUN (`README.md:193-195`). Decide before runtime: delay termination
   until teardown completes, or formally carve close-path removal out of the contract.

### Minor (Nice to Have)

- **RED evidence typo.** Report says "43 failures" (`review/implementation-report.md:78`); the
  retained log says 434 (`.build/logs/red-test.log` final summary, lines 660/662). Both are red; correct the
  number so the reproduced evidence matches.
- **Stale terminal snapshot can clear a newer adapter.** `AppDelegate.swift:214-224` nils the
  adapter for any `.closed`/`.off` snapshot; add a per-adapter token/generation to ignore snapshots
  from an older adapter.
- **Final stop cause overwritten by drain completion.** `RoutingEngine.swift:436-446`; keep
  `emergencyEscape`/`userStopped` separately from the drain outcome, or add an emergency-stop
  counter for R7 evidence.
- **Dead teardown drain comment/branch.** `TapAdapter.swift:349-354` cannot drain because
  `.adapterError` is non-viable (`RoutingEngine.swift:593-602`); simplify or correct the comment.
- **Native clipping is not marked.** Adapter caps at 128 and drops a trailing high surrogate
  (`TapAdapter.swift:308-330`); if `keyboardGetUnicodeString` clipped a longer string, the core sees
  exactly 128 and reports no `eventTruncated`. This is disclosed in report:259-265 and README:186-189,
  but the binding says truncation must be marked; either inspect `actualStringLength`/request one
  unit beyond the cap to detect clipping, or keep it explicitly NOT IMPLEMENTED for large native
  compositions.
- **Settling branch has no absolute-deadline check.** `RoutingEngine.swift:188-226` checks the
  session deadline only in `.armed` (`:248`); if the 10 Hz timer stalls, settling can pass input
  past 30 s. Low risk, but the absolute cap should be enforced in both phases.
- **Target/mode controls remain editable while armed.** `AppDelegate.swift:37-170`; changes have no
  effect on the running adapter, but the UI suggests they might. Disable configuration while active
  or label it "next arm".
- **Mapping is fixed, not configurable.** The panel/README advertise only `cmd+shift+K` and
  `armPressed` always passes `[.fixtureDefault]` (`AppDelegate.swift:160-167`). If "configure
  mapping while OFF" was meant literally, a mapping editor is missing; if the fixed probe is the
  contract, say so explicitly.
- **Permission gate may be over-restrictive for this tap class.** `NativeChecks.swift:29` ANDs
  `AXIsProcessTrusted()` and `CGPreflightListenEventAccess()`, while the preflight research says a
  session-level default tap is the Accessibility-class path. Requiring both may make a valid
  Accessibility-only runtime read "unavailable"; since runtime is NOT RUN, classify this as an
  unverified gate rather than a bug.
- **Mask guard is one-line only.** `SourceAuditTests.swift:122-129` scans only the first line
  containing `eventsOfInterest`; a separate mask variable with disabled bits would evade it. Harden
  the guard if this fixture is promoted.
- **`serve-local.mjs` malformed percent-encoding throws.** `decodeURIComponent` at the request path
  (`tools/serve-local.mjs:19-29`) is uncaught; a malformed local request can terminate the manual
  server. Not a security or runtime matrix issue, but easy to harden.
- **README teardown order differs slightly from code.** README says stop timers/run loop then
  release the retained context; `TapAdapter.swift:366-391` invalidates timers, removes observers,
  releases the context, then stops the run loop. The actual order is safe (tap/source invalidated
  before release); align the documentation.

## Cannot verify from the reviewed diff

- Any runtime row R1–R10: tap creation success, `CGEvent.tapIsEnabled == true`, actual suppression
  of the selected non-modifier key/up, browser selected-key/input deltas, focus/visibility/scroll
  preservation, modifier delivery baseline, OFF positive-control counters, Escape consumption,
  stop/timeout/permission/secure-input/sleep behavior, post-disarm recovery, cleanup.
- Real-browser behavior of the oracle (listeners, preconditions, counter IDs, no-suppression) and
  Chrome/WindowServer-reserved chord behavior; no browser or server was launched.
- TCC sufficiency/attribution for the ad-hoc bundle, responsible-process identity, packaged-vs-
  terminal launch identity, Accessibility vs Input Monitoring grant, secure-input behavior, and
  grant reuse across rebuilds. The ad-hoc signature is not Developer ID/notarized and gives no
  Gatekeeper guarantee.
- Native Unicode extraction for shifted/large/composition input; IME, dead keys, non-US layouts;
  the adapter's native 128-unit clipping detection.
- Callback duration under real gate reads versus the 2 ms invalidation threshold; no runtime
  baseline exists.
- Close-path drain/classification, screen-lock detection (only sleep/session-resign observers),
  permission-loss detection outside the 10 Hz/event checks, and whether every OS security change is
  observed.
- The coordinator's 181-file privacy scan beyond 005; I confirmed no private path/email in 005, but
  did not rescan the tree. Test/build/package logs are ignored `.build` artifacts and were reviewed
  for the final summaries, not independently regenerated.
- Whether the implementation worker authored the commit; the reviewed commit exists under the
  owner identity and contains coordinator-owned PLAN/preflight files. No cross-spike edits appear
  in the diff.

## Assessment

**Spec compliance: ❌ (Important gaps; no Critical).** The safety-critical shape is right: OFF
startup, explicit arm, active `.defaultTap`, keycode ownership, finite drain with invalid-on-pending,
lazy-gated text, fail-open interruption paths, no auto-reenable, no injection/logging/persistence,
and a non-suppressing oracle with positive controls. The block is the missing plan-required adapter
test seam, the narrower-than-written focus behavior, and close-path teardown.

**Task quality: Needs fixes (narrow).** This is clean, dependency-free, well-decomposed Swift with
genuine red/green and tamper evidence and unusually honest limitations. Fix the adapter test seam and
the status/teardown lifecycle edges, correct the RED count, and either implement or explicitly narrow
focus/close before requesting interactive runtime approval.
