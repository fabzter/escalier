import XCTest
@testable import RoutingCore

final class GateAndPrivacyTests: XCTestCase {
    func testNoExtractionOutsideAllowedBranches() {
        var off = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        var offSupply = UnicodeSupply("x")
        _ = press(&off, down(Key.a), supply: offSupply)
        XCTAssertEqual(offSupply.calls, 0)

        var settling = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        _ = settling.beginArm(mode: .text, gate: allowedGate(), heldNonModifierKeys: false, now: 100)
        _ = settling.tapInstalled(at: 100)
        var settlingSupply = UnicodeSupply("x")
        _ = press(&settling, down(Key.a), now: 100.1, supply: settlingSupply)
        XCTAssertEqual(settlingSupply.calls, 0)

        var draining = armedEngine(mode: .text)
        _ = press(&draining, down(Key.a), supply: UnicodeSupply("a"))
        _ = draining.disarm(reason: .userStopped, now: 101)
        var drainSupply = UnicodeSupply("x")
        _ = press(&draining, down(Key.b), now: 101.1, supply: drainSupply)
        XCTAssertEqual(drainSupply.calls, 0)

        var modifiers = armedEngine(mode: .text)
        var modifierSupply = UnicodeSupply("x")
        _ = press(&modifiers, modifierChanged(Key.leftShift, [.shift]), supply: modifierSupply)
        XCTAssertEqual(modifierSupply.calls, 0)

        var reserved = armedEngine(mode: .text)
        var reservedSupply = UnicodeSupply("k")
        _ = press(&reserved, down(Key.k, [.command, .shift]), supply: reservedSupply)
        XCTAssertEqual(reservedSupply.calls, 0)
    }

    func testDisabledNotificationNeverExtractsUnicode() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        _ = press(&engine, KeyEvent(kind: .tapDisabledByTimeout, keyCode: 0), supply: supply)
        XCTAssertEqual(supply.calls, 0)
    }

    func testForegroundMismatchDuringArmedPassesWithoutExtraction() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        let decision = press(&engine, down(Key.a), gate: allowedGate(pid: 1234), supply: supply)

        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(engine.invalidReason, .caseInterrupted)
    }

    func testPermissionLossDuringArmedDisarmsRatherThanCapturing() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        let decision = press(&engine, down(Key.a), gate: allowedGate(permissions: false), supply: supply)

        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.stopReason, .permissionLost)
        XCTAssertEqual(decision.invalidReason, .caseInterrupted)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.phase, .closed)
    }

    func testSecureInputDuringArmedDisarmsRatherThanCapturing() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        let decision = press(&engine, down(Key.a), gate: allowedGate(secureInput: true), supply: supply)

        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.stopReason, .secureInputBegan)
        XCTAssertEqual(decision.invalidReason, .caseInterrupted)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.phase, .closed)
    }

    func testModifierChangeIsAlwaysPassedEvenWhenShiftedStateChanges() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        let decision = press(&engine, modifierChanged(Key.leftShift, [.shift]), supply: supply)

        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.eventClass, .modifierPassThrough)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.phase, .armed)
    }

    func testGateFailureOrderingPrefersAllowedPIDThenForegroundThenPermissionThenSecure() {
        let gate = GateContext(foregroundPID: 9, permissionsAvailable: false, secureInputEnabled: true)
        XCTAssertEqual(gate.failures(allowedPID: 0), [.allowedPIDMissing, .foregroundMismatch, .permissionsUnavailable, .secureInputEnabled])
    }

    func testNoTextSurvivesTermination() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("secret-synthetic"))
        let stop = press(&engine, down(Key.escape))

        XCTAssertEqual(stop.stopReason, .emergencyEscape)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.status(now: 101).text, "")
    }
}
