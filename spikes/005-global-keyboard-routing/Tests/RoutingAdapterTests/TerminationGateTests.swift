import XCTest
import RoutingCore
@testable import RoutingAdapter

final class TerminationGateTests: XCTestCase {
    func testImmediateTerminationWhenNoTeardownIsPending() {
        let gate = TerminationGate()
        var stopCalls = 0

        let request = gate.request(needsTeardownWait: false) {
            stopCalls += 1
        }
        XCTAssertEqual(request, .terminateNow)
        XCTAssertEqual(stopCalls, 0)
        XCTAssertFalse(gate.isWaiting)
    }

    func testCloseWaitsForDrainAndTeardownBeforeTermination() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = arm(fixture, mode: .text)
        _ = coordinator.process(keyDown(0), original: Token(value: 1), unicode: { "a" })

        let gate = TerminationGate()
        var stopCalls = 0
        let request = gate.request(needsTeardownWait: !coordinator.teardownIsComplete) {
            stopCalls += 1
            _ = coordinator.requestStop()
        }
        XCTAssertEqual(request, .waitForTeardown)
        XCTAssertEqual(stopCalls, 1)
        XCTAssertEqual(coordinator.phase, .draining)
        XCTAssertTrue(gate.isWaiting)

        // The owned key-up completes the bounded drain, then the scheduled teardown runs.
        _ = coordinator.process(keyUp(0), original: Token(value: 2), unicode: { nil })
        XCTAssertEqual(fixture.dependencies.scheduledTeardowns.count, 1)
        runFirstScheduledTeardown(fixture.dependencies)

        XCTAssertTrue(coordinator.teardownIsComplete)
        XCTAssertTrue(gate.teardownCompleted())
        XCTAssertFalse(gate.teardownCompleted())
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
        XCTAssertEqual(fixture.target.enableCalls, 0)
    }

    func testClosePendingAtDrainDeadlineInvalidatesBeforeTermination() {
        let fixture = makeCoordinatorFixture(mode: .text)
        let coordinator = arm(fixture, mode: .text)
        _ = coordinator.process(keyDown(0), original: Token(value: 3), unicode: { "a" })

        let gate = TerminationGate()
        XCTAssertEqual(
            gate.request(needsTeardownWait: !coordinator.teardownIsComplete) {
                _ = coordinator.requestStop()
            },
            .waitForTeardown
        )
        XCTAssertEqual(coordinator.phase, .draining)

        fixture.dependencies.uptime = 102.5
        let tick = coordinator.tick()
        XCTAssertTrue(tick.shouldRemoveTap)
        runFirstScheduledTeardown(fixture.dependencies)

        XCTAssertEqual(
            fixture.dependencies.snapshots.last?.invalidReason,
            .pendingOwnershipAtDrainDeadline
        )
        XCTAssertTrue(coordinator.teardownIsComplete)
        XCTAssertTrue(gate.teardownCompleted())
        XCTAssertEqual(fixture.target.teardownCompletions, 1)
    }

    func testRepeatedCloseRequestDoesNotDuplicateStop() {
        let gate = TerminationGate()
        var stopCalls = 0
        _ = gate.request(needsTeardownWait: true) { stopCalls += 1 }
        _ = gate.request(needsTeardownWait: true) { stopCalls += 1 }
        XCTAssertEqual(stopCalls, 1)
        XCTAssertTrue(gate.isWaiting)
    }

    func testForcedFallbackIsBoundedAndOneShot() {
        let gate = TerminationGate()
        var stopCalls = 0
        _ = gate.request(needsTeardownWait: true) { stopCalls += 1 }
        XCTAssertTrue(gate.forceAfterDeadline())
        XCTAssertTrue(gate.didForceTermination)
        XCTAssertFalse(gate.isWaiting)
        XCTAssertFalse(gate.forceAfterDeadline())
        XCTAssertFalse(gate.teardownCompleted())
        XCTAssertEqual(stopCalls, 1)
    }
}
