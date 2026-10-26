import XCTest
@testable import RoutingCore

final class OffAndArmingTests: XCTestCase {
    func testStartsOffAndPassesWithoutTextExtraction() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        let supply = UnicodeSupply("a")

        XCTAssertEqual(engine.phase, .off)
        XCTAssertEqual(engine.retainedText, "")
        let decision = press(&engine, down(Key.a, [.command, .shift]), supply: supply)

        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.eventClass, .passThrough)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.phase, .off)
    }

    func testArmRejectsMissingAllowedPID() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: 0))
        let request = engine.beginArm(
            mode: .text,
            gate: GateContext(foregroundPID: nil),
            heldNonModifierKeys: false,
            now: 100
        )

        XCTAssertEqual(request, .rejected(.allowedPIDMissing))
        XCTAssertEqual(engine.phase, .off)
        XCTAssertEqual(engine.unavailableReason, .allowedPIDMissing)
    }

    func testArmRejectsForeignForegroundAndRemainsOff() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        let request = engine.beginArm(
            mode: .text,
            gate: allowedGate(pid: 999),
            heldNonModifierKeys: false,
            now: 100
        )

        XCTAssertEqual(request, .rejected(.foregroundMismatch))
        XCTAssertEqual(engine.phase, .off)
        XCTAssertEqual(engine.unavailableReason, .foregroundMismatch)
    }

    func testArmRejectsPermissionsSecureInputAndHeldKeys() {
        var permissions = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        XCTAssertEqual(
            permissions.beginArm(
                mode: .text,
                gate: allowedGate(permissions: false),
                heldNonModifierKeys: false,
                now: 100
            ),
            .rejected(.permissionsUnavailable)
        )

        var secure = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        XCTAssertEqual(
            secure.beginArm(
                mode: .text,
                gate: allowedGate(secureInput: true),
                heldNonModifierKeys: false,
                now: 100
            ),
            .rejected(.secureInputEnabled)
        )

        var held = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        XCTAssertEqual(
            held.beginArm(
                mode: .text,
                gate: allowedGate(),
                heldNonModifierKeys: true,
                now: 100
            ),
            .rejected(.heldNonModifierKeys)
        )
    }

    func testNilTapInstallationIsUnavailableNeverArmed() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        XCTAssertEqual(
            engine.beginArm(mode: .text, gate: allowedGate(), heldNonModifierKeys: false, now: 100),
            .installTap
        )
        engine.tapInstallationFailed(.tapReturnedNil)

        XCTAssertEqual(engine.phase, .off)
        XCTAssertEqual(engine.unavailableReason, .tapReturnedNil)
        XCTAssertEqual(engine.tick(now: 100.5, gate: allowedGate()).shouldRemoveTap, false)
        XCTAssertNotEqual(engine.phase, .armed)
    }

    func testSettlingPassesWithoutExtractionThenArms() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        let supply = UnicodeSupply("a")
        XCTAssertEqual(
            engine.beginArm(mode: .text, gate: allowedGate(), heldNonModifierKeys: false, now: 100),
            .installTap
        )
        XCTAssertTrue(engine.tapInstalled(at: 100))
        XCTAssertEqual(engine.phase, .settling)

        let during = press(&engine, down(Key.a), now: 100.1, supply: supply)
        XCTAssertEqual(during.disposition, .pass)
        XCTAssertEqual(during.eventClass, .settlingPassThrough)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.counters.settledInputsPassed, 1)

        let tick = engine.tick(now: settleAt, gate: allowedGate())
        XCTAssertTrue(tick.phaseChanged)
        XCTAssertEqual(engine.phase, .armed)
        XCTAssertEqual(engine.installedAt, 100)
        let status = engine.status(now: settleAt)
        XCTAssertGreaterThan(status.remainingSessionSeconds, 29.0)
        XCTAssertLessThanOrEqual(status.remainingSessionSeconds, 30.0)
    }

    func testSettleFailsClosedWhenPreconditionsNoLongerHold() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        XCTAssertEqual(
            engine.beginArm(mode: .text, gate: allowedGate(), heldNonModifierKeys: false, now: 100),
            .installTap
        )
        XCTAssertTrue(engine.tapInstalled(at: 100))

        let tick = engine.tick(now: settleAt, gate: allowedGate(pid: 999))
        XCTAssertEqual(engine.phase, .off)
        XCTAssertEqual(engine.unavailableReason, .preconditionsLostWhileSettling)
        XCTAssertTrue(tick.shouldRemoveTap)
        XCTAssertNil(engine.installedAt)
        XCTAssertEqual(engine.status(now: settleAt).remainingSessionSeconds, 0)
        XCTAssertNotEqual(engine.phase, .armed)
    }

    func testEventWithForeignPIDWhileSettlingPassesAndTearsDown() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        let supply = UnicodeSupply("a")
        XCTAssertEqual(
            engine.beginArm(mode: .text, gate: allowedGate(), heldNonModifierKeys: false, now: 100),
            .installTap
        )
        XCTAssertTrue(engine.tapInstalled(at: 100))

        let decision = press(&engine, down(Key.a), gate: allowedGate(pid: 999), now: 100.1, supply: supply)
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertTrue(decision.shouldRemoveTap)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.phase, .off)
        XCTAssertEqual(engine.unavailableReason, .preconditionsLostWhileSettling)
    }

    func testUnownedRepeatWhileSettlingFailsTheArmAttempt() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        XCTAssertEqual(
            engine.beginArm(mode: .text, gate: allowedGate(), heldNonModifierKeys: false, now: 100),
            .installTap
        )
        XCTAssertTrue(engine.tapInstalled(at: 100))

        let decision = press(&engine, down(Key.a, repeat: true), now: 100.1)
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.stopReason, .repeatWithoutOwnedDown)
        XCTAssertEqual(decision.invalidReason, .repeatWithoutOwnedDown)
        XCTAssertTrue(decision.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .off)
        XCTAssertEqual(engine.unavailableReason, .preconditionsLostWhileSettling)
        XCTAssertEqual(engine.counters.repeatWithoutOwnership, 1)
    }

    func testCannotRearmAfterClosed() {
        var engine = armedEngine(mode: .text)
        _ = engine.disarm(reason: .userStopped, now: 101)
        XCTAssertEqual(engine.phase, .closed)

        let request = engine.beginArm(
            mode: .text,
            gate: allowedGate(),
            heldNonModifierKeys: false,
            now: 102
        )
        XCTAssertEqual(request, .rejected(.alreadyActive))
        XCTAssertEqual(engine.phase, .closed)
    }
}
