import Foundation
import RoutingCore

/// Platform-neutral event shape used by the adapter seam. The AppKit/CoreGraphics
/// fixture maps one native callback into this value; tests use the same value.
public struct AdapterEvent: Equatable, Sendable {
    public enum Kind: Equatable, Sendable {
        case keyDown
        case keyUp
        case flagsChanged
        case tapDisabledByTimeout
        case tapDisabledByUserInput
        case unsupported
    }

    public var kind: Kind
    public var keyCode: UInt16
    public var rawModifiers: UInt64
    public var isRepeat: Bool

    public init(
        kind: Kind,
        keyCode: UInt16 = 0,
        rawModifiers: UInt64 = 0,
        isRepeat: Bool = false
    ) {
        self.kind = kind
        self.keyCode = keyCode
        self.rawModifiers = rawModifiers
        self.isRepeat = isRepeat
    }

    /// Nil for disabled notifications and unsupported native events, which pass through
    /// without an engine decision.
    public var keyEvent: KeyEvent? {
        switch kind {
        case .keyDown:
            return KeyEvent(kind: .keyDown, keyCode: keyCode, rawModifiers: rawModifiers, isRepeat: isRepeat)
        case .keyUp:
            return KeyEvent(kind: .keyUp, keyCode: keyCode, rawModifiers: rawModifiers, isRepeat: isRepeat)
        case .flagsChanged:
            return KeyEvent(kind: .flagsChanged, keyCode: keyCode, rawModifiers: rawModifiers, isRepeat: isRepeat)
        case .tapDisabledByTimeout:
            return KeyEvent(kind: .tapDisabledByTimeout, keyCode: 0)
        case .tapDisabledByUserInput:
            return KeyEvent(kind: .tapDisabledByUserInput, keyCode: 0)
        case .unsupported:
            return nil
        }
    }
}

public protocol AdapterDependencies: AnyObject {
    var uptime: TimeInterval { get }
    func monotonicNanos() -> UInt64
    func currentGate() -> GateContext
    func scheduleTeardown(_ action: @escaping () -> Void)
    func publish(_ snapshot: StatusSnapshot)
}

/// The product of the callback decision. `event == nil` means consume (native layer
/// returns nil); a non-nil event is the original token and passes through.
public struct AdapterCallbackResult<Event> {
    public var event: Event?
    public var decision: RoutingDecision?
    public var budget: CallbackBudgetResult?
    public var teardownScheduled: Bool

    public init(
        event: Event?,
        decision: RoutingDecision? = nil,
        budget: CallbackBudgetResult? = nil,
        teardownScheduled: Bool = false
    ) {
        self.event = event
        self.decision = decision
        self.budget = budget
        self.teardownScheduled = teardownScheduled
    }
}

/// Native-side operations the coordinator drives. The production fixture implements
/// these on its tap thread; tests use a recorder fake.
public protocol AdapterLifecycleTarget: AnyObject {
    func enableTap()
    func disableTap()
    func invalidateTapAndSource()
    func invalidateTimers()
    func removeObservers()
    func releaseCallbackContext()
    func stopRunLoop()
    func teardownDidComplete()
}
