import Foundation

/// Pure decision state machine. It never creates, posts, replays or injects events and
/// never formats a raw event. The native adapter owns the tap, its thread and the clock.
public struct RoutingEngine {
    public let configuration: RoutingConfiguration

    public private(set) var phase: Phase = .off
    public private(set) var mode: ArmMode?
    public private(set) var unavailableReason: UnavailableReason?
    public private(set) var stopReason: StopReason?
    public private(set) var invalidReason: InvalidReason?
    public private(set) var counters = Counters()
    public private(set) var actionCount = 0
    public private(set) var lastActionID: String?
    public private(set) var installedAt: TimeInterval?
    public private(set) var drainDeadline: TimeInterval?

    private var buffer: TextBuffer
    private var ownedKeyCodesValue: Set<UInt16> = []
    private var sessionDeadline: TimeInterval?
    private var settleDeadline: TimeInterval?

    public init(configuration: RoutingConfiguration = .default) {
        self.configuration = configuration
        self.buffer = TextBuffer(
            perEventUTF16Limit: configuration.perEventUTF16Limit,
            retainedUTF16Limit: configuration.retainedUTF16Limit
        )
    }

    public var registeredBindings: [ShortcutBinding] {
        configuration.validBindings
    }

    public var bindingIssues: [BindingIssue] {
        configuration.bindingIssues
    }

    public var ownedKeyCodes: Set<UInt16> {
        ownedKeyCodesValue
    }

    public var retainedText: String {
        buffer.text
    }

    public var textWasTruncated: Bool {
        buffer.isTruncated
    }

    // MARK: - Arm lifecycle

    public mutating func beginArm(
        mode: ArmMode,
        gate: GateContext,
        heldNonModifierKeys: Bool,
        now: TimeInterval
    ) -> ArmRequest {
        guard phase == .off else {
            return .rejected(.alreadyActive)
        }

        if let reason = armRejection(gate: gate, heldNonModifierKeys: heldNonModifierKeys) {
            unavailableReason = reason
            phase = .off
            return .rejected(reason)
        }

        self.mode = mode
        unavailableReason = nil
        stopReason = nil
        invalidReason = nil
        counters = Counters()
        actionCount = 0
        lastActionID = nil
        ownedKeyCodesValue = []
        installedAt = nil
        sessionDeadline = nil
        settleDeadline = nil
        drainDeadline = nil
        buffer = TextBuffer(
            perEventUTF16Limit: configuration.perEventUTF16Limit,
            retainedUTF16Limit: configuration.retainedUTF16Limit
        )
        phase = .installing
        return .installTap
    }

    @discardableResult
    public mutating func tapInstalled(at now: TimeInterval) -> Bool {
        guard phase == .installing else { return false }
        installedAt = now
        sessionDeadline = now + configuration.maxSessionDuration
        settleDeadline = now + configuration.settleInterval
        phase = .settling
        return true
    }

    public mutating func tapInstallationFailed(_ reason: UnavailableReason) {
        guard phase == .installing || phase == .off else { return }
        phase = .off
        mode = nil
        unavailableReason = reason
        installedAt = nil
        sessionDeadline = nil
        settleDeadline = nil
        drainDeadline = nil
        buffer.clear()
    }

    // MARK: - Clock ticks

    public mutating func tick(now: TimeInterval, gate: GateContext) -> TickResult {
        let previous = phase

        switch phase {
        case .settling:
            if let sessionDeadline, now >= sessionDeadline {
                phase = .off
                mode = nil
                unavailableReason = .lifetimeExpiredWhileSettling
                stopReason = .lifetimeExpired
                installedAt = nil
                self.sessionDeadline = nil
                settleDeadline = nil
                drainDeadline = nil
                return TickResult(
                    phaseChanged: true,
                    shouldRemoveTap: true,
                    stopReason: .lifetimeExpired,
                    unavailableReason: .lifetimeExpiredWhileSettling
                )
            }
            if let settleDeadlineValue = settleDeadline, now >= settleDeadlineValue {
                if let failure = firstGateFailure(gate) {
                    phase = .off
                    mode = nil
                    unavailableReason = .preconditionsLostWhileSettling
                    stopReason = stopReason(for: failure)
                    installedAt = nil
                    sessionDeadline = nil
                    settleDeadline = nil
                    drainDeadline = nil
                    return TickResult(
                        phaseChanged: true,
                        shouldRemoveTap: true,
                        stopReason: stopReason,
                        unavailableReason: .preconditionsLostWhileSettling
                    )
                }
                phase = .armed
                settleDeadline = nil
                return TickResult(phaseChanged: true)
            }

        case .armed:
            if let sessionDeadline, now >= sessionDeadline {
                return finishLifetime()
            }
            if let failure = firstGateFailure(gate) {
                return finishNonViableStop(stopReason(for: failure))
            }

        case .draining:
            if let drainDeadline, now >= drainDeadline {
                return finishDrainDeadline()
            }

        case .off, .installing, .closed:
            break
        }

        return TickResult(phaseChanged: phase != previous)
    }

    // MARK: - Event decisions

    public mutating func handle(
        _ event: KeyEvent,
        gate: GateContext,
        now: TimeInterval,
        unicode: () -> String?
    ) -> RoutingDecision {
        switch event.kind {
        case .tapDisabledByTimeout:
            return handleDisabledTap(stop: .tapDisabledByTimeout)
        case .tapDisabledByUserInput:
            return handleDisabledTap(stop: .tapDisabledByUserInput)
        case .keyDown, .keyUp, .flagsChanged:
            break
        }

        switch phase {
        case .off, .installing, .closed:
            counters.passed += 1
            return RoutingDecision(disposition: .pass, eventClass: .passThrough)

        case .settling:
            if let failure = firstGateFailure(gate) {
                failArm(stop: stopReason(for: failure))
                counters.passed += 1
                return RoutingDecision(
                    disposition: .pass,
                    eventClass: .settlingPassThrough,
                    stopReason: stopReason,
                    shouldRemoveTap: true
                )
            }
            if event.kind == .keyDown, event.isRepeat, !KeyPolicy.isModifierKey(event.keyCode) {
                counters.passed += 1
                counters.settledInputsPassed += 1
                counters.repeatWithoutOwnership += 1
                invalidReason = .repeatWithoutOwnedDown
                failArm(stop: .repeatWithoutOwnedDown)
                return RoutingDecision(
                    disposition: .pass,
                    eventClass: .settlingPassThrough,
                    stopReason: .repeatWithoutOwnedDown,
                    invalidReason: .repeatWithoutOwnedDown,
                    shouldRemoveTap: true
                )
            }
            counters.passed += 1
            counters.settledInputsPassed += 1
            return RoutingDecision(disposition: .pass, eventClass: .settlingPassThrough)

        case .draining:
            return handleDraining(event, now: now)

        case .armed:
            return handleArmed(event, gate: gate, now: now, unicode: unicode)
        }
    }

    private mutating func handleArmed(
        _ event: KeyEvent,
        gate: GateContext,
        now: TimeInterval,
        unicode: () -> String?
    ) -> RoutingDecision {
        if event.kind == .flagsChanged {
            counters.passed += 1
            counters.modifierEvents += 1
            return RoutingDecision(disposition: .pass, eventClass: .modifierPassThrough)
        }

        if let sessionDeadline, now >= sessionDeadline {
            let finish = finishLifetime()
            counters.passed += 1
            return RoutingDecision(
                disposition: .pass,
                eventClass: .passThrough,
                stopReason: finish.stopReason,
                invalidReason: finish.invalidReason,
                shouldRemoveTap: finish.shouldRemoveTap
            )
        }

        if let failure = firstGateFailure(gate) {
            let finish = finishNonViableStop(stopReason(for: failure))
            counters.passed += 1
            return RoutingDecision(
                disposition: .pass,
                eventClass: .passThrough,
                stopReason: finish.stopReason,
                invalidReason: finish.invalidReason,
                shouldRemoveTap: finish.shouldRemoveTap
            )
        }

        if event.kind == .keyDown,
           !event.isRepeat,
           event.keyCode == KeyPolicy.escapeKeyCode {
            ownedKeyCodesValue.insert(event.keyCode)
            counters.consumed += 1
            counters.selectedKeyDowns += 1
            let result = beginDrain(reason: .emergencyEscape, now: now)
            return RoutingDecision(
                disposition: .consume,
                eventClass: .emergencyStop,
                stopReason: .emergencyEscape,
                invalidReason: result.invalidReason,
                shouldRemoveTap: result.shouldRemoveTap
            )
        }

        if event.kind == .keyUp {
            if ownedKeyCodesValue.remove(event.keyCode) != nil {
                counters.consumed += 1
                counters.selectedKeyUps += 1
                return RoutingDecision(disposition: .consume, eventClass: .ownedKeyUp)
            }
            counters.passed += 1
            return RoutingDecision(disposition: .pass, eventClass: .passThrough)
        }

        if event.isRepeat {
            if ownedKeyCodesValue.contains(event.keyCode) {
                counters.consumed += 1
                counters.repeatsConsumed += 1
                return RoutingDecision(disposition: .consume, eventClass: .ownedRepeat)
            }
            counters.passed += 1
            counters.repeatWithoutOwnership += 1
            stopReason = .repeatWithoutOwnedDown
            invalidReason = .repeatWithoutOwnedDown
            phase = .closed
            drainDeadline = nil
            buffer.clear()
            return RoutingDecision(
                disposition: .pass,
                eventClass: .unownedRepeatInvalid,
                stopReason: .repeatWithoutOwnedDown,
                invalidReason: .repeatWithoutOwnedDown,
                shouldRemoveTap: true
            )
        }

        // A registered chord wins over text capture.
        if let binding = registeredBindings.first(where: {
            $0.keyCode == event.keyCode && $0.modifiers == event.modifiers
        }) {
            ownedKeyCodesValue.insert(event.keyCode)
            counters.consumed += 1
            counters.selectedKeyDowns += 1
            counters.actions += 1
            actionCount += 1
            lastActionID = binding.actionID
            return RoutingDecision(
                disposition: .consume,
                eventClass: .shortcutAction,
                actionID: binding.actionID
            )
        }

        guard mode == .text else {
            counters.passed += 1
            return RoutingDecision(disposition: .pass, eventClass: .passThrough)
        }

        // Unregistered command/control/option combinations never enter text policy,
        // including on control and navigation keys (for example cmd+Backspace).
        if event.modifiers.hasChordModifierBeyondShift() {
            counters.passed += 1
            return RoutingDecision(disposition: .pass, eventClass: .passThrough)
        }

        switch KeyPolicy.role(for: event.keyCode) {
        case .backspace:
            counters.controlEvents += 1
            counters.consumed += 1
            counters.selectedKeyDowns += 1
            ownedKeyCodesValue.insert(event.keyCode)
            let changed = buffer.removePreviousGrapheme()
            return RoutingDecision(
                disposition: .consume,
                eventClass: .textControl,
                textChanged: changed
            )

        case .forwardDelete, .returnKey, .tab:
            counters.controlEvents += 1
            counters.consumed += 1
            counters.selectedKeyDowns += 1
            ownedKeyCodesValue.insert(event.keyCode)
            if event.keyCode == KeyPolicy.forwardDeleteKeyCode {
                _ = buffer.forwardDeleteAtEnd()
            }
            return RoutingDecision(disposition: .consume, eventClass: .textControl)

        case .navigation:
            counters.navigationEvents += 1
            counters.consumed += 1
            counters.selectedKeyDowns += 1
            ownedKeyCodesValue.insert(event.keyCode)
            return RoutingDecision(disposition: .consume, eventClass: .navigationIgnored)

        case .printable:
            counters.unicodeExtractions += 1
            let supplied = unicode()
            guard let supplied, !supplied.isEmpty else {
                counters.emptyUnicodePasses += 1
                counters.passed += 1
                return RoutingDecision(disposition: .pass, eventClass: .passThrough)
            }
            let appendResult = buffer.append(supplied)
            counters.textEvents += 1
            counters.consumed += 1
            counters.selectedKeyDowns += 1
            ownedKeyCodesValue.insert(event.keyCode)
            return RoutingDecision(
                disposition: .consume,
                eventClass: .textInput,
                appendResult: appendResult,
                textChanged: appendResult.appendedUTF16 > 0
            )

        case .escape:
            // Escape initial-down is handled above; repeats fall through to the repeat branch.
            counters.passed += 1
            return RoutingDecision(disposition: .pass, eventClass: .passThrough)

        case .modifier, .unknown:
            counters.passed += 1
            return RoutingDecision(disposition: .pass, eventClass: .passThrough)
        }
    }

    private mutating func handleDraining(
        _ event: KeyEvent,
        now: TimeInterval
    ) -> RoutingDecision {
        if let drainDeadline, now >= drainDeadline {
            let finish = finishDrainDeadline()
            return RoutingDecision(
                disposition: .pass,
                eventClass: .drainPassThrough,
                stopReason: finish.stopReason,
                invalidReason: finish.invalidReason,
                shouldRemoveTap: finish.shouldRemoveTap
            )
        }

        if event.kind == .flagsChanged {
            counters.passed += 1
            counters.modifierEvents += 1
            return RoutingDecision(disposition: .pass, eventClass: .modifierPassThrough)
        }

        if event.kind == .keyUp {
            if ownedKeyCodesValue.remove(event.keyCode) != nil {
                counters.consumed += 1
                counters.selectedKeyUps += 1
                counters.drainOwnedKeyUps += 1
                if ownedKeyCodesValue.isEmpty {
                    phase = .closed
                    stopReason = .drainComplete
                    drainDeadline = nil
                    buffer.clear()
                    return RoutingDecision(
                        disposition: .consume,
                        eventClass: .drainKeyUp,
                        stopReason: .drainComplete,
                        shouldRemoveTap: true
                    )
                }
                return RoutingDecision(disposition: .consume, eventClass: .drainKeyUp)
            }
            counters.passed += 1
            return RoutingDecision(disposition: .pass, eventClass: .drainPassThrough)
        }

        if event.kind == .keyDown, event.isRepeat, ownedKeyCodesValue.contains(event.keyCode) {
            counters.consumed += 1
            counters.drainRepeatsConsumed += 1
            return RoutingDecision(disposition: .consume, eventClass: .drainRepeat)
        }

        counters.passed += 1
        return RoutingDecision(disposition: .pass, eventClass: .drainPassThrough)
    }

    private mutating func handleDisabledTap(stop: StopReason) -> RoutingDecision {
        guard phase == .armed || phase == .settling || phase == .draining || phase == .installing else {
            return RoutingDecision(disposition: .pass, eventClass: .disabledTap)
        }
        buffer.clear()
        let pending = !ownedKeyCodesValue.isEmpty
        if invalidReason == nil {
            invalidReason = pending ? .pendingOwnershipAtNonViableStop : .caseInterrupted
        }
        stopReason = stop
        phase = .closed
        drainDeadline = nil
        counters.passed += 1
        return RoutingDecision(
            disposition: .pass,
            eventClass: .disabledTap,
            stopReason: stop,
            invalidReason: invalidReason,
            shouldRemoveTap: true
        )
    }

    // MARK: - Disarm and teardown

    public mutating func disarm(reason: StopReason, now: TimeInterval) -> DisarmResult {
        switch phase {
        case .draining:
            if isNonViableStop(reason) {
                buffer.clear()
                stopReason = reason
                if invalidReason == nil {
                    invalidReason = ownedKeyCodesValue.isEmpty
                        ? .caseInterrupted
                        : .pendingOwnershipAtNonViableStop
                }
                phase = .closed
                drainDeadline = nil
                return DisarmResult(
                    phase: .closed,
                    shouldRemoveTap: true,
                    stopReason: reason,
                    invalidReason: invalidReason
                )
            }
            return DisarmResult(
                phase: .draining,
                shouldRemoveTap: false,
                stopReason: stopReason ?? reason,
                invalidReason: invalidReason
            )
        case .closed:
            return DisarmResult(
                phase: .closed,
                shouldRemoveTap: true,
                stopReason: stopReason ?? reason,
                invalidReason: invalidReason
            )
        case .off:
            return DisarmResult(phase: .off, shouldRemoveTap: false, stopReason: reason)
        case .installing:
            buffer.clear()
            stopReason = reason
            phase = .closed
            drainDeadline = nil
            return DisarmResult(phase: .closed, shouldRemoveTap: true, stopReason: reason)
        case .settling, .armed:
            if isNonViableStop(reason) {
                return finishImmediate(reason: reason)
            }
            return beginDrain(reason: reason, now: now)
        }
    }

    private mutating func beginDrain(reason: StopReason, now: TimeInterval) -> DisarmResult {
        buffer.clear()
        stopReason = reason
        if let sessionDeadline, !ownedKeyCodesValue.isEmpty {
            let deadline = min(now + configuration.drainDuration, sessionDeadline)
            if deadline > now {
                phase = .draining
                drainDeadline = deadline
                return DisarmResult(
                    phase: .draining,
                    shouldRemoveTap: false,
                    stopReason: reason,
                    invalidReason: invalidReason
                )
            }
        }

        phase = .closed
        drainDeadline = nil
        if !ownedKeyCodesValue.isEmpty, invalidReason == nil {
            invalidReason = reason == .lifetimeExpired
                ? .pendingOwnershipAtLifetimeExpiry
                : .pendingOwnershipAtDrainDeadline
        }
        return DisarmResult(
            phase: .closed,
            shouldRemoveTap: true,
            stopReason: reason,
            invalidReason: invalidReason
        )
    }

    private mutating func finishImmediate(reason: StopReason) -> DisarmResult {
        buffer.clear()
        stopReason = reason
        if invalidReason == nil {
            if reason == .lifetimeExpired {
                if !ownedKeyCodesValue.isEmpty {
                    invalidReason = .pendingOwnershipAtLifetimeExpiry
                }
            } else {
                invalidReason = ownedKeyCodesValue.isEmpty
                    ? .caseInterrupted
                    : .pendingOwnershipAtNonViableStop
            }
        }
        phase = .closed
        drainDeadline = nil
        return DisarmResult(
            phase: .closed,
            shouldRemoveTap: true,
            stopReason: reason,
            invalidReason: invalidReason
        )
    }

    private func isNonViableStop(_ reason: StopReason) -> Bool {
        switch reason {
        case .foregroundChanged, .permissionLost, .secureInputBegan,
             .sessionResigned, .systemSleep,
             .tapDisabledByTimeout, .tapDisabledByUserInput,
             .adapterError, .lifetimeExpired, .tapReturnedNil:
            return true
        default:
            return false
        }
    }

    // MARK: - Callback budget

    public mutating func noteCallbackDuration(
        nanoseconds: UInt64,
        now: TimeInterval
    ) -> CallbackBudgetResult {
        counters.callbackSamples += 1
        counters.maxCallbackNanoseconds = max(counters.maxCallbackNanoseconds, nanoseconds)

        guard nanoseconds > configuration.callbackBudgetNanoseconds else {
            return CallbackBudgetResult(exceeded: false)
        }

        counters.callbackBudgetViolations += 1
        if invalidReason == nil {
            invalidReason = .callbackBudgetExceeded
        }

        guard phase == .armed || phase == .settling || phase == .installing else {
            return CallbackBudgetResult(
                exceeded: true,
                shouldRemoveTap: phase == .closed,
                stopReason: stopReason,
                invalidReason: invalidReason
            )
        }

        let result = disarm(reason: .callbackBudgetExceeded, now: now)
        return CallbackBudgetResult(
            exceeded: true,
            shouldRemoveTap: result.shouldRemoveTap,
            stopReason: .callbackBudgetExceeded,
            invalidReason: invalidReason
        )
    }

    // MARK: - Status

    public func status(now: TimeInterval) -> StatusSnapshot {
        let active = phase == .installing || phase == .settling || phase == .armed || phase == .draining
        let remaining: Double
        if active, let sessionDeadline {
            remaining = max(0, sessionDeadline - now)
        } else {
            remaining = 0
        }

        var seenActions: Set<String> = []
        var actionIDs: [String] = []
        for binding in registeredBindings where seenActions.insert(binding.actionID).inserted {
            actionIDs.append(binding.actionID)
        }

        return StatusSnapshot(
            phase: phase,
            mode: mode,
            unavailableReason: unavailableReason,
            stopReason: stopReason,
            invalidReason: invalidReason,
            text: buffer.text,
            textTruncated: buffer.isTruncated,
            ownedKeyCodes: ownedKeyCodesValue.sorted(),
            actionCount: actionCount,
            lastActionID: lastActionID,
            counters: counters,
            remainingSessionSeconds: remaining,
            drainRemainingSeconds: drainDeadline.map { max(0, $0 - now) },
            sessionDeadline: sessionDeadline,
            registeredActionIDs: actionIDs
        )
    }

    // MARK: - Helpers

    private func armRejection(gate: GateContext, heldNonModifierKeys: Bool) -> UnavailableReason? {
        if configuration.allowedPID <= 0 { return .allowedPIDMissing }
        if gate.foregroundPID != configuration.allowedPID { return .foregroundMismatch }
        if !gate.permissionsAvailable { return .permissionsUnavailable }
        if gate.secureInputEnabled { return .secureInputEnabled }
        if heldNonModifierKeys { return .heldNonModifierKeys }
        return nil
    }

    private func firstGateFailure(_ gate: GateContext) -> GateFailure? {
        if configuration.allowedPID <= 0 { return .allowedPIDMissing }
        if gate.foregroundPID != configuration.allowedPID { return .foregroundMismatch }
        if !gate.permissionsAvailable { return .permissionsUnavailable }
        if gate.secureInputEnabled { return .secureInputEnabled }
        return nil
    }

    private func stopReason(for failure: GateFailure) -> StopReason {
        switch failure {
        case .allowedPIDMissing, .foregroundMismatch:
            return .foregroundChanged
        case .permissionsUnavailable:
            return .permissionLost
        case .secureInputEnabled:
            return .secureInputBegan
        }
    }

    private mutating func failArm(stop: StopReason) {
        buffer.clear()
        phase = .off
        mode = nil
        unavailableReason = .preconditionsLostWhileSettling
        stopReason = stop
        installedAt = nil
        sessionDeadline = nil
        settleDeadline = nil
        drainDeadline = nil
    }

    private mutating func finishNonViableStop(_ reason: StopReason) -> TickResult {
        buffer.clear()
        stopReason = reason
        if invalidReason == nil {
            invalidReason = ownedKeyCodesValue.isEmpty
                ? .caseInterrupted
                : .pendingOwnershipAtNonViableStop
        }
        phase = .closed
        drainDeadline = nil
        return TickResult(
            phaseChanged: true,
            shouldRemoveTap: true,
            stopReason: reason,
            invalidReason: invalidReason
        )
    }

    private mutating func finishLifetime() -> TickResult {
        buffer.clear()
        stopReason = .lifetimeExpired
        if !ownedKeyCodesValue.isEmpty, invalidReason == nil {
            invalidReason = .pendingOwnershipAtLifetimeExpiry
        }
        phase = .closed
        drainDeadline = nil
        return TickResult(
            phaseChanged: true,
            shouldRemoveTap: true,
            stopReason: .lifetimeExpired,
            invalidReason: invalidReason
        )
    }

    private mutating func finishDrainDeadline() -> TickResult {
        buffer.clear()
        let pending = !ownedKeyCodesValue.isEmpty
        stopReason = pending ? .drainDeadlinePending : .drainComplete
        if pending, invalidReason == nil {
            invalidReason = .pendingOwnershipAtDrainDeadline
        }
        phase = .closed
        drainDeadline = nil
        return TickResult(
            phaseChanged: true,
            shouldRemoveTap: true,
            stopReason: stopReason,
            invalidReason: invalidReason
        )
    }
}
