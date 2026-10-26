# Spike 005 implementation report

Status: **round 1 review fixes applied; round 2 N-01 settling-cleanup fix applied; headless/build/
static slice green; all interactive runtime rows NOT RUN.** Added the plan-required injected
adapter/callback seam, close/termination path, and the settling-phase cleanup fix; narrowed the focus
claim to foreground-application PID. No live event tap was created, no permission was requested or
granted, no GUI/browser/server was launched, and no synthetic text was typed outside the test
process.

Date: 2026-10-26. Worker: implementation subagent. Owner scope: implementation, tests,
Package.swift/resources/tools, README/FINDINGS and this report. The coordinator owns PLAN.md,
review/preflight-resolutions.md and the independent review ledger. No subagents, no commits, no
index writes, no model/host installs.

## Environment

- macOS 27.x arm64 (Swift target `arm64-apple-macosx27.0.0`).
- Apple Swift 6.4, `swift-driver 1.168.6`; package tools version 5.9, deployment target macOS 14.
- Node v20.20.2.
- Dependency-free package; build products confined to ignored `.build/`.
- Observed commands and logs are under `.build/logs/`.

## Round 1 review fixes

- **Adapter/callback test seam (Important 1).** Added `RoutingAdapter.AdapterCoordinator`, the
  production callback/delivery and teardown sequencing used by `TapAdapter`, with injected
  dependencies and lifecycle target. A new `RoutingAdapterTests` target exercises the same
  production wiring through fakes: consume→nil, pass→original token, over-budget→one scheduled
  teardown, disabled→no enable and no re-arm, idempotent ordered teardown, callbacks after
  teardown pass harmlessly, and close/drain/termination.
- **Close/error clean removal (Important 3).** Last-window close now enters
  `applicationShouldTerminate` termination-later handling, makes an idempotent Stop request, and
  waits for the coordinator's bounded drain + idempotent teardown. Completion replies to AppKit; a
  one-shot 2.5 s forced fallback prevents an indefinite wait if teardown itself is stuck. The normal
  path and the fallback are exercised through the adapter/termination seam; runtime close behavior
  is still NOT RUN.
- **Focus scope adjudication (Important 2).** Native authority is foreground-application PID only,
  as ruled in the coordinator-owned resolutions. Browser page/tab/editable-field focus and
  visibility are separate manual INVALID preconditions requiring immediate manual Stop. No AX/DOM
  field-focus surveillance or new permission is claimed; same-PID focus loss can remain armed until
  manual Stop/timeout and is recorded as a residual.
- **RED count correction.** The earlier report draft understated the failure count by a factor of
  ten; the retained RED log's final summary is **434 failures** (the selection/failure counts were
  retyped incorrectly). Corrected below; `.build/logs/red-test.log` is retained.
- **Updated fingerprints** are recorded after the packaging run below. No commit or stage action was
  taken.

Exact adapter/close seam tests from round 1 (12; three N-01 settling regressions were added in
round 2, bringing the current adapter suite to 15):

- `AdapterCoordinatorTests`: `testConsumeReturnsNilAndPassReturnsOriginalToken`,
  `testUnsupportedEventPassesWithoutDecisionOrTeardown`,
  `testOverBudgetCallbackSchedulesOneTeardownAndDisablesWithoutEnabling`,
  `testDisabledNotificationPassesFailsClosedAndCannotRearm`,
  `testBudgetExceededWhileHoldingAKeyDrainsBeforeTeardown`,
  `testTeardownPublishesBeforeStoppingTheRunLoop`,
  `testCallbackAfterTeardownCompletionPassesWithoutSideEffects`.
- `TerminationGateTests`: `testImmediateTerminationWhenNoTeardownIsPending`,
  `testCloseWaitsForDrainAndTeardownBeforeTermination`,
  `testClosePendingAtDrainDeadlineInvalidatesBeforeTermination`,
  `testRepeatedCloseRequestDoesNotDuplicateStop`,
  `testForcedFallbackIsBoundedAndOneShot`.

## Round 2 N-01 fix — settling-phase failures schedule cleanup

Confirmed the review finding in the current tree: `RoutingEngine.tick`/`handle` settling failures
(`preflight lost at settle deadline`, `settling lifetime expiry`, `settling unowned repeat`) set
`phase = .off` and return `shouldRemoveTap: true`; `AdapterCoordinator.scheduleTeardown` required
`engine.phase == .closed`, so those results scheduled nothing. The installed tap/timers/observers/
callback context stayed alive and the UI had no Stop path. This was reproduced by three new
`AdapterCoordinatorTests` **before** changing implementation:

```sh
swift test --filter 'AdapterCoordinatorTests/testSettle|AdapterCoordinatorTests/testSettling'
# Executed 3 tests, with 6 failures (0 unexpected); exit 1
# .build/logs/n01-red.log
```

Fix: `scheduleTeardown` now accepts both terminal cleanup phases `.closed` and `.off` while keeping
the existing idempotence guards. It never fires for a still-valid `.draining` state: that state is
excluded, and its terminal event/deadline first transitions to `.closed` (or an invalid close) before
any schedule call. No other cleanup path changed.

New regressions:

- `testSettleDeadlineForegroundLossSchedulesExactlyOneCleanup` — settle-deadline foreground/PID loss:
  exactly one scheduled cleanup, full target teardown once, no extraction after, no second schedule.
- `testSettlingUnownedRepeatSchedulesCleanupWithoutExtraction` — settling unowned repeat: pass-through
  decision, zero Unicode supplier calls, one cleanup, teardown/idempotence, no extraction after.
- `testSettlingLifetimeExpirySchedulesExactlyOneCleanup` — settling lifetime expiry: one cleanup,
  target teardown once, no duplicate schedule/extraction after.

```sh
swift test --filter 'AdapterCoordinatorTests/testSettle|AdapterCoordinatorTests/testSettling'
# Executed 3 tests, with 0 failures; exit 0  (.build/logs/n01-green.log)
swift test --filter RoutingAdapterTests
# Executed 15 tests, with 0 failures; exit 0
swift test --filter OffAndArmingTests
# Executed 10 tests, with 0 failures; exit 0
swift test --filter DrainAndLifetimeTests
# Executed 12 tests, with 0 failures; exit 0
swift test --filter SourceAuditTests
# Executed 11 tests, with 0 failures; exit 0
swift test
# RoutingCoreTests 69/0 + RoutingAdapterTests 15/0 = 84/0; exit 0
```

No live tap/browser/server/TCC/GUI was used for this fix. The other review minors
(`teardownCompleted` early/read synchronization, RED-log abort limitation, publish-order assertion
precision) remain deferred to the one final broad review.

## Preflight report provenance

The original adversarial report was available only through the coordinator-provided session-scratch
transport location, not from the worktree. It was copied verbatim with the real `write` tool to the
relative worktree path `review/preflight.md` (27,945 bytes) exactly once, as explicitly authorized.
It was not re-reviewed, rewritten or extended. `PLAN.md` and
`review/preflight-resolutions.md` were read, not edited.

## Changed/created paths (all under this spike)

- `Package.swift`
- `Sources/RoutingCore/Model.swift`
- `Sources/RoutingCore/KeyPolicy.swift`
- `Sources/RoutingCore/TextBuffer.swift`
- `Sources/RoutingCore/RoutingEngine.swift`
- `Sources/RoutingAdapter/AdapterContracts.swift`
- `Sources/RoutingAdapter/AdapterCoordinator.swift`
- `Sources/RoutingAdapter/TerminationGate.swift`
- `Sources/RoutingFixture/NativeChecks.swift`
- `Sources/RoutingFixture/TapAdapter.swift`
- `Sources/RoutingFixture/AppDelegate.swift`
- `Sources/RoutingFixture/main.swift`
- `Tests/RoutingCoreTests/TestSupport.swift`
- `Tests/RoutingCoreTests/OffAndArmingTests.swift`
- `Tests/RoutingCoreTests/ShortcutTests.swift`
- `Tests/RoutingCoreTests/TextPolicyTests.swift`
- `Tests/RoutingCoreTests/DrainAndLifetimeTests.swift`
- `Tests/RoutingCoreTests/GateAndPrivacyTests.swift`
- `Tests/RoutingCoreTests/CallbackAndStatusTests.swift`
- `Tests/RoutingCoreTests/SourceAuditTests.swift`
- `Tests/RoutingAdapterTests/TestSupport.swift`
- `Tests/RoutingAdapterTests/AdapterCoordinatorTests.swift`
- `Tests/RoutingAdapterTests/TerminationGateTests.swift`
- `Resources/Info.plist`
- `web/index.html`
- `web/oracle.mjs`
- `web/app.css`
- `tools/oracle-audit.mjs`
- `tools/serve-local.mjs`
- `tools/package-app.sh` (ad-hoc signing/verification added after bundle assembly)
- `tools/packaging-audit.mjs`
- `tools/tests/oracle-static.test.mjs`
- `tools/tests/packaging-static.test.mjs`
- `README.md`
- `FINDINGS.md`
- `review/preflight.md` (authorized copy)
- `review/implementation-report.md` (this file)

`git status --short spikes/005-global-keyboard-routing` reports modified tracked files plus the new
untracked `Sources/RoutingAdapter/` and `Tests/RoutingAdapterTests/` directories; no commit, stage
or index write was performed. No file outside 005 was authored or edited by this worker.

## RED evidence (failing assertions before implementation)

The contract types and stubbed engine were authored first so the tests failed on assertions rather
than compilation. Command (from the spike directory):

```sh
swift test 2>&1 | tee .build/logs/red-test.log
```

Observed summary at the RED gate:

```text
Executed 63 tests, with 434 failures (0 unexpected) in 0.136 (0.141) seconds
...
Exit code: 65
```

Correction: an earlier report draft understated this retained failure count by a factor of ten; the
retained log's final summary is 434. The source-history note is kept here rather than silently
rewriting the earlier evidence.

Representative failures were real assertion mismatches, not missing symbols:

- `testShiftedPrintableIsPermitted`: expected `.installTap`, got `.rejected(.foregroundMismatch)`;
  expected `.armed`, got `.off`; expected `.consume`, got `.pass`.
- `testReturnTabDeleteNavigationAndBackspacePolicy`: expected control/navigation consumption and
  text edits; got pass-through and empty text.
- `testFixtureUsesPinnedActiveTapConfiguration`: missing tap location/place/options/callback
  patterns because the fixture was still a stub.
- `testBrowserOracleHasRequiredCountersFieldAndControls`: oracle files did not exist yet.

After the first green pass, five core coverage tests were added (settling unowned-repeat
invalidation, sleep/session-resign stops, non-viable stop during drain, unregistered modified
control/navigation-key policy, and command-modified Backspace preservation), plus one adapter-source
guard. The new adapter seam was first authored as a compiling skeleton; its RED command was:

```sh
swift test --filter RoutingAdapterTests 2>&1 | tee .build/logs/adapter-red.log
# 12 selected tests; assertion failures on arm/delivery/teardown/termination
# (e.g. expected .installTap got .rejected(.alreadyActive); expected nil/original delivery
# mismatch; no scheduled teardown), then a fatal index-out-of-range in the fake
# scheduled-teardown helper; exit 1
```

After implementation the same historical filter was 12/0. Round 2 added three N-01 settling
regressions; the current full suite is **84 tests** (69 RoutingCoreTests + 15 RoutingAdapterTests),
not the RED gate's 63.

## GREEN evidence (exact final commands)

From `spikes/005-global-keyboard-routing`:

```sh
swift build
# Build complete! (0.23 s, debug)

swift build -c release
# Build complete! (2.13 s)

swift test --filter RoutingAdapterTests 2>&1 | tee .build/logs/adapter-green.log
# Executed 15 tests, with 0 failures (0 unexpected) in 0.003 (0.005) seconds

swift test 2>&1 | tee .build/logs/green-test-final.log
# RoutingCoreTests: Executed 69 tests, with 0 failures (0 unexpected)
# RoutingAdapterTests: Executed 15 tests, with 0 failures (0 unexpected)
# combined 84/0; exit 0

node --test tools/tests/*.test.mjs 2>&1 | tee .build/logs/node-tests-all.log
# tests 12, pass 12, fail 0, exit 0 (6 oracle + 6 packaging)

bash tools/package-app.sh 2>&1 | tee .build/logs/package-adhoc.log
# Build complete!
# .build/RoutingFixture.app: valid on disk
# .build/RoutingFixture.app: satisfies its Designated Requirement
# Identifier=local.escalier.spike005.keyboard
# Format=app bundle with Mach-O thin (arm64)
# Signature=adhoc
# TeamIdentifier=not set
# Ad-hoc signed and strictly verified ... (not launched; no TCC grant)
# exit 0

plutil -lint Resources/Info.plist
# Resources/Info.plist: OK

bash -n tools/package-app.sh
# package-app.sh syntax OK (no output beyond echo)
```

Coverage groups: OFF/arm rejection/nil tap/settling; shortcut matching/repeats/ownership; text
policy/bounds/controls/Escape; drain/lifetime/disable/focus/session; gate/privacy;
callback/status; source and browser static audits; plus the adapter seam's production
callback/delivery, budget, disabled, teardown-idempotence and close/drain/termination behavior.
See the test files for exact names.

## Guard tamper evidence

The Swift source guards read `GUARD_ROOT` when set. A temporary copy of `Sources/` and `web/` was
tampered, leaving the worktree untouched; the tampered tree was deleted afterward. Injected:

1. `print("raw-event")` in `TapAdapter.swift`;
2. `print("adapter-raw")` in `Sources/RoutingAdapter/AdapterContracts.swift`;
3. `// tapDisabledByTimeout` on the `eventsOfInterest` mask line;
4. `DispatchQueue.main.async { }` inside the callback boundary;
5. `preventDefault()` in `web/oracle.mjs`.

Command and observed outcome:

```sh
GUARD_ROOT=<temp-copy> swift test --filter SourceAuditTests
# Executed 11 tests, with 5 failures (0 unexpected) in 0.092 s
# - testAdapterLibraryContainsNoNativeOrSideEffectSymbols: AdapterContracts.swift ["print("]
# - testFixtureContainsNoPromptInjectionPersistenceOrRawLogging: TapAdapter.swift ["print("]
# - testDisabledNotificationsAreNotMaskBits: XCTAssertFalse failed
# - testCallbackBoundaryDoesNotDispatchLogOrReadFiles: XCTAssertTrue failed
# - testBrowserOracleDoesNotSuppressOrExfiltrateInput: oracle.mjs ["preventDefault"]
# tamper-run-exit=1
```

The committed tree passes the same 11 guards (0 failures). The Node audits have nine independent
tamper tests: four oracle cases (injected `preventDefault`, injected `fetch(`, weakened listener
options, renamed test field) and five packaging cases (removed strict verification, added `--deep`,
added `spctl`, removed the ad-hoc assertion, removed failure propagation). All are rejected; the
committed oracle and packager pass. This proves the guards are sensitive to these classes of
regression, not that the runtime tap suppresses anything.

## Ad-hoc packaging / signing evidence

The owner requested local ad-hoc signing for launchability. `tools/package-app.sh` now assembles
the bundle, lints the plist, then runs:

```sh
codesign --force --sign - --timestamp=none "$APP"
codesign --verify --strict --verbose=2 "$APP"
# capture codesign --display --verbose=4 and fail unless Signature=adhoc
```

Observed output (`.build/logs/package-adhoc.log`, exit 0):

```text
.build/RoutingFixture.app: replacing existing signature
.build/RoutingFixture.app: valid on disk
.build/RoutingFixture.app: satisfies its Designated Requirement
Identifier=local.escalier.spike005.keyboard
Format=app bundle with Mach-O thin (arm64)
Signature=adhoc
TeamIdentifier=not set
Ad-hoc signed and strictly verified .build/RoutingFixture.app (not launched; no TCC grant)
```

`packaging-audit.mjs` pins the exact ad-hoc signing command, strict verification, captured
signature inspection and failure propagation, and rejects `--deep`, `spctl`, `xattr`, `tccutil`,
`security`/Keychain trust, notarization, `launchctl`, `osascript`, `open`, `sudo`, `--options
`runtime` and quarantine manipulation. Five tamper tests exercise those guards.

This is local ad-hoc signing only: **not Developer ID, not notarized, not a Gatekeeper trust
guarantee**. The ad-hoc code identity (and therefore TCC attribution) may change across rebuilds, so
TCC grant reuse is **unproven**. No certificate was generated or trusted, no Keychain trust was
changed, no Gatekeeper/TCC/quarantine state was altered, no `--deep` workaround was used, and the
app was **not launched**. The runtime launch/TCC rows remain NOT RUN.

## Contract self-review against the binding brief

| Finding/contract | Implementation | Evidence |
|---|---|---|
| G-01 tap location/place/options/mask; unavailable states; no producer-PID authority | `.cgSessionEventTap`, `.headInsertEventTap`, `.defaultTap`, mask only keyDown/keyUp/flagsChanged; disabled notifications handled in callback; nil/failed tap is `UNAVAILABLE`/OFF; gate uses `NSWorkspace` frontmost PID | `SourceAuditTests.testFixtureUsesPinnedActiveTapConfiguration`, `testDisabledNotificationsAreNotMaskBits`, `OffAndArmingTests.testNilTapInstallationIsUnavailableNeverArmed` |
| G-02 key-up authority, repeats, drain, settle | Ownership is `Set<UInt16>` of consumed physical non-modifier downs; matching up removes regardless of flags/mode; repeats of owned keys consumed without action/extraction; unowned repeat passes and INVALIDATES (including settling); 250 ms settle; finite 1.5 s drain capped by 30 s install deadline; pending ownership at deadline is INVALID | `ShortcutTests`, `DrainAndLifetimeTests`, `OffAndArmingTests.testUnownedRepeatWhileSettlingFailsTheArmAttempt` |
| G-03 modifier matching | Match only command/shift/control/option + key code; ignore Caps Lock/Fn/numeric-pad/help/device/unknown bits; `flagsChanged` always passes and is counted separately; modifier-only bindings rejected; pure-modifier shortcuts unsupported | `ShortcutTests.testCapsLockFnNumericPadAndDeviceBitsAreIgnored`, `testFlagsChangedAlwaysPassesAndIsCountedSeparately`, `testModifierOnlyEscapeAndEmptyActionBindingsAreRejected` |
| G-04 text path/control surface | Text is a pure in-memory append; no event creation/post/replay, AX value write, pasteboard or injection; non-activating `NSPanel` with `.nonactivatingPanel` and `becomesKeyOnlyIfNeeded`; Stop/Escape/timeout; no arm-path activation call; source guards ban injection/prompt/pasteboard symbols | `SourceAuditTests.testFixtureContainsNoPromptInjectionPersistenceOrRawLogging`, `TextPolicyTests`, `AppDelegate` |
| G-05 browser oracle | Visible editable field; capture-phase/passive listeners; no suppression; keydown/up, beforeinput/input, composition, focus/blur, visibility/scroll counters; selected non-modifier counters separate from modifier counters; OFF positive control with same chord/profile/page and focused field; precondition readout; post-disarm ordinary recovery key; zero control = INVALID | `SourceAuditTests.testBrowserOracle*`, Node oracle audit + 4 tamper tests, `web/index.html` |
| G-06 executor/budget/UI | All decisions, timers and teardown on one owned tap run loop; callback does no logging/I/O/UI mutation or per-event main dispatch; UI snapshots at 10 Hz from timer; per-callback duration counters measured inside the adapter seam; >2 ms marks INVALID and schedules teardown | `TapAdapter`, `AdapterCoordinator`, `AdapterCoordinatorTests.testOverBudgetCallbackSchedulesOneTeardownAndDisablesWithoutEnabling`, `SourceAuditTests.testCallbackBoundaryDoesNotDispatchLogOrReadFiles` |
| G-07 extraction gating/privacy | Gate (phase, foreground PID, permission, secure input, event policy) before Unicode supplier; supplier is lazy and tests count calls; no event description/log/disk output; no Unicode read in OFF/settling/draining/foreign/modifier/reserved/unrelated branches | `GateAndPrivacyTests.testNoExtractionOutsideAllowedBranches`, all supplier-call assertions, static core/privacy guards |
| G-08 teardown ordering/context | Single idempotent coordinator teardown: stop decisions → drain when viable → disable tap → invalidate port/source → invalidate timers → remove observers → release `passRetained` context → publish final snapshot → stop run loop → notify completion; same run loop as callbacks; double teardown no-op | `AdapterCoordinator.completeTeardown`, `AdapterCoordinatorTests.testTeardownPublishesBeforeStoppingTheRunLoop`, `testOverBudget...`, `TapAdapter` target methods, `Unmanaged.passRetained(self)` guard |
| G-09 claim split | Headless tests prove decisions **and production adapter delivery/teardown wiring** through injected fakes (consume→nil, pass→original, budget→teardown, disabled→no enable, idempotence, close/drain, settling failures); static guards prove `.defaultTap`, nil-return branch and absence of `.listenOnly`; runtime capability (`tapIsEnabled`, non-nil tap, actual suppression) remains NOT RUN | `RoutingAdapterTests` (15), `SourceAuditTests`, runtime matrix R10 |
| G-10 action firing | One action on first physical down; repeats consumed without re-fire; action and text counters separate | `ShortcutTests.testExactChordFiresOnceAndRepeatsAreConsumed`, `CallbackAndStatusTests.testActionCountersAreSeparateFromTextCounters` |
| G-11 text policy/buffers | 128 UTF-16 per event, 1024 retained, scalar-boundary truncation, overflow marked; Backspace removes one grapheme; forward Delete end-of-buffer no-op; Return/Tab consumed not inserted; navigation consumed/ignored; unknown controls pass; US layout; IME/dead keys NOT IMPLEMENTED | `TextPolicyTests`, `TextBuffer`, README table |
| G-12 disable/stop paths | Timeout/user-input disabled notification, permission loss, secure input, foreground-app PID loss, sleep/screen sleep/session resign observers, adapter error, close and lifetime expiry all disarm; no auto re-enable; every non-viable interruption marks the case INVALID (`caseInterrupted` or pending-ownership reason), including during drain; settling failures that land in `.off` still schedule exactly one cleanup; last-window close waits for bounded teardown via the termination gate, with one forced fallback | `DrainAndLifetimeTests`, `RoutingEngine.isNonViableStop`, `TapAdapter.observeSessionEvents`, `TerminationGateTests`, `AdapterCoordinatorTests` (N-01) |
| G-13 secure input/chords | Secure-input readback per gate and on 10 Hz tick before extraction; case fails closed on secure input; per-chord OFF controls and reserved-chord limitation documented | `GateAndPrivacyTests.testSecureInputDuringArmedDisarmsRatherThanCapturing`, README R2/R8 |
| G-14 TCC identity | README/report require launch identity, responsible process, System Settings pane/entry, and distinguish packaged vs unbundled; Info.plist provides packaged identity; no grant attempted | README "Interactive runtime matrix", this report limitations |
| G-15 003 boundary | README records 005 as the single opt-in exception, fixture-specific, runtime-gated, not validating 003; no 003/root edits | README "Supersession boundary" |
| PLAN step 4 / adapter seam | Production `AdapterCoordinator` is the single callback/teardown wiring; fake dependencies/target prove delivery nil-vs-original, budget teardown, disabled no-enable, idempotent teardown, callback-after-teardown, close/drain termination, and settling-failure cleanup without creating a tap | `Sources/RoutingAdapter`, `Tests/RoutingAdapterTests` (15) |
| Focus-scope adjudication | Native gate is foreground-application PID only; page/tab/field focus and visibility are manual INVALID + immediate Stop, not AX/DOM surveillance; same-PID residual documented | README contract/limitations, FINDINGS F-22, runtime matrix R2/R3/R4/R8 |
| N-01 settling cleanup | Settle-deadline foreground loss, settling unowned repeat and settling lifetime expiry return `shouldRemoveTap` in `.off`; coordinator schedules exactly one cleanup, target teardown completes once, no extraction/duplicate schedule, and a valid draining state is excluded | `AdapterCoordinatorTests` three N-01 tests; `.build/logs/n01-red.log` / `n01-green.log` |
| Close/termination | Last-window close returns `.terminateLater`, makes an idempotent Stop request, waits for coordinator teardown completion (bounded drain, INVALID if pending), then replies; a single 2.5 s forced fallback prevents indefinite wait | `TerminationGateTests` (5), `AdapterCoordinatorTests` close tests, `AppDelegate.applicationShouldTerminate` |
| Owner addendum — ad-hoc packaging | Bundle assembly then `codesign --force --sign - --timestamp=none`, `codesign --verify --strict --verbose=2`, captured `Signature=adhoc` assertion with failure propagation; no certificate/Keychain/Gatekeeper/TCC/quarantine changes, no `--deep`, no launch | `tools/package-app.sh` execution log, `tools/packaging-audit.mjs`, five packaging tamper tests, README caveat |

### Adjudicated corrections applied (not mechanically adopted reviewer suggestions)

- Disabled notifications are **not** shifted into `eventsOfInterest` mask bits; they are handled as
  callback notification types and a static guard asserts they are absent from the mask line.
- Suppression ownership is a set of physical key codes, **not** a repeat reference count and
  **not** a `(keyCode, currentModifier)` tuple; a matching physical up is consumed even if flags or
  mode changed.
- Drain is finite (1.5 s, capped by the 30 s absolute install deadline) and pending ownership at the
  deadline marks the case INVALID. No future key-up suppression is promised after tap removal or
  disable.
- Callback performance is an explicitly measured invalidation threshold (2 ms, fixed counters), not
  a hard-real-time or no-allocation claim.
- Native focus is foreground-application PID only. Page/field focus is a manual INVALID + immediate
  Stop condition, not an automatic same-PID AX/DOM disarm; no new permission was added.
- Close/termination is delayed until the coordinator's bounded drain/teardown completes; the 2.5 s
  fallback is a bounded safety escape, not a claim of clean forced teardown.

## Design notes and edge-case behavior

- The engine is single-lifecycle: after `.closed` or an arm rejection, a new arm returns
  `.alreadyActive`; the UI creates a fresh adapter/engine per explicit arm.
- Ordinary disarm clears the buffer immediately. While draining, new text/actions are refused;
  foreign/unknown events pass; only owned ups/repeats are consumed. Closing the last ownership
  produces `drainComplete` and teardown.
- Event-handler deadline checks run before consumption. An event arriving at/after the absolute or
  drain deadline passes and closes the case; it is not consumed beyond the registered window.
- `flagsChanged` is always passed and never consults capture mode for its decision; it is counted
  as modifier delivery.
- An empty/nil Unicode extraction for an otherwise printable allowed event passes (fail open) rather
  than swallowing a key without captured text; this is recorded as `emptyUnicodePasses`.
- Forward Delete is a documented end-of-buffer no-op; Backspace removes one extended grapheme.
- Teardown queued from the callback runs as a run-loop block on the same thread after the callback
  returns, so the retained context is not released under an in-flight callback.
- UI status snapshots are dispatched to the main queue only from the 10 Hz timer and terminal
  transitions; the callback path itself never touches the main queue.
- The fixture panel uses accessory activation policy and `.nonactivatingPanel`; arming never calls
  an activation API. Clicking the panel is expected to change focus and may disarm.
- `TapAdapter.process` maps one native callback to `AdapterEvent`, delegates delivery/decision/budget
  to the same `AdapterCoordinator` exercised by the fake seam, and returns nil only when the
  coordinator reports a consumed event. Unsupported native types and disabled notifications pass
  the original event.
- Teardown scheduling, the ordered native cleanup calls and the final completion callback live in
  the coordinator. `TapAdapter` implements the native enable/disable/invalidate/timer/observer/
  context operations. The retained context is released after tap/source invalidation.
- Last-window close terminates later: the termination gate requests one Stop, waits for the
  coordinator completion callback, and replies to AppKit. A one-shot 2.5 s fallback replies anyway
  if teardown is stuck; that forced path is a bounded safety escape, not a claim of clean teardown.

## Focus scope (adjudicated)

The native gate is **foreground-application PID only**, matching the coordinator-owned resolutions.
It calls `NSWorkspace` frontmost PID before Unicode extraction and does not see browser page, tab or
editable-field focus. Page/tab/field focus and visibility are independent browser/manual acceptance
preconditions: failure is **INVALID and requires immediate manual Stop**, never a PASS and never a
claim that the native tap automatically disarmed. No AX/DOM field-focus surveillance and no new
permission were added. The **same-PID residual** is explicit: focus moving to another window/tab/
field inside the allowed browser process leaves the PID unchanged, so the tap can remain armed until
manual Stop or the bounded 30 s timeout. This residual must be recorded in the runtime report before
runtime approval; automatic same-PID field-focus enforcement is NOT IMPLEMENTED / NOT TESTED.

## Deviations, limitations and unproven claims

1. **Native extraction cap nuance.** The adapter requests at most 128 UTF-16 units from
   `keyboardGetUnicodeString`. Core truncation at 128/1024 and scalar boundaries is proven with an
   injected supplier that returns more than the limit; a native string longer than 128 units is
   clipped by the native call without an additional native-truncation flag. A trailing high
   surrogate at the cap is dropped rather than handed to the buffer as a split scalar. The
   synthetic one-key fixture does not exercise that case. This is a documented limitation, not a
   claimed exact-text success for large compositions.
2. **No runtime suppression proof.** Headless decisions and static active-tap guards do not prove a
   live tap suppresses; a `listenOnly` tap would ignore the return value. `.defaultTap` is pinned,
   but `tapIsEnabled`, non-nil creation and recipient non-delivery remain runtime rows.
3. **No permission/TCC evidence.** No prompt or grant was performed. `AXIsProcessTrusted` and
   `CGPreflightListenEventAccess` are read-only; actual sufficiency for an active session tap,
   secure-input behavior, responsible-process attribution and packaged-vs-terminal identity are
   unverified.
4. **Held-key scan is a snapshot.** `CGEventSource.keyState` is checked over the fixed key universe
   at arm; keys outside that universe are not detectable at arm. The settling unowned-repeat guard
   catches a later repeat but is not continuous held-key tracking.
5. **Sleep/session handlers.** `NSWorkspace` will-sleep, screen-sleep and session-resign
   notifications enqueue a non-viable stop. A dedicated screen-lock observer is not added; lock
   coverage depends on session-resign/sleep notifications and is NOT RUN.
6. **Callback duration includes several gate readbacks** (`NSWorkspace` frontmost, two permission
   queries, secure-input query). No runtime baseline was measured; the 2 ms rule is an invalidation
   threshold, not a performance guarantee.
7. **Focus non-theft is configured/static only.** `.nonactivatingPanel` and
   `becomesKeyOnlyIfNeeded` are set and statically audited; actual browser-focus preservation while
   armed is NOT RUN.
8. **Native focus scope is foreground-application PID only.** Page/tab/editable-field focus and
   visibility are separate browser/manual INVALID preconditions requiring immediate manual Stop.
   No AX/DOM field-focus surveillance or new permission is added, and same-PID page/field focus loss
   can remain armed until manual Stop or the bounded timeout. This residual must be recorded before
   runtime approval; automatic same-PID field-focus disarm is NOT IMPLEMENTED / NOT TESTED.
9. **Ad-hoc signing is not a trust or TCC guarantee.** The bundle is signed ad hoc and strictly
   verified locally, but is not Developer ID/notarized and has no Gatekeeper assessment. The ad-hoc
   identity may change across rebuilds, so TCC grant reuse is unproven. The signed app was not
   launched; packaged launch, TCC attribution and permission behavior are NOT RUN.
10. **Browser oracle uses DOM `keyCode`** for a fixed US-layout probe set. It does not test non-US
    layouts, IME, dead keys or composition correctness; composition events are counted but policy is
    not implemented.
11. **No OFF-control enforcement in software.** The page instructs and displays preconditions, but a
    human could still skip a control; the run sheet makes zero/missing control INVALID.
12. **No server/browser launch.** `tools/serve-local.mjs` is manual-only and was not executed; no
    request/response behavior is proven here.
13. **Close/termination path is designed and seam-tested but NOT RUN.** Last-window close now
    returns `.terminateLater`, makes an idempotent Stop request, and waits for the coordinator's
    bounded drain and idempotent teardown before replying. A one-shot 2.5 s fallback prevents an
    indefinite wait if teardown is stuck; that forced path cannot claim clean teardown, and process
    exit still removes the OS tap. The normal and forced paths are exercised headlessly; runtime is
    NOT RUN.
14. **No commit.** Round 1/2 changes remain unstaged in the worktree (plus two new untracked adapter
    directories); no stage/index action was taken.

## Updated fingerprints (round 2)

Source SHA-256 (relative to this spike):

```text
2587fcf604841a62756f2031ecb7641fe400bdff7078f04284fe98962911f906  Sources/RoutingAdapter/AdapterContracts.swift
900b2298174e0befc3d18f316b675baa4deb52cc37fd8bc395f5d507b26c65f1  Sources/RoutingAdapter/AdapterCoordinator.swift
18425c41b2dd596dcc46da8588bd9fd9ce57d685d639c1f638619083afc6358d  Sources/RoutingAdapter/TerminationGate.swift
7b6ab98085ded451d09e66a3fac18d9c93d825e78c2a90545dac728e88e8afa0  Sources/RoutingFixture/TapAdapter.swift
997c95efaf0dce0af355c80ad2c41fd146c8416b3e790e92f869fdf16edbee85  Sources/RoutingFixture/AppDelegate.swift
33b0ea294c89673ecf47fa44606a13220105876f6e49c2af95d7dd400e694706  Sources/RoutingCore/RoutingEngine.swift
8465d0eaff55fea4b91462cc6f0850c01140fd3230c59ee75b72544dbde90f2c  Package.swift
```

Packaged app after the final ad-hoc signing/verification run:

```text
Identifier=local.escalier.spike005.keyboard
CDHash=1b49aea7cb5d1c576b06302eded608bc5899792e
Signature=adhoc
TeamIdentifier=not set
```

The app was not launched. These fingerprints identify this round's source/binary, not a runtime
approval.

## Interactive runtime matrix — ALL ROWS NOT RUN

These require separate live human approval immediately before execution: exact target
PID/window/page, exact chord and known synthetic text, and any permission grant. Record OS/build,
source/binary fingerprints, browser/build/profile, foreground PID, TCC code/responsible-process
identity and System Settings pane/entry, permissions and secure-input before/after, chord/text
registration, selected-key/input deltas, modifier baseline separately, action/text results,
elapsed/over-budget counters, drain outcome, cleanup and normal-input recovery.

| Row | Case | Status |
|---|---|---|
| R1 | Launch the ad-hoc-signed packaged app; capture OFF; no tap created; prompt-free preflight readback; record TCC identity and whether it survives a rebuild. | **NOT RUN** |
| R2 | OFF positive control with same chord/profile/page/focused field; non-zero selected-key and input counters; failed field-focus/visibility is INVALID. | **NOT RUN** |
| R3 | Armed shortcut mode exact foreground PID; one action; zero browser selected-key deliveries; modifiers separate; focus/visibility unchanged. Same-PID page/field focus loss is manual INVALID + immediate Stop, not native automatic disarm. | **NOT RUN** |
| R4 | Armed text mode exact synthetic text; exact bounded buffer; zero browser selected-key/input deliveries; field focused; no scroll change; same-PID residual recorded. | **NOT RUN** |
| R5 | Return/Tab/Backspace/forward Delete/navigation policy and no focus/scroll side effects. | **NOT RUN** |
| R6 | Unrelated key/text still delivered while armed. | **NOT RUN** |
| R7 | Escape stop, drain, post-disarm ordinary recovery key (not Escape). | **NOT RUN** |
| R8 | Stop button, foreground-app PID loss, permission loss, secure input, tap disable, sleep/session resign, last-window close, 30 s timeout, no auto re-enable; close waits for bounded teardown/termination. Browser page/field focus loss at the same PID is separately manual INVALID + immediate Stop. | **NOT RUN** |
| R9 | Cleanup, tap/source/timer removal, no launch agent, normal delivery restored, permissions/secure-input after-state. | **NOT RUN** |
| R10 | Non-nil tap, `CGEvent.tapIsEnabled == true`, max callback duration and over-budget count. | **NOT RUN** |

No local result establishes HackerRank server-side invisibility. Browser/OS-reserved chords without
a per-chord OFF delivery control are unproven. Expected modifier delivery is a baseline, not a
leak. All runtime claims remain **NOT ESTABLISHED**.

## Hygiene

- Dependency-free Swift package; no third-party dependencies or host installs.
- No live tap, TCC prompt, GUI launch, browser/server launch, synthetic typing or audio/mic/LLM use
  during this task.
- No event injection/logging/upload/autostart/automatic permission grant in authored sources.
- Adapter tests use injected fakes only; no tap is created by the test target or test process.
- Local ad-hoc signing only; no certificate generation/Keychain trust, Gatekeeper/TCC/quarantine
  change, `--deep` workaround, app launch or TCC grant.
- No commits, staging, subagents or edits outside 005.
- Authored files via `write`/`edit`; the only copied report is the authorized preflight.
