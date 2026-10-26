# Spike 005 — scoped re-review of keyboard fix 2 (round 2)

Scope: `spikes/005-global-keyboard-routing` only, commit `784a020` against `205fc03`
(6 files, +580/-29). Reviewer: subagent `keyboard-fix-review`. Date: 2026-10-26. This is a
continuation of `fix-1-review.md` — only the new-Important N-01 (settling-phase `shouldRemoveTap` /
`.off` scheduling regression) and any new breakage in fix-2 are re-verified. Original I-1/I-2/I-3 are
accepted; all minors from round 1 remain deferred to the single final review.

The review diff `spikes/001-transcription/.tools/reviews/keyboard-fix-2.diff` is byte-identical to
`git diff 205fc03..784a020` (`cmp` exact-match, 766 lines). The coordinator's independent full
`swift test` (69 core + 15 adapter = 84/0), release build, repackage, strict verify, plist, and
204-file privacy scan are treated as established and were not rerun. No suite, build, app, browser,
server, tap, permission, GUI or synthetic typing was performed here. No source/test/index/ref was
edited; the only write is this report.

## Verdict summary

| Item | Verdict | Basis |
|---|---|---|
| **N-01** settling-phase `shouldRemoveTap`/`.off` teardown scheduling | **ADDRESSED** | Guard widened `.closed` → `.closed \|\| .off`; all settling failures now schedule exactly one cleanup; `.draining` exclusion is correct; idempotence preserved. |
| **New Important breakage in fix-2** | **None** | The widened guard cannot schedule on a tap-less `.off` state; every `shouldRemoveTap:true` terminal result lands `.closed` or `.off`. No spurious teardown, no test weakened. |
| **Scoped spec verdict** | **✅ PASS** | N-01 resolved correctly and completely; the fix matches the recommended correction and adds the three requested regression tests. |
| **Scoped quality verdict** | **✅ PASS** | Minimal 5-line production change; faithful tests; genuine RED→GREEN; docs consistent. No new Important or Minor introduced by fix-2. |
| **New Critical** | **None** |  |
| **New Important** | **None** |  |
| **New Minor (fix-2 only)** | **None** |  |

## N-01 — resolution trace

Finding (fix-1-review): settling-phase `shouldRemoveTap:true` results land in `.off` but
`scheduleTeardown()` required `engine.phase == .closed`, so no teardown was scheduled — the installed
tap/timers/observers/retained context leaked and the UI had no Stop/re-arm path.

### Fix applied

`AdapterCoordinator.swift:157` — the single change is the guard:

```swift
guard !teardownScheduled,
      !teardownCompleted,
      engine.phase == .closed || engine.phase == .off,   // was: == .closed
      let dependencies else {
    return false
}
```

Plus a 4-line comment stating callers only reach this for a terminal `shouldRemoveTap`/`closed`
result. No other production code changed (`git diff …Sources/` = 5 lines added, 1 removed in this
file only).

### Why `.closed || .off` is correct and complete

I enumerated every `shouldRemoveTap:true` producer in `RoutingEngine` and its resulting phase:

- Settling failures → `.off`: settle-deadline gate/foreground-PID loss (`tick :136-150`), settling
  lifetime expiry (`tick :119-133`), settling gate failure (`handle :199-208`), settling unowned
  repeat (`handle :210-222`). All four call `failArm` (→ `.off`) or set `.off` directly.
- All armed/draining/disabled/close/budget terminal failures → `.closed`: `finishNonViableStop`,
  `finishImmediate`, `beginDrain` close branch, drain-completion keyup, drain deadline,
  `handleDisabledTap`, and over-budget `disarm`. `.callbackBudgetExceeded` is not in
  `isNonViableStop` (`:593-601`), so a viable over-budget goes `.draining` (no removal) or `.closed`
  when the deadline already passed — never `.off`.

Every non-failure `.off`/`installing`/`closed` state returns `shouldRemoveTap:false`:
`engine.handle` `.off`/`.installing`/`.closed` arm returns pass-through with no removal (`:183-186`);
`engine.tick` `.off`/`.installing`/`.closed` case breaks with no removal (`:157-159`); `disarm` `.off`
returns `shouldRemoveTap:false` (`:521-522`); `noteCallbackDuration` `.off` returns `shouldRemoveTap`
false (`:623-630`). So the `.off` acceptance can only fire for a post-install settling failure —
exactly the states that own an installed tap needing teardown. No tap-less `.off` (arm rejection,
install failure) ever reaches `scheduleTeardown`. **No spurious teardown.**

### Why `.draining` exclusion is correct (not a bug)

No `shouldRemoveTap:true` originates while the engine is `.draining`: every drain exit transitions to
`.closed` first (drain-completion owned keyup → `.closed`; drain deadline → `.closed`; non-viable
disarm during drain → `.closed`; lifetime-capped drain deadline → `.closed`). A live `.draining`
state intentionally keeps the tap installed for the bounded owned-keyup drain; excluding it is
correct, and its terminal event/deadline schedules via `.closed` as the comment says.

### Idempotence and teardown ordering preserved

`teardownScheduled`/`teardownCompleted` still gate `scheduleTeardown` and `completeTeardown`;
`completeTeardown` still runs the ordered sequence disable→invalidate→timers→observers→release→
publish→stop→notify and is a no-op on repeat. For a settling `.off` failure the `engine.phase !=
.closed && != .off` disarm guard is skipped (already `.off`) and the same target sequence runs — no
double-disarm, correct.

### New tests (3 adapter regressions; 12→15)

`AdapterCoordinatorTests` gained exactly the three cases fix-1-review recommended:

- `testSettleDeadlineForegroundLossSchedulesExactlyOneCleanup` — gate mismatch at settle deadline →
  `tick.shouldRemoveTap`, `.off`, exactly one `scheduledTeardowns`, ordered cleanup
  `["disable","invalidate","timers","observers","context","stop","complete"]`, `teardownCompletions==1`,
  `enableCalls==0`, post-teardown process passes without extraction/decision, no second schedule,
  idempotent `completeTeardown`.
- `testSettlingUnownedRepeatSchedulesCleanupWithoutExtraction` — unowned repeat during settle → pass,
  `invalidReason == .repeatWithoutOwnedDown`, zero supplier calls, `.off`, one cleanup, ordered
  teardown, no re-schedule/extraction after.
- `testSettlingLifetimeExpirySchedulesExactlyOneCleanup` — uptime past 30 s during settle →
  `tick.shouldRemoveTap`, `.off`, one cleanup, ordered teardown, no duplicate.

These are additive (+137 lines); no existing test was removed or weakened. Round-1 count was 7
coordinator + 5 gate = 12; now 10 + 5 = 15, matching "3 new production coordinator regressions".

### RED/GREEN evidence (verified, not rerun)

- `.build/logs/n01-red.log`: `swift test --filter 'testSettle|testSettling'` executed 3 tests with 6
  failures, exit 1. The failures are genuine: `scheduledTeardowns` is `0` where `1` is expected
  (`("0") is not equal to ("1")`) plus the `XCTFail` "did not schedule cleanup" — the exact pre-fix
  bug.
- `.build/logs/n01-green.log`: same filter executed 3 tests, 0 failures, exit 0.
- Full suite 84/0 (69 core + 15 adapter) confirmed by the coordinator's independent run and the
  `green-test-final`/report updates; not rerun here.

**N-01 verdict: ADDRESSED.**

## New breakage in fix-2 — none found

Checked specifically for regressions introduced by widening the guard:

- **Spurious teardown:** impossible — only post-install settling failures produce `.off` +
  `shouldRemoveTap:true` (proven above). Tap-less `.off` paths (arm rejection, install failure)
  return `shouldRemoveTap:false`.
- **`.draining` still-valid teardown:** correctly excluded; drain exits always transition `.closed`
  first, so bounded drain still holds the tap until its terminal event/deadline.
- **Idempotence:** `teardownScheduled`/`teardownCompleted` still single-shot; the new tests assert
  `scheduledTeardowns.count == 1` across repeat process/tick/completeTeardown.
- **Test weakening:** none — all +137 lines are new test cases; no assertion removed/relaxed.
- **Docs:** `FINDINGS` F-16 (81→84), new F-24, README status/test-count/adapter-seam lines and the
  contract rows (G-08/G-09/G-12, adapter-seam, close/termination) updated consistently; report round-2
  section matches code and logs.
- **Out of diff scope:** only `fix-1-review.md` (my own prior report) appears as a data file in the
  range; no behavior.

One cosmetic note (not new breakage): `process`'s backstop condition
`decision.shouldRemoveTap || budget.shouldRemoveTap || engine.phase == .closed` omits `.off`, so a
`.off` terminal returns `teardownScheduled=false` on a repeat callback — but `.off` states never
reach that backstop unscheduled (every `.off` path already set `decision.shouldRemoveTap`), so the
reported flag is only a cosmetic asymmetry. Deferred with the other minors.

## Deferred (unchanged; for the one final review)

Per assignment these remain deferred and are not reopened: the `teardownCompleted` early-set /
unsynchronized cross-thread read minor, the round-1 RED-log abort limitation, the
publish-order test overclaim, AppKit/AppDelegate not behavior-tested, and all runtime rows NOT RUN.
`fix-1-review.md`'s out-of-scope list stands.

## Execution-probe requests

None. The doubt that required probing in round 1 (whether `.off` could spuriously schedule) is
resolved by the engine producer/phase enumeration above — no novel probe is needed.

## Final

- **N-01: ADDRESSED.**
- **Scoped spec verdict: ✅ PASS** — the `.closed || .off` guard is complete over every
  `shouldRemoveTap` terminal state; settling failures now schedule exactly one ordered cleanup;
  `.draining` exclusion is correct; idempotence intact.
- **Scoped quality verdict: ✅ PASS** — minimal fix, faithful regression tests, genuine RED→GREEN,
  consistent docs. No new Important or Minor breakage introduced by fix-2.
- Runtime remains ALL ROWS NOT RUN / NOT ESTABLISHED.
