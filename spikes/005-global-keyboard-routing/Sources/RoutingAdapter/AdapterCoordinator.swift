import Foundation
import RoutingCore

/// Production callback/teardown coordinator shared by the native fixture and headless
/// adapter tests. It owns the engine decisions, callback budget accounting, teardown
/// scheduling and the single idempotent teardown sequence. The native layer supplies
/// delivery, while tests use the same seam with fake dependencies and a fake target.
public final class AdapterCoordinator {
    public let configuration: RoutingConfiguration
    private var engine: RoutingEngine
    private weak var dependencies: AdapterDependencies?
    private weak var target: AdapterLifecycleTarget?
    private var teardownScheduled = false
    private var teardownCompleted = false

    public init(
        configuration: RoutingConfiguration,
        dependencies: AdapterDependencies,
        target: AdapterLifecycleTarget
    ) {
        self.configuration = configuration
        self.engine = RoutingEngine(configuration: configuration)
        self.dependencies = dependencies
        self.target = target
    }

    public var phase: Phase {
        engine.phase
    }

    public var teardownIsComplete: Bool {
        teardownCompleted
    }

    public var teardownWasScheduled: Bool {
        teardownScheduled
    }

    public var snapshot: StatusSnapshot {
        engine.status(now: dependencies?.uptime ?? 0)
    }

    public func beginArm(
        mode: ArmMode,
        gate: GateContext,
        heldNonModifierKeys: Bool
    ) -> ArmRequest {
        engine.beginArm(
            mode: mode,
            gate: gate,
            heldNonModifierKeys: heldNonModifierKeys,
            now: dependencies?.uptime ?? 0
        )
    }

    @discardableResult
    public func tapInstalled(at now: TimeInterval) -> Bool {
        engine.tapInstalled(at: now)
    }

    public func tapInstallationFailed(_ reason: UnavailableReason) {
        engine.tapInstallationFailed(reason)
    }

    public func tick() -> TickResult {
        guard let dependencies else {
            return TickResult()
        }
        let tick = engine.tick(now: dependencies.uptime, gate: dependencies.currentGate())
        if tick.shouldRemoveTap {
            _ = scheduleTeardown()
        }
        return tick
    }

    public func process<Event>(
        _ event: AdapterEvent,
        original: Event,
        unicode: () -> String?
    ) -> AdapterCallbackResult<Event> {
        guard !teardownCompleted else {
            return AdapterCallbackResult(event: original)
        }
        guard let keyEvent = event.keyEvent else {
            return AdapterCallbackResult(event: original)
        }
        guard let dependencies else {
            return AdapterCallbackResult(event: original)
        }

        let startedAt = dependencies.monotonicNanos()
        let now = dependencies.uptime
        let decision = engine.handle(
            keyEvent,
            gate: dependencies.currentGate(),
            now: now,
            unicode: unicode
        )
        let finishedAt = dependencies.monotonicNanos()
        let elapsed = finishedAt >= startedAt ? finishedAt - startedAt : 0
        let budget = engine.noteCallbackDuration(nanoseconds: elapsed, now: now)

        var scheduled = false
        if decision.shouldRemoveTap || budget.shouldRemoveTap || engine.phase == .closed {
            scheduled = scheduleTeardown()
        }

        let forwarded: Event? = decision.disposition == .consume ? nil : original
        return AdapterCallbackResult(
            event: forwarded,
            decision: decision,
            budget: budget,
            teardownScheduled: scheduled
        )
    }

    public func requestStop(reason: StopReason = .userStopped) -> DisarmResult {
        guard let dependencies else {
            return DisarmResult(phase: engine.phase, shouldRemoveTap: false, stopReason: reason)
        }
        let result = engine.disarm(reason: reason, now: dependencies.uptime)
        if result.shouldRemoveTap {
            _ = scheduleTeardown()
        }
        return result
    }

    public func publishStatus() {
        guard let dependencies else { return }
        dependencies.publish(engine.status(now: dependencies.uptime))
    }

    public func completeTeardown() {
        guard !teardownCompleted else { return }
        teardownCompleted = true

        if engine.phase != .closed && engine.phase != .off {
            _ = engine.disarm(reason: .adapterError, now: dependencies?.uptime ?? 0)
        }

        target?.disableTap()
        target?.invalidateTapAndSource()
        target?.invalidateTimers()
        target?.removeObservers()
        target?.releaseCallbackContext()
        publishStatus()
        target?.stopRunLoop()
        target?.teardownDidComplete()
    }

    @discardableResult
    private func scheduleTeardown() -> Bool {
        // Callers only invoke this for a terminal shouldRemoveTap/closed result. Settling
        // failures legitimately land in .off but still own an installed tap, timers,
        // observers and callback context that must be removed. A still-valid draining
        // state never reaches this path; its terminal event/close or deadline does.
        guard !teardownScheduled,
              !teardownCompleted,
              engine.phase == .closed || engine.phase == .off,
              let dependencies else {
            return false
        }
        teardownScheduled = true
        dependencies.scheduleTeardown { [weak self] in
            self?.completeTeardown()
        }
        return true
    }
}
