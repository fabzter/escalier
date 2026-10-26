import XCTest
@testable import RoutingCore

final class DrainAndLifetimeTests: XCTestCase {
    func testDisarmClearsTextImmediatelyAndDrainsOwnedUps() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        _ = press(&engine, down(Key.a), supply: supply)
        XCTAssertEqual(engine.retainedText, "a")

        let disarm = engine.disarm(reason: .userStopped, now: 101)
        XCTAssertEqual(disarm.phase, .draining)
        XCTAssertFalse(disarm.shouldRemoveTap)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.drainDeadline, 102.5)

        let newText = UnicodeSupply("b")
        let freshDown = press(&engine, down(Key.b), now: 101.1, supply: newText)
        XCTAssertEqual(freshDown.disposition, .pass)
        XCTAssertEqual(freshDown.eventClass, .drainPassThrough)
        XCTAssertEqual(newText.calls, 0)
        XCTAssertEqual(engine.retainedText, "")

        let unrelatedUp = press(&engine, up(Key.b), now: 101.1)
        XCTAssertEqual(unrelatedUp.disposition, .pass)

        let ownedRepeat = press(&engine, down(Key.a, repeat: true), now: 101.2)
        XCTAssertEqual(ownedRepeat.disposition, .consume)
        XCTAssertEqual(ownedRepeat.eventClass, .drainRepeat)
        XCTAssertEqual(engine.counters.drainRepeatsConsumed, 1)

        let ownedUp = press(&engine, up(Key.a), now: 101.3)
        XCTAssertEqual(ownedUp.disposition, .consume)
        XCTAssertEqual(ownedUp.eventClass, .drainKeyUp)
        XCTAssertEqual(ownedUp.stopReason, .drainComplete)
        XCTAssertTrue(ownedUp.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(engine.counters.drainOwnedKeyUps, 1)
        XCTAssertEqual(engine.retainedText, "")

        let second = engine.disarm(reason: .userStopped, now: 101.4)
        XCTAssertEqual(second.phase, .closed)
        XCTAssertTrue(second.shouldRemoveTap)
    }

    func testDisarmWithNoOwnershipTearsDownImmediately() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))
        _ = press(&engine, up(Key.a))

        let disarm = engine.disarm(reason: .userStopped, now: 101)
        XCTAssertEqual(disarm.phase, .closed)
        XCTAssertTrue(disarm.shouldRemoveTap)
        XCTAssertEqual(engine.stopReason, .userStopped)
        XCTAssertEqual(engine.status(now: 101).remainingSessionSeconds, 0)
    }

    func testDrainDeadlinePendingOwnershipInvalidates() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))
        _ = engine.disarm(reason: .userStopped, now: 100.5)
        XCTAssertEqual(engine.drainDeadline, 102.0)

        let justBefore = engine.tick(now: 101.99, gate: allowedGate())
        XCTAssertFalse(justBefore.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .draining)

        let deadline = engine.tick(now: 102.0, gate: allowedGate())
        XCTAssertTrue(deadline.shouldRemoveTap)
        XCTAssertEqual(deadline.stopReason, .drainDeadlinePending)
        XCTAssertEqual(deadline.invalidReason, .pendingOwnershipAtDrainDeadline)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(engine.invalidReason, .pendingOwnershipAtDrainDeadline)
    }

    func testDrainDeadlineIsCappedByAbsoluteSessionLifetime() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), now: 129.8, supply: UnicodeSupply("a"))

        let disarm = engine.disarm(reason: .userStopped, now: 129.8)
        XCTAssertEqual(disarm.phase, .draining)
        XCTAssertEqual(engine.drainDeadline, 130.0)

        let deadline = engine.tick(now: 130.0, gate: allowedGate())
        XCTAssertTrue(deadline.shouldRemoveTap)
        XCTAssertEqual(deadline.invalidReason, .pendingOwnershipAtDrainDeadline)
        XCTAssertEqual(engine.phase, .closed)
    }

    func testLifetimeExpiryWithNoOwnershipClosesCleanly() {
        var engine = armedEngine(mode: .text)
        let expiry = engine.tick(now: 130.0, gate: allowedGate())

        XCTAssertTrue(expiry.shouldRemoveTap)
        XCTAssertEqual(expiry.stopReason, .lifetimeExpired)
        XCTAssertNil(expiry.invalidReason)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(engine.remainingSeconds(now: 130.0), 0)
    }

    func testLifetimeExpiryWithOwnershipInvalidates() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), now: 129.5, supply: UnicodeSupply("a"))

        let expiry = engine.tick(now: 130.0, gate: allowedGate())
        XCTAssertTrue(expiry.shouldRemoveTap)
        XCTAssertEqual(expiry.stopReason, .lifetimeExpired)
        XCTAssertEqual(expiry.invalidReason, .pendingOwnershipAtLifetimeExpiry)
        XCTAssertEqual(engine.phase, .closed)
    }

    func testTapDisabledTimeoutWhileArmedFailsOpenAndInvalidates() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))
        let supply = UnicodeSupply("x")

        let decision = press(
            &engine,
            KeyEvent(kind: .tapDisabledByTimeout, keyCode: 0),
            supply: supply
        )
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.eventClass, .disabledTap)
        XCTAssertEqual(decision.stopReason, .tapDisabledByTimeout)
        XCTAssertEqual(decision.invalidReason, .pendingOwnershipAtNonViableStop)
        XCTAssertTrue(decision.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(supply.calls, 0)
    }

    func testTapDisabledByUserInputWithoutOwnershipIsInvalid() {
        var engine = armedEngine(mode: .shortcut)
        let decision = press(&engine, KeyEvent(kind: .tapDisabledByUserInput, keyCode: 0))
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.stopReason, .tapDisabledByUserInput)
        XCTAssertEqual(decision.invalidReason, .caseInterrupted)
        XCTAssertTrue(decision.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(engine.invalidReason, .caseInterrupted)
    }

    func testNonViableStopDuringDrainClosesAndInvalidatesImmediately() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))
        let drain = engine.disarm(reason: .userStopped, now: 101)
        XCTAssertEqual(drain.phase, .draining)

        let error = engine.disarm(reason: .adapterError, now: 101.1)
        XCTAssertEqual(error.phase, .closed)
        XCTAssertTrue(error.shouldRemoveTap)
        XCTAssertEqual(error.stopReason, .adapterError)
        XCTAssertEqual(error.invalidReason, .pendingOwnershipAtNonViableStop)
        XCTAssertEqual(engine.phase, .closed)
    }

    func testForegroundLossWithPendingOwnershipPassesAndInvalidates() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))
        let supply = UnicodeSupply("b")

        let decision = press(&engine, down(Key.b), gate: allowedGate(pid: 999), supply: supply)
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.stopReason, .foregroundChanged)
        XCTAssertEqual(decision.invalidReason, .pendingOwnershipAtNonViableStop)
        XCTAssertTrue(decision.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(supply.calls, 0)
    }

    func testSessionResignAndSystemSleepAreNonViableStops() {
        for reason in [StopReason.sessionResigned, .systemSleep] {
            var engine = armedEngine(mode: .text)
            _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))

            let result = engine.disarm(reason: reason, now: 101)
            XCTAssertEqual(result.phase, .closed, "\(reason)")
            XCTAssertTrue(result.shouldRemoveTap, "\(reason)")
            XCTAssertEqual(result.invalidReason, .pendingOwnershipAtNonViableStop, "\(reason)")
            XCTAssertEqual(engine.phase, .closed, "\(reason)")
        }
    }

    func testTickDisarmsOnPermissionLossAndSecureInput() {
        var permission = armedEngine(mode: .text)
        let permissionTick = permission.tick(now: 101, gate: allowedGate(permissions: false))
        XCTAssertTrue(permissionTick.shouldRemoveTap)
        XCTAssertEqual(permissionTick.stopReason, .permissionLost)
        XCTAssertEqual(permissionTick.invalidReason, .caseInterrupted)
        XCTAssertEqual(permission.phase, .closed)

        var secure = armedEngine(mode: .text)
        let secureTick = secure.tick(now: 101, gate: allowedGate(secureInput: true))
        XCTAssertTrue(secureTick.shouldRemoveTap)
        XCTAssertEqual(secureTick.stopReason, .secureInputBegan)
        XCTAssertEqual(secureTick.invalidReason, .caseInterrupted)
        XCTAssertEqual(secure.phase, .closed)
    }
}

extension RoutingEngine {
    func remainingSeconds(now: TimeInterval) -> Double {
        status(now: now).remainingSessionSeconds
    }
}
