import XCTest
import RoutingCore
@testable import RoutingAdapter

final class AdapterCoordinatorTests: XCTestCase {
    func testConsumeReturnsNilAndPassReturnsOriginalToken() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = arm(fixture, mode: .text)

        let consumed = coordinator.process(
            keyDown(0),
            original: Token(value: 1),
            unicode: { "a" }
        )
        XCTAssertNil(consumed.event)
        XCTAssertEqual(consumed.decision?.disposition, .consume)
        XCTAssertFalse(consumed.teardownScheduled)

        let passed = coordinator.process(
            keyDown(0, [.command]),
            original: Token(value: 2),
            unicode: { nil }
        )
        XCTAssertEqual(passed.event, Token(value: 2))
        XCTAssertEqual(passed.decision?.disposition, .pass)
        XCTAssertFalse(passed.teardownScheduled)
    }

    func testUnsupportedEventPassesWithoutDecisionOrTeardown() {
        let fixture = makeCoordinatorFixture(mode: .shortcut)
        _ = arm(fixture, mode: .shortcut)

        let result = fixture.coordinator.process(
            AdapterEvent(kind: .unsupported),
            original: Token(value: 9),
            unicode: { nil }
        )
        XCTAssertEqual(result.event, Token(value: 9))
        XCTAssertNil(result.decision)
        XCTAssertNil(result.budget)
        XCTAssertFalse(result.teardownScheduled)
        XCTAssertTrue(fixture.dependencies.scheduledTeardowns.isEmpty)
    }

    func testOverBudgetCallbackSchedulesOneTeardownAndDisablesWithoutEnabling() {
        let fixture = makeCoordinatorFixture(mode: .shortcut)
        let coordinator = arm(fixture, mode: .shortcut)
        fixture.dependencies.callbackDurationNanos = 2_000_001

        let result = coordinator.process(
            keyDown(0),
            original: Token(value: 3),
            unicode: { "a" }
        )
        XCTAssertEqual(result.event, Token(value: 3))
        XCTAssertEqual(result.decision?.disposition, .pass)
        XCTAssertTrue(result.budget?.exceeded ?? false)
        XCTAssertTrue(result.teardownScheduled)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)
        XCTAssertEqual(coordinator.phase, .closed)

        // A later callback must not schedule a second teardown.
        _ = coordinator.process(keyDown(1), original: Token(value: 4), unicode: { nil })
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)

        runFirstScheduledTeardown(fixture.dependencies)
        XCTAssertEqual(
            fixture.target.calls,
            ["disable", "invalidate", "timers", "observers", "context", "stop", "complete"]
        )
        XCTAssertEqual(fixture.target.enableCalls, 0)
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
        XCTAssertEqual(fixture.dependencies.snapshots.last?.phase, .closed)

        // Idempotent teardown: no second native action or completion.
        let callsAfterFirst = fixture.target.calls
        coordinator.completeTeardown()
        XCTAssertEqual(fixture.target.calls, callsAfterFirst)
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
    }

    func testDisabledNotificationPassesFailsClosedAndCannotRearm() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = arm(fixture, mode: .text)

        let result = coordinator.process(
            AdapterEvent(kind: .tapDisabledByTimeout),
            original: Token(value: 5),
            unicode: { "never" }
        )
        XCTAssertEqual(result.event, Token(value: 5))
        XCTAssertEqual(result.decision?.eventClass, .disabledTap)
        XCTAssertTrue(result.teardownScheduled)
        XCTAssertEqual(coordinator.phase, .closed)
        XCTAssertEqual(
            coordinator.beginArm(
                mode: .text,
                gate: fixture.dependencies.gate,
                heldNonModifierKeys: false
            ),
            .rejected(.alreadyActive)
        )

        runFirstScheduledTeardown(fixture.dependencies)
        XCTAssertEqual(fixture.target.enableCalls, 0)
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
        XCTAssertEqual(coordinator.phase, .closed)
    }

    func testBudgetExceededWhileHoldingAKeyDrainsBeforeTeardown() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = arm(fixture, mode: .text)

        let down = coordinator.process(keyDown(0), original: Token(value: 6), unicode: { "a" })
        XCTAssertNil(down.event)
        XCTAssertEqual(coordinator.phase, .armed)

        fixture.dependencies.callbackDurationNanos = 2_000_001
        let repeatDown = coordinator.process(
            keyDown(0, repeat: true),
            original: Token(value: 7),
            unicode: { nil }
        )
        XCTAssertNil(repeatDown.event)
        XCTAssertEqual(coordinator.phase, .draining)
        XCTAssertTrue(fixture.dependencies.scheduledTeardowns.isEmpty)

        fixture.dependencies.uptime = 102.5
        let tick = coordinator.tick()
        XCTAssertTrue(tick.shouldRemoveTap)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)
        runFirstScheduledTeardown(fixture.dependencies)

        XCTAssertTrue(coordinator.teardownIsComplete)
        XCTAssertEqual(fixture.dependencies.snapshots.last?.invalidReason, .callbackBudgetExceeded)
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
        XCTAssertEqual(fixture.target.enableCalls, 0)
    }

    func testTeardownPublishesBeforeStoppingTheRunLoop() {
        let fixture = makeCoordinatorFixture(mode: .shortcut)
        let coordinator = arm(fixture, mode: .shortcut)
        _ = coordinator.process(
            AdapterEvent(kind: .tapDisabledByUserInput),
            original: Token(value: 8),
            unicode: { nil }
        )
        runFirstScheduledTeardown(fixture.dependencies)

        XCTAssertEqual(fixture.target.calls.last, "complete")
        XCTAssertEqual(fixture.target.calls.dropLast().last, "stop")
        XCTAssertEqual(fixture.dependencies.snapshots.count, 1)
        XCTAssertEqual(fixture.dependencies.snapshots.first?.phase, .closed)
    }

    func testSettleDeadlineForegroundLossSchedulesExactlyOneCleanup() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = fixture.coordinator
        XCTAssertEqual(
            coordinator.beginArm(
                mode: .text,
                gate: fixture.dependencies.gate,
                heldNonModifierKeys: false
            ),
            .installTap
        )
        XCTAssertTrue(coordinator.tapInstalled(at: 100))
        fixture.dependencies.uptime = 100.3
        fixture.dependencies.gate = GateContext(foregroundPID: 999)

        let tick = coordinator.tick()
        XCTAssertTrue(tick.shouldRemoveTap)
        XCTAssertEqual(coordinator.phase, .off)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)

        guard let cleanup = fixture.dependencies.scheduledTeardowns.first else {
            return XCTFail("settling failure did not schedule cleanup")
        }
        cleanup()
        XCTAssertEqual(
            fixture.target.calls,
            ["disable", "invalidate", "timers", "observers", "context", "stop", "complete"]
        )
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
        XCTAssertEqual(fixture.target.enableCalls, 0)

        var extractionCalls = 0
        let after = coordinator.process(
            keyDown(0),
            original: Token(value: 20),
            unicode: { extractionCalls += 1; return "x" }
        )
        XCTAssertEqual(after.event, Token(value: 20))
        XCTAssertNil(after.decision)
        XCTAssertEqual(extractionCalls, 0)
        XCTAssertEqual(coordinator.tick().shouldRemoveTap, false)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)
        coordinator.completeTeardown()
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
    }

    func testSettlingUnownedRepeatSchedulesCleanupWithoutExtraction() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = fixture.coordinator
        XCTAssertEqual(
            coordinator.beginArm(
                mode: .text,
                gate: fixture.dependencies.gate,
                heldNonModifierKeys: false
            ),
            .installTap
        )
        XCTAssertTrue(coordinator.tapInstalled(at: 100))
        fixture.dependencies.uptime = 100.1

        var extractionCalls = 0
        let result = coordinator.process(
            keyDown(0, repeat: true),
            original: Token(value: 21),
            unicode: { extractionCalls += 1; return "x" }
        )
        XCTAssertEqual(result.event, Token(value: 21))
        XCTAssertEqual(result.decision?.invalidReason, .repeatWithoutOwnedDown)
        XCTAssertEqual(extractionCalls, 0)
        XCTAssertEqual(coordinator.phase, .off)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)

        guard let cleanup = fixture.dependencies.scheduledTeardowns.first else {
            return XCTFail("settling repeat did not schedule cleanup")
        }
        cleanup()
        XCTAssertEqual(
            fixture.target.calls,
            ["disable", "invalidate", "timers", "observers", "context", "stop", "complete"]
        )
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
        XCTAssertEqual(fixture.target.enableCalls, 0)

        _ = coordinator.process(
            keyDown(1),
            original: Token(value: 22),
            unicode: { extractionCalls += 1; return "x" }
        )
        XCTAssertEqual(extractionCalls, 0)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)
        coordinator.completeTeardown()
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
    }

    func testSettlingLifetimeExpirySchedulesExactlyOneCleanup() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = fixture.coordinator
        XCTAssertEqual(
            coordinator.beginArm(
                mode: .text,
                gate: fixture.dependencies.gate,
                heldNonModifierKeys: false
            ),
            .installTap
        )
        XCTAssertTrue(coordinator.tapInstalled(at: 100))
        fixture.dependencies.uptime = 130.0

        let tick = coordinator.tick()
        XCTAssertTrue(tick.shouldRemoveTap)
        XCTAssertEqual(coordinator.phase, .off)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)

        guard let cleanup = fixture.dependencies.scheduledTeardowns.first else {
            return XCTFail("settling lifetime expiry did not schedule cleanup")
        }
        cleanup()
        XCTAssertEqual(
            fixture.target.calls,
            ["disable", "invalidate", "timers", "observers", "context", "stop", "complete"]
        )
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
        XCTAssertEqual(fixture.target.enableCalls, 0)

        var extractionCalls = 0
        _ = coordinator.process(
            keyDown(0),
            original: Token(value: 23),
            unicode: { extractionCalls += 1; return "x" }
        )
        XCTAssertEqual(extractionCalls, 0)
        XCTAssertEqual(coordinator.tick().shouldRemoveTap, false)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)
        coordinator.completeTeardown()
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
    }

    func testCallbackAfterTeardownCompletionPassesWithoutSideEffects() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = arm(fixture, mode: .text)
        _ = coordinator.process(
            AdapterEvent(kind: .tapDisabledByTimeout),
            original: Token(value: 10),
            unicode: { nil }
        )
        runFirstScheduledTeardown(fixture.dependencies)

        let result = coordinator.process(
            keyDown(0),
            original: Token(value: 11),
            unicode: { "a" }
        )
        XCTAssertEqual(result.event, Token(value: 11))
        XCTAssertNil(result.decision)
        XCTAssertFalse(result.teardownScheduled)
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)
    }
}
