# Spike 005 — scoped re-review of keyboard fix 1

Scope: `spikes/005-global-keyboard-routing` only, commit `94c895b9a057e1deca57ce2832e36655120ee759`
against `396858b` (13 files, +1118/-181). Reviewer: subagent `keyboard-fix-review`. Date:
2026-10-26.

Inputs: `PLAN.md`; `review/preflight-resolutions.md`; `review/implementation-review.md` findings
I-1/I-2/I-3; `review/implementation-report.md`; `spikes/001-transcription/.tools/reviews/keyboard-fix-1.diff`;
HEAD source/tests; pre-fix source; retained `.build/logs/`. The review diff is byte-identical to
`git diff 396858b..94c895b` (`cmp` exact-match, 1849 lines). The coordinator's 69 core + 12 adapter
XCTest, 12 Node, package/strict-verify and 195-file privacy results are treated as independently
established and were not rerun. No build, test suite, app, browser, server, tap, permission, GUI or
synthetic typing was performed here. No source/test/diff was edited; the only write is this report.

## Verdict summary

| Item | Verdict | Basis |
|---|---|---|
| **I-1** production callback/delivery/teardown seam | **ADDRESSED** | `AdapterCoordinator` is production wiring used by `TapAdapter`; `RoutingAdapterTests` exercises the same initializer with injected dependencies and a fake lifecycle target: consume→nil, pass→original, over-budget→one teardown, disabled→fail-closed/no re-arm/no enable, idempotent ordered teardown, callback-after-teardown. |
| **I-2** focus scope adjudication | **ADDRESSED** | Native gate is foreground-application PID only (`NativeChecks.currentGate` → `RoutingEngine.armRejection/firstGateFailure`). PLAN/resolutions and README/FINDINGS/report all state page/field focus and visibility are manual INVALID + immediate Stop, and same-PID enforcement is NOT IMPLEMENTED/NOT TESTED. No AX/DOM focus code or new permission was added. |
| **I-3** close wait / bounded drain / forced fallback | **ADDRESSED** (normal and forced paths) | `applicationShouldTerminate` returns `.terminateLater`, gate requests one Stop, waits for the coordinator's completion callback after bounded drain/teardown, and has a one-shot 2.5 s `forceAfterDeadline` fallback. `didForceTermination` distinguishes the forced path and docs do not call it clean teardown. A new Minor race is recorded below. |
| **Scoped spec verdict** | **❌ NOT PASS** | The three requested findings are addressed, but the fix introduces one new Important teardown regression: settling-phase `shouldRemoveTap` results never schedule teardown, leaving the installed tap/timers/observers/retained context alive until process exit. |
| **Scoped quality verdict** | **⚠️ Needs fix (narrow)** | One Important regression; one Minor close-gate race; two Minor evidence/test gaps. No new Critical under the initial review's criteria. |
| **New Critical** | **None** | No new injection/replay, raw logging, auto-re-enable, persistence/autostart, or silent PASS path found. |
| **New Important** | **One** | Settling-phase teardown is not scheduled (details below). |

The new Important regression is reachable by switching foreground applications during the 250 ms
settling window, or by an unowned repeat during settling. It is not merely a timer-stall edge.

## I-1 — production callback/delivery/teardown wiring

The original finding was that the native adapter's callback decisions and teardown scheduling were
only statically audited (`implementation-review.md:105-113,150-156`). The fix extracts
`RoutingAdapter.AdapterCoordinator` and makes `TapAdapter` use it in production:
`TapAdapter.swift:46-50` constructs the coordinator with `dependencies: self, target: self`;
`TapAdapter.process` delegates the decision/delivery to it (`TapAdapter.swift:262-306`); the
coordinator owns the single teardown sequence (`AdapterCoordinator.swift:133-149`).

Sub-requirement evidence:

| I-1 sub-requirement | Production evidence | Test evidence |
|---|---|---|
| Production seam, not a test-only path | `TapAdapter.start` uses `AdapterCoordinator(configuration:dependencies:target:)` (`TapAdapter.swift:46-50`); the coordinator is in the `RoutingAdapter` library, not the test target | `Package.swift:36-40` adds `RoutingAdapterTests` depending on `RoutingAdapter`/`RoutingCore`; `TestSupport.makeCoordinatorFixture` calls the same initializer with fakes (`TestSupport.swift:111-130`) |
| consume → nil, pass → original token | `AdapterCoordinator.swift:103-113` forwards `nil` only for `.consume`, otherwise `original`; `TapAdapter.process` returns `passUnretained(event)` when non-nil and `nil` when consumed (`TapAdapter.swift:302-306`) | `AdapterCoordinatorTests.swift:6-27` asserts `XCTAssertNil(consumed.event)` and `XCTAssertEqual(passed.event, Token(value: 2))` |
| budget → exactly one teardown | `AdapterCoordinator.swift:101-106` schedules when the budget result says remove; `:151-163` guards `teardownScheduled`/`teardownCompleted` | `AdapterCoordinatorTests.swift:45-80` asserts one scheduled teardown, no second on a later callback, and idempotent `completeTeardown`; `:110-138` covers over-budget while holding a key (drain first, then one teardown) |
| disabled → fail closed, no enable, no re-arm | Disabled notifications are notification event kinds (`AdapterContracts.swift:11-12,43-46`), handled by the engine; `TapAdapter.enableTap()` is only called from `installTap` (`TapAdapter.swift:155`); `TapAdapter.start` refuses a second start (`:37-42`) | `AdapterCoordinatorTests.swift:82-108` asserts pass-through, `.closed`, `.rejected(.alreadyActive)` on re-arm, zero enable calls, one completion |
| idempotent teardown | `AdapterCoordinator.completeTeardown` returns early when already completed (`:133-135`); target operations run once | `AdapterCoordinatorTests.swift:45-80` calls `completeTeardown()` a second time and asserts no extra target calls/completion |

Residual evidence limits (not blockers):
- The native `CGEvent` → `AdapterEvent` mapping and the `TapAdapter` implementations of
  `enableTap/disableTap/invalidateTapAndSource/invalidateTimers/removeObservers/releaseCallbackContext/stopRunLoop`
  are still source-guarded, not behavior-tested. The coordinator seam tests the decision/delivery/
  teardown orchestration, which was the finding; native target operations remain static-audit
  territory. `SourceAuditTests.testFixtureUsesPinnedActiveTapConfiguration` requires the coordinator
  and termination tokens but does not execute them.
- `testOverBudget...`/`testDisabled...` assertions that `enableCalls == 0` are weak because the
  coordinator never calls `enableTap()` at all. No-re-enable is structurally true in the production
  adapter (enable only at install; start is one-shot), but the test does not exercise the production
  target's enable path. This is a coverage note, not a failure of I-1's four named requirements.

**I-1 verdict: ADDRESSED.**

## I-2 — focus scope against the current adjudicated contract

The coordinator's committed ruling is in `preflight-resolutions.md:51-55` and is reflected in
`PLAN.md:15`: the native gate is **foreground-application PID only**; page/tab/editable-field focus
and visibility are separate **manual INVALID + immediate Stop** conditions; automatic same-PID
field-focus enforcement remains **NOT IMPLEMENTED** and must be disclosed. This is the current
contract, not the original review's broader AX/DOM suggestion.

Implementation evidence:
- `NativeChecks.foregroundPID()` uses `NSWorkspace.shared.frontmostApplication?.processIdentifier`
  and `currentGate()` builds only foreground PID, permission readback and secure-input state
  (`NativeChecks.swift:10-31`). There is no AX focused-window or DOM/field-focus authority.
- `RoutingEngine.armRejection` and `firstGateFailure` compare `gate.foregroundPID` against
  `configuration.allowedPID`; they do not inspect page/field focus (`RoutingEngine.swift:682-706`).
- The new adapter library is banned from `AXUIElement` by
  `SourceAuditTests.testAdapterLibraryContainsNoNativeOrSideEffectSymbols`; the fixture guard still
  bans `AXUIElementSetAttributeValue`. No new permission or surveillance was added.

Documentation evidence:
- `README.md:67` says foreground-application-PID only and page/tab/editable-field focus/visibility
  are separate manual INVALID preconditions that do not auto-disarm.
- `README.md:198-202` records the same-PID residual and says it can remain armed until manual Stop
  or the 30 s timeout.
- `FINDINGS.md` F-22 (line 29) says automatic same-PID field-focus enforcement is NOT IMPLEMENTED /
  NOT TESTED; F-12/F-23 are consistent with foreground-app PID loss and close/drain behavior.
- `implementation-report.md:36-40` and `:345-355`, `:385-389` state the adjudication and the
  residual explicitly.

No material inconsistency found. One wording nuance remains: `preflight-resolutions.md:16` (G-04)
says "failing foreground/focus checks disarms", which is broader than the later PID-only
clarification; the later binding clarification, PLAN:15, README, FINDINGS and report all resolve it
to foreground-application PID. Treat G-04's "focus" as the native app-focus gate, not page/field
focus. This is a documentation-precision note, not an I-2 failure.

**I-2 verdict: ADDRESSED.**

## I-3 — close wait, bounded drain, forced fallback

Implementation:
- `applicationShouldTerminate` computes whether the adapter still needs teardown, requests one Stop
  through `TerminationGate`, and returns `.terminateLater` when waiting
  (`AppDelegate.swift:33-43`). `TerminationGate.request` suppresses duplicate Stop requests and marks
  waiting (`TerminationGate.swift:17-31`).
- The gate waits for `adapterTeardownDidComplete`, which is the adapter's `onTeardownComplete`
  callback; the coordinator invokes `teardownDidComplete()` only at the end of its ordered teardown
  (`AdapterCoordinator.swift:133-149`; `TapAdapter.swift:390-392`). The normal path therefore waits
  for the coordinator's bounded drain and cleanup, not merely for `stop()` to be called.
- The forced path is a single 2.5 s `DispatchQueue.main.asyncAfter` that calls
  `forceAfterDeadline()` and replies only if the gate is still waiting (`AppDelegate.swift:45-57`;
  `TerminationGate.swift:39-44`). `didForceTermination` is public/readable and the report/README say
  the forced path cannot claim clean teardown (`implementation-report.md:401-406`;
  `README.md:203-206`).
- Tests cover: immediate termination when no teardown is pending; waiting through a key-up drain and
  scheduled teardown; drain-deadline invalidation before termination; repeated close not duplicating
  Stop; forced fallback one-shot and bounded (`TerminationGateTests.swift:6-93`). The coordinator
  close/drain tests also assert one teardown and one completion.

Residual evidence limits:
- The AppKit glue (`applicationShouldTerminate` and `NSApp.reply`) is source-audited, not
  behavior-tested. The tests exercise the production `TerminationGate` and `AdapterCoordinator`, not
  `AppDelegate`. Runtime close behavior remains NOT RUN, correctly disclosed.
- The forced fallback is distinguished in code/tests/docs (`didForceTermination`) but is not surfaced
  in a status snapshot or emitted record. Because the app is terminating, a human run record must
  capture it; the docs do not claim clean teardown. This is a transparency residual, not a false
  clean-teardown claim.
- **New Minor race (see below):** `teardownCompleted` is set at the start of `completeTeardown`, so a
  termination request in the cleanup window can return `.terminateNow` before cleanup finishes.

**I-3 verdict: ADDRESSED for the requested close/termination mechanism; new Minor race recorded.**

## New Important — settling-phase failures never schedule teardown

### Trace

1. During the 250 ms settling window, `RoutingEngine.tick` handles two failure paths and sets
   `phase = .off` before returning `shouldRemoveTap: true`:
   - lifetime expiry while settling (`RoutingEngine.swift:119-133`);
   - preconditions lost at the settle deadline (`RoutingEngine.swift:136-150`).
2. `RoutingEngine.handle` during settling has two more such paths:
   - gate failure (`failArm` sets `.off`) and `shouldRemoveTap: true`
     (`RoutingEngine.swift:199-208`; `failArm` at `:707-717`);
   - unowned autorepeat (`failArm`, `shouldRemoveTap: true`) (`RoutingEngine.swift:210-222`).
3. `AdapterCoordinator.tick` receives `tick.shouldRemoveTap == true` and calls `scheduleTeardown()`
   (`AdapterCoordinator.swift:65-72`). `AdapterCoordinator.process` calls it when
   `decision.shouldRemoveTap` (`:103-105`).
4. `scheduleTeardown()` refuses unless `engine.phase == .closed` (`AdapterCoordinator.swift:151-158`).
   These settling paths are `.off`, so it returns `false`; no teardown is scheduled and
   `teardownScheduled` remains false.
5. `TapAdapter.pump()` discards `TickResult.shouldRemoveTap` (`TapAdapter.swift:228-231`). There is no
   other post-install teardown path: `TapAdapter.threadMain` calls `completeTeardown()` directly only
   for early stop before install and install failure (`TapAdapter.swift:92-102`), not for a later
   settling failure.

This is a regression from `396858b`: the pre-fix `TapAdapter.scheduleTeardown()` had no phase guard
(`guard !teardownScheduled` only) and was called directly from `pump`, `requestUserStop`,
`enqueueSessionStop` and `process` on every `shouldRemoveTap`; the fix moved scheduling into the
coordinator and added the `.closed` guard without preserving the `.off` + `shouldRemoveTap` cases.
Every `shouldRemoveTap` producer and every teardown consumer was enumerated: `tick`, `process` and
`requestStop` all funnel into the single guarded `scheduleTeardown`; `TapAdapter.pump` discards the
returned `TickResult` (a missed backstop, not the cause — the coordinator does attempt scheduling and
the `.closed` guard is what rejects `.off`); `windowWillClose`, `applicationWillTerminate`,
`stopPressed` and the termination gate all reach `adapter.stop()` → `coordinator.requestStop`; the
sole `adapter = nil` site is `adapterTeardownDidComplete`. No other call site needs the same change.

### Impact

- The installed `.defaultTap` stays enabled and installed (pass-through; `engine.handle` in `.off`
  passes at `RoutingEngine.swift:194-197`, so no Unicode extraction or consumption occurs), with its
  timers, session observers and retained callback context alive until process exit.
- The UI sees phase `.off`. `applyPhase` disables the Stop button (`active == false`) and keeps Arm
  disabled because `adapter != nil` (`AppDelegate.swift:257-261`); `armPressed` also refuses while
  `adapter != nil` (`:198`). The user has no in-app recovery path and must close the app.
- This violates the binding lifetime/removal contract: `preflight-resolutions.md:13` ("Never retain a
  tap indefinitely"), `:34` (tap disable/permission/focus/lifetime all disarm), `PLAN.md:15`
  ("clean removal on close/error"), and `README.md:76` (one idempotent coordinator teardown). It also
  contradicts the general F-12/F-23 claims for these paths.
- Reachability: switching to another application during the 250 ms settle makes the settle-deadline
  gate check fail and immediately hits this path. An unowned repeat during settle is a second path.
  The 30 s settling-expiry path is narrower but still affected.

### Severity

Important, not Critical under the initial review's Critical criteria: the leaked tap is pass-through
in `.off` and does no text extraction, logging, injection or auto-re-enable, and the engine/UI
reports `.off` rather than PASS. It is still a global event-tap lifetime/clean-removal violation and
should block runtime approval until fixed.

### Missing evidence

`OffAndArmingTests` asserts the engine returns `shouldRemoveTap` for the settling cases
(`OffAndArmingTests.swift:120-180`), but no `AdapterCoordinatorTests` case arms into settling and
asserts a scheduled teardown. `TerminationGateTests` starts from armed. `testEventWithForeignPIDWhileSettlingPassesAndTearsDown`
is engine-only; its name overstates adapter-level teardown. This gap is why the GREEN adapter suite
does not catch the regression.

### Recommended correction

- Make teardown scheduling accept every `shouldRemoveTap` result regardless of the engine's current
  phase (remove the `engine.phase == .closed` guard, or replace it with an explicit
  `shouldRemoveTap` parameter); retain the existing `teardownScheduled`/`teardownCompleted`
  idempotence.
- Alternatively, have `AdapterCoordinator.tick` and `process` call `completeTeardown()` directly when
  `shouldRemoveTap` is true and scheduling is not possible, and have `TapAdapter.pump()` act on
  `TickResult.shouldRemoveTap` as a backstop.
- Add coordinator tests for: settle-deadline foreground/PID loss, settling unowned repeat, and
  settling lifetime expiry. Assert one scheduled teardown, target cleanup, and no second teardown.

## New Minor — `teardownCompleted` is set before cleanup (close-gate race)

`AdapterCoordinator.completeTeardown` sets `teardownCompleted = true` at `AdapterCoordinator.swift:135`
and only then performs disable/invalidate/timers/observers/release/publish/stop
(`:141-148`). `TapAdapter.teardownIsComplete` exposes that flag to the main thread
(`TapAdapter.swift:33-35`), and `AppDelegate.applicationShouldTerminate` reads it on the main thread
(`AppDelegate.swift:33-40`). Two consequences:

1. A termination request arriving while `completeTeardown` is between line 135 and line 148 can see
   `true` and return `.terminateNow`, bypassing the wait for the completion callback and the rest of
   cleanup. The window is small and process exit still removes the OS tap, so I assess this Minor,
   but it is a narrow breach of I-3's "wait for cleanup".
2. The read/write is unsynchronized across the tap thread and main thread. The write is on the tap
   run loop; the read is on main. The flag is a plain `Bool`. In practice the impact is the same
   narrow race; under strict concurrency checking it would also be a data race.

Recommended: use a separate `teardownStarted` guard for reentrancy and set `teardownCompleted` only
after the target cleanup sequence, before/around the completion callback. A test that observes the
flag mid-teardown (or a termination request from a fake target callback) would pin the ordering.

## New Minor — adapter RED log aborted after the first test

`.build/logs/adapter-red.log` shows the selected 12 tests starting, then the first test
(`testBudgetExceededWhileHoldingAKeyDrainsBeforeTeardown`) failing multiple assertions and a fatal
`Swift/ContiguousArrayBuffer.swift:695: Fatal error: Index out of range` from the fake
scheduled-teardown helper (`TestSupport.swift:145`, indexing an empty array). The process aborts, so
the remaining 11 tests have no independent RED evidence in that log. The implementation report
discloses the fatal error (`implementation-report.md:155-161`), but its "12 selected tests" phrasing
can read as though all 12 were observed red. The GREEN adapter run is 12/0 and is verified. This is
an evidence limitation, not a code failure; the core RED gate (63 tests, 434 failures) is confirmed
by `.build/logs/red-test.log`. No rerun was performed.

## New Minor — a teardown-order test does not actually prove publish-before-stop

`AdapterCoordinatorTests.testTeardownPublishesBeforeStoppingTheRunLoop`
(`AdapterCoordinatorTests.swift:140-154`) records snapshots on `FakeDependencies` and target calls on
`FakeTarget`; it asserts the snapshot count and that `stop` precedes `complete` in the target call
list, but it does not assert that `publish` occurred before `stopRunLoop`. The production order is
visible in `AdapterCoordinator.swift:146-148` (publish then stop), so the behavior is correct on
inspection; the test name overclaims what the separate recorders prove. A shared sequence recorder
would make the ordering assertion meaningful. This is a test-quality note, not a finding against the
implementation.

## Consistency / scope / verification checks

- **Consistency:** every `shouldRemoveTap` producer site was enumerated (`RoutingEngine.tick`
  settling/lifetime paths at `:119-150`, `handle` settling/armed/draining/disabled paths at
  `:199-222,:251-317,:416-482`, `disarm`/`beginDrain`/`finishImmediate`/`finishNonViableStop` at
  `:488-591`, `noteCallbackDuration` at `:623-634`) and every consumer (`AdapterCoordinator.tick`,
  `process`, `requestStop` → the single `scheduleTeardown`; `TapAdapter.pump`/`stop`/`process`;
  `AppDelegate.applicationShouldTerminate`/`windowWillClose`/`applicationWillTerminate`/
  `stopPressed`/`adapterTeardownDidComplete`). The relocation is applied at all call sites — there is
  no second copy of the old unguarded scheduling left in `TapAdapter` — but the new `.closed` guard is
  itself the inconsistent site: it drops the `.off` settling cases the old unguarded scheduler
  handled (new Important above). No other call site needs the identical change.
- **Scope:** the 13-file diff stays inside the spike package. The new `RoutingAdapter` library,
  coordinator, `TerminationGate`, test target and guard tokens are the minimum machinery the I-1
  injected-dependency seam and I-3 close-gate require; AppDelegate/doc changes implement I-2/I-3 and
  the stale-snapshot minor. One non-issue-driven behavioral change exists: `threadMain` now calls
  `completeTeardown()` on the early-stop and install-failure paths where `396858b` only published and
  finished — safe (no tap/context yet; sets `teardownCompleted`, publishes, stops the run loop, fires
  `onTeardownComplete`) and consistent with the close contract, but it is broader than the literal
  findings. No behavior outside the reported issues was otherwise changed.
- **Verification:** per the scoped constraint (no builds, no suite reruns, CPU-sensitive measurements
  running concurrently) I did not execute the test module. Evidence that the worker ran the *full*
  module, not only flipped tests: `green-test-final.log` runs `swift test` — all 69 RoutingCoreTests
  including `OffAndArmingTests`/`DrainAndLifetimeTests`/`CallbackAndStatusTests`/`ShortcutTests`/
  `TextPolicyTests` (siblings covering the same `shouldRemoveTap`/drain/teardown semantics the fix
  touched) plus all 12 RoutingAdapterTests — 81/0. No sibling-test breakage is visible in the
  retained logs. Caveat: the full GREEN run does not cover the new regression because no adapter test
  exercises a settling-phase `shouldRemoveTap` (documented above).

## RED/GREEN evidence check (no suites rerun)

- **Scoped diff:** `cmp` of `keyboard-fix-1.diff` against `git diff 396858b..94c895b` is exact;
  1849 lines, 13 files, +1118/-181. Diff file list matches the live range.
- **Core RED:** `.build/logs/red-test.log` final summary is `Executed 63 tests, with 434 failures
  (0 unexpected)`; the report's corrected 434 is accurate. Representative failure descriptions in
  `implementation-report.md:128-145` are consistent with the logged assertion failures.
- **Adapter RED:** 12 selected; only the first test executes before the fatal index-out-of-range
  (above). The report says this; it does not overstate the fatal outcome. The remaining 11 tests
  have no observed RED assertion output in that log.
- **GREEN:** `.build/logs/green-test-final.log` shows `RoutingCoreTests` 69/0 and
  `RoutingAdapterTests` 12/0 (combined 81); `.build/logs/node-tests-all.log` shows 12/12; packaging
  log shows `Signature=adhoc`, `TeamIdentifier=not set`, strict verification, exit 0; guard-tamper
  log shows 5 injected violations detected. Source SHA-256 values in
  `implementation-report.md:414-420` match the reviewed HEAD exactly (recomputed with `shasum -a
  256`; no build).
- **Test inclusion:** `Package.swift:31-40` includes both test targets; the new adapter target
  depends on `RoutingAdapter` and `RoutingCore`. No `XCTSkip`, `XCTExpectFailure`, `#if` or
  `@available` skip patterns were found in `Tests/RoutingAdapterTests` or the wider `Tests` tree by
  static search. The fix's only change to an existing test file is additive:
  `SourceAuditTests.swift` gains the adapter-library guard and four required fixture tokens; no
  existing assertion was removed or relaxed.
- **Claim boundary:** all runtime rows remain NOT RUN; no live tap/TCC/GUI/browser/server or
  synthetic typing occurred. The report and README correctly keep native suppression and
  browser non-delivery NOT ESTABLISHED.

## Out-of-scope observations (not reopened)

These are unchanged initial-review minors or runtime limits; they are recorded for the final review
and are not findings of this scoped re-review:

- Final stop cause is still overwritten by drain completion (`RoutingEngine.swift:436-446`); an
  emergency/user stop can be visible only transiently.
- Native extraction clipping beyond 128 UTF-16 units is still not marked with a native truncation
  flag; the one-key fixture does not exercise large native strings.
- The settling branch still lacks an absolute-deadline check inside `handle`; a stalled 10 Hz timer
  can pass input past 30 s before the tick runs.
- Target/mode controls remain editable while armed; mapping is fixed to the fixture default.
- Permission preflight still ANDs `AXIsProcessTrusted()` and `CGPreflightListenEventAccess()`;
  sufficiency for this tap class is unverified/NOT RUN.
- The mask guard still scans only the first `eventsOfInterest` line.
- `serve-local.mjs` still has an uncaught malformed percent-decoding path.
- Teardown releases the retained context before `CFRunLoopStop`, while `preflight-resolutions.md:33`
  orders "stop owned timers/run loop as applicable, then release retained callback context". The
  initial review judged the actual tap/source-invalidation-before-release order safe; the new
  README order matches the code (release → publish → stop → notify). Not reopened as a new finding.
- The report's "No commit" statements (`implementation-report.md:11-12,407-408`) are stale at the
  reviewed HEAD: the fix is committed as `94c895b`. This is documentation drift in the retained
  worker report, not a code/spec issue.
- The initial "stale terminal snapshot can clear a newer adapter" minor appears incidentally
  resolved: `applyPhase` no longer nils `adapter` on `.off`/`.closed` snapshots; `adapter` is cleared
  only in `adapterTeardownDidComplete` after the completion callback. No new identity bug was found in
  the production UI path.

## Execution-probe requests

None are required to establish the static findings. If the coordinator wants confirmation after the
CPU-sensitive measurements, schedule a test-only probe (not performed here, no test edits):
1. A `RoutingAdapterTests` case that arms, sets a mismatching gate at the settle deadline, calls
   `tick()`, and asserts `scheduledTeardowns.count == 1` plus one target cleanup. This should fail on
   the reviewed HEAD because `scheduleTeardown` rejects `.off`.
2. A termination-during-teardown test that invokes a target cleanup callback and checks the gate does
   not return `.terminateNow` until cleanup completes; this would probe the new Minor race.

## Final

- **I-1: ADDRESSED.**
- **I-2: ADDRESSED** against the coordinator's committed PID-only adjudication.
- **I-3: ADDRESSED** for the normal and forced close paths; new Minor race recorded.
- **Scoped spec verdict: ❌ NOT PASS** because of the new Important settling-phase teardown
  regression. The regression is a fix-introduced contract violation, not a failure of the three
  originally requested changes.
- **Scoped quality verdict: ⚠️ Needs fix (narrow).** One Important regression; one Minor close-gate
  race; two Minor test/evidence gaps. No new Critical.
- Runtime remains ALL ROWS NOT RUN / NOT ESTABLISHED.
