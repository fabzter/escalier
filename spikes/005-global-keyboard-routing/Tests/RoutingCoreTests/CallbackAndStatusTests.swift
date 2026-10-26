import XCTest
@testable import RoutingCore

final class CallbackAndStatusTests: XCTestCase {
    func testCallbackBudgetUnderThresholdIsRecordedWithoutDisarm() {
        var engine = armedEngine(mode: .text)
        let result = engine.noteCallbackDuration(nanoseconds: 1_000_000, now: 101)

        XCTAssertFalse(result.exceeded)
        XCTAssertFalse(result.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .armed)
        XCTAssertEqual(engine.counters.callbackSamples, 1)
        XCTAssertEqual(engine.counters.maxCallbackNanoseconds, 1_000_000)
        XCTAssertEqual(engine.counters.callbackBudgetViolations, 0)
    }

    func testCallbackOverBudgetWithOwnershipInvalidatesAndDrains() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))

        let result = engine.noteCallbackDuration(nanoseconds: 2_000_001, now: 101)
        XCTAssertTrue(result.exceeded)
        XCTAssertEqual(result.stopReason, .callbackBudgetExceeded)
        XCTAssertEqual(result.invalidReason, .callbackBudgetExceeded)
        XCTAssertFalse(result.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .draining)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.counters.callbackBudgetViolations, 1)

        let deadline = engine.tick(now: 102.5, gate: allowedGate())
        XCTAssertTrue(deadline.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .closed)
    }

    func testCallbackOverBudgetWithoutOwnershipTearsDownImmediately() {
        var engine = armedEngine(mode: .shortcut)
        let result = engine.noteCallbackDuration(nanoseconds: 2_000_001, now: 101)

        XCTAssertTrue(result.exceeded)
        XCTAssertTrue(result.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(engine.invalidReason, .callbackBudgetExceeded)
    }

    func testStatusReportsRegisteredActionsAndBoundedText() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("hello"))
        let snapshot = engine.status(now: 101)

        XCTAssertEqual(snapshot.phase, .armed)
        XCTAssertEqual(snapshot.mode, .text)
        XCTAssertEqual(snapshot.text, "hello")
        XCTAssertEqual(snapshot.registeredActionIDs, ["fixture-action"])
        XCTAssertEqual(snapshot.sessionDeadline, 130.0)
        XCTAssertEqual(snapshot.remainingSessionSeconds, 29.0, accuracy: 0.0001)
    }

    func testActionCountersAreSeparateFromTextCounters() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.k, [.command, .shift]), supply: UnicodeSupply("k"))
        _ = press(&engine, up(Key.k))
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("a"))
        _ = press(&engine, up(Key.a))

        let snapshot = engine.status(now: 101)
        XCTAssertEqual(snapshot.actionCount, 1)
        XCTAssertEqual(snapshot.counters.textEvents, 1)
        XCTAssertEqual(snapshot.counters.actions, 1)
        XCTAssertEqual(snapshot.counters.unicodeExtractions, 1)
    }
}
