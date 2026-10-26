import XCTest
import RoutingCore
@testable import RoutingAdapter

struct Token: Equatable {
    let value: Int
}

final class FakeDependencies: AdapterDependencies {
    var uptime: TimeInterval = 100
    var gate = GateContext(foregroundPID: 501)
    var callbackDurationNanos: UInt64 = 100
    private var currentNanos: UInt64 = 0
    private(set) var scheduledTeardowns: [() -> Void] = []
    private(set) var snapshots: [StatusSnapshot] = []

    func monotonicNanos() -> UInt64 {
        let value = currentNanos
        currentNanos += callbackDurationNanos
        return value
    }

    func currentGate() -> GateContext {
        gate
    }

    func scheduleTeardown(_ action: @escaping () -> Void) {
        scheduledTeardowns.append(action)
    }

    func publish(_ snapshot: StatusSnapshot) {
        snapshots.append(snapshot)
    }
}

final class FakeTarget: AdapterLifecycleTarget {
    private(set) var calls: [String] = []
    private(set) var enableCalls = 0
    private(set) var teardownCompletions = 0

    func enableTap() {
        enableCalls += 1
        calls.append("enable")
    }

    func disableTap() {
        calls.append("disable")
    }

    func invalidateTapAndSource() {
        calls.append("invalidate")
    }

    func invalidateTimers() {
        calls.append("timers")
    }

    func removeObservers() {
        calls.append("observers")
    }

    func releaseCallbackContext() {
        calls.append("context")
    }

    func stopRunLoop() {
        calls.append("stop")
    }

    func teardownDidComplete() {
        teardownCompletions += 1
        calls.append("complete")
    }
}

struct CoordinatorFixture {
    let coordinator: AdapterCoordinator
    let dependencies: FakeDependencies
    let target: FakeTarget
}

func rawFlags(_ modifiers: ModifierSet) -> UInt64 {
    var raw: UInt64 = 0
    if modifiers.contains(.command) { raw |= RawModifierBits.command }
    if modifiers.contains(.shift) { raw |= RawModifierBits.shift }
    if modifiers.contains(.control) { raw |= RawModifierBits.control }
    if modifiers.contains(.option) { raw |= RawModifierBits.option }
    return raw
}

func keyDown(_ keyCode: UInt16, _ modifiers: ModifierSet = [], repeat isRepeat: Bool = false) -> AdapterEvent {
    AdapterEvent(
        kind: .keyDown,
        keyCode: keyCode,
        rawModifiers: rawFlags(modifiers),
        isRepeat: isRepeat
    )
}

func keyUp(_ keyCode: UInt16, _ modifiers: ModifierSet = []) -> AdapterEvent {
    AdapterEvent(kind: .keyUp, keyCode: keyCode, rawModifiers: rawFlags(modifiers))
}

func makeCoordinatorFixture(
    mode: ArmMode = .shortcut,
    allowedPID: Int32 = 501
) -> CoordinatorFixture {
    let dependencies = FakeDependencies()
    dependencies.uptime = 100
    dependencies.gate = GateContext(foregroundPID: allowedPID)
    let target = FakeTarget()
    let coordinator = AdapterCoordinator(
        configuration: RoutingConfiguration(allowedPID: allowedPID),
        dependencies: dependencies,
        target: target
    )
    return CoordinatorFixture(
        coordinator: coordinator,
        dependencies: dependencies,
        target: target
    )
}

@discardableResult
func arm(_ fixture: CoordinatorFixture, mode: ArmMode) -> AdapterCoordinator {
    let coordinator = fixture.coordinator
    XCTAssertEqual(
        coordinator.beginArm(
            mode: mode,
            gate: fixture.dependencies.gate,
            heldNonModifierKeys: false
        ),
        .installTap
    )
    XCTAssertTrue(coordinator.tapInstalled(at: 100))
    fixture.dependencies.uptime = 100.3
    let tick = coordinator.tick()
    XCTAssertTrue(tick.phaseChanged)
    XCTAssertEqual(coordinator.phase, .armed)
    fixture.dependencies.uptime = 101
    return coordinator
}

func runFirstScheduledTeardown(_ dependencies: FakeDependencies) {
    XCTAssertFalse(dependencies.scheduledTeardowns.isEmpty)
    dependencies.scheduledTeardowns[0]()
}
