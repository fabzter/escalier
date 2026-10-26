import Foundation

// MARK: - Modifiers

/// Only the four chord-relevant modifiers. Caps Lock, Fn, numeric-pad, help,
/// device-left/right and unknown flag bits are deliberately excluded.
public struct ModifierSet: OptionSet, Hashable, Sendable {
    public let rawValue: UInt64

    public init(rawValue: UInt64) {
        self.rawValue = rawValue
    }

    public static let command = ModifierSet(rawValue: 1 << 0)
    public static let shift = ModifierSet(rawValue: 1 << 1)
    public static let control = ModifierSet(rawValue: 1 << 2)
    public static let option = ModifierSet(rawValue: 1 << 3)

    public static let relevant: ModifierSet = [.command, .shift, .control, .option]
    public static let none: ModifierSet = []

    /// True when a chord demands a modifier whose delivery cannot be suppressed.
    public func hasChordModifierBeyondShift() -> Bool {
        !intersection([.command, .control, .option]).isEmpty
    }
}

/// Raw `CGEventFlags` bit constants, kept here so the pure core never imports CoreGraphics.
/// The high bits are the documented public flags; the low byte is device-dependent
/// left/right information. Matching extracts only the four relevant bits.
public enum RawModifierBits {
    public static let capsLock: UInt64 = 1 << 16
    public static let shift: UInt64 = 1 << 17
    public static let control: UInt64 = 1 << 18
    public static let option: UInt64 = 1 << 19
    public static let command: UInt64 = 1 << 20
    public static let numericPad: UInt64 = 1 << 21
    public static let help: UInt64 = 1 << 22
    public static let function: UInt64 = 1 << 23
    public static let nonCoalesced: UInt64 = 1 << 8

    public static let deviceLeftControl: UInt64 = 0x0000_0001
    public static let deviceLeftShift: UInt64 = 0x0000_0002
    public static let deviceRightShift: UInt64 = 0x0000_0004
    public static let deviceLeftCommand: UInt64 = 0x0000_0008
    public static let deviceRightCommand: UInt64 = 0x0000_0010
    public static let deviceLeftOption: UInt64 = 0x0000_0020
    public static let deviceRightOption: UInt64 = 0x0000_0040
    public static let deviceRightControl: UInt64 = 0x0000_2000

    public static let ignoredMask: UInt64 =
        0x0000_00FF | capsLock | numericPad | help | function | nonCoalesced

    public static func normalize(_ raw: UInt64) -> ModifierSet {
        var result: ModifierSet = []
        if raw & command != 0 { result.insert(.command) }
        if raw & shift != 0 { result.insert(.shift) }
        if raw & control != 0 { result.insert(.control) }
        if raw & option != 0 { result.insert(.option) }
        return result
    }
}

// MARK: - Events and gates

public struct KeyEvent: Equatable, Sendable {
    public enum Kind: String, Equatable, Sendable {
        case keyDown
        case keyUp
        case flagsChanged
        case tapDisabledByTimeout
        case tapDisabledByUserInput
    }

    public var kind: Kind
    public var keyCode: UInt16
    public var rawModifiers: UInt64
    public var isRepeat: Bool

    public init(kind: Kind, keyCode: UInt16, rawModifiers: UInt64 = 0, isRepeat: Bool = false) {
        self.kind = kind
        self.keyCode = keyCode
        self.rawModifiers = rawModifiers
        self.isRepeat = isRepeat
    }

    public var modifiers: ModifierSet {
        RawModifierBits.normalize(rawModifiers)
    }
}

/// Prompt-free observations taken by the native adapter. The pure core makes the decision.
public struct GateContext: Equatable, Sendable {
    public var foregroundPID: Int32?
    public var permissionsAvailable: Bool
    public var secureInputEnabled: Bool

    public init(
        foregroundPID: Int32?,
        permissionsAvailable: Bool = true,
        secureInputEnabled: Bool = false
    ) {
        self.foregroundPID = foregroundPID
        self.permissionsAvailable = permissionsAvailable
        self.secureInputEnabled = secureInputEnabled
    }

    public func failures(allowedPID: Int32) -> [GateFailure] {
        var result: [GateFailure] = []
        if allowedPID <= 0 { result.append(.allowedPIDMissing) }
        if foregroundPID != allowedPID { result.append(.foregroundMismatch) }
        if !permissionsAvailable { result.append(.permissionsUnavailable) }
        if secureInputEnabled { result.append(.secureInputEnabled) }
        return result
    }
}

public enum GateFailure: String, Equatable, Sendable {
    case allowedPIDMissing
    case foregroundMismatch
    case permissionsUnavailable
    case secureInputEnabled
}

// MARK: - Phase and outcomes

public enum Phase: String, Equatable, Sendable {
    case off
    case installing
    case settling
    case armed
    case draining
    case closed
}

public enum ArmMode: String, Equatable, Sendable {
    case shortcut
    case text
}

public enum UnavailableReason: String, Equatable, Sendable {
    case allowedPIDMissing
    case foregroundMismatch
    case permissionsUnavailable
    case secureInputEnabled
    case heldNonModifierKeys
    case tapInstallationFailed
    case tapReturnedNil
    case preconditionsLostWhileSettling
    case lifetimeExpiredWhileSettling
    case alreadyActive
    case adapterError
}

public enum StopReason: String, Equatable, Sendable {
    case userStopped
    case emergencyEscape
    case lifetimeExpired
    case foregroundChanged
    case permissionLost
    case secureInputBegan
    case sessionResigned
    case systemSleep
    case tapDisabledByTimeout
    case tapDisabledByUserInput
    case callbackBudgetExceeded
    case adapterError
    case repeatWithoutOwnedDown
    case drainComplete
    case drainDeadlinePending
    case tapReturnedNil
}

public enum InvalidReason: String, Equatable, Sendable {
    case pendingOwnershipAtDrainDeadline
    case pendingOwnershipAtLifetimeExpiry
    case pendingOwnershipAtNonViableStop
    case caseInterrupted
    case repeatWithoutOwnedDown
    case callbackBudgetExceeded
    case armPreconditionsLost
}

public enum Disposition: String, Equatable, Sendable {
    case pass
    case consume
}

public enum EventClass: String, Equatable, Sendable {
    case passThrough
    case settlingPassThrough
    case drainPassThrough
    case unavailablePassThrough
    case shortcutAction
    case textInput
    case textControl
    case navigationIgnored
    case modifierPassThrough
    case emergencyStop
    case ownedKeyUp
    case ownedRepeat
    case drainKeyUp
    case drainRepeat
    case unownedRepeatInvalid
    case disabledTap
}

public struct TextAppendResult: Equatable, Sendable {
    public var appendedUTF16: Int
    public var eventTruncated: Bool
    public var bufferOverflowed: Bool
    public var textUTF16Count: Int

    public init(
        appendedUTF16: Int,
        eventTruncated: Bool,
        bufferOverflowed: Bool,
        textUTF16Count: Int
    ) {
        self.appendedUTF16 = appendedUTF16
        self.eventTruncated = eventTruncated
        self.bufferOverflowed = bufferOverflowed
        self.textUTF16Count = textUTF16Count
    }
}

public struct RoutingDecision: Equatable, Sendable {
    public var disposition: Disposition
    public var eventClass: EventClass
    public var actionID: String?
    public var appendResult: TextAppendResult?
    public var textChanged: Bool
    public var stopReason: StopReason?
    public var invalidReason: InvalidReason?
    public var shouldRemoveTap: Bool

    public init(
        disposition: Disposition,
        eventClass: EventClass,
        actionID: String? = nil,
        appendResult: TextAppendResult? = nil,
        textChanged: Bool = false,
        stopReason: StopReason? = nil,
        invalidReason: InvalidReason? = nil,
        shouldRemoveTap: Bool = false
    ) {
        self.disposition = disposition
        self.eventClass = eventClass
        self.actionID = actionID
        self.appendResult = appendResult
        self.textChanged = textChanged
        self.stopReason = stopReason
        self.invalidReason = invalidReason
        self.shouldRemoveTap = shouldRemoveTap
    }
}

public enum ArmRequest: Equatable, Sendable {
    case installTap
    case rejected(UnavailableReason)
}

public struct TickResult: Equatable, Sendable {
    public var phaseChanged: Bool
    public var shouldRemoveTap: Bool
    public var stopReason: StopReason?
    public var invalidReason: InvalidReason?
    public var unavailableReason: UnavailableReason?

    public init(
        phaseChanged: Bool = false,
        shouldRemoveTap: Bool = false,
        stopReason: StopReason? = nil,
        invalidReason: InvalidReason? = nil,
        unavailableReason: UnavailableReason? = nil
    ) {
        self.phaseChanged = phaseChanged
        self.shouldRemoveTap = shouldRemoveTap
        self.stopReason = stopReason
        self.invalidReason = invalidReason
        self.unavailableReason = unavailableReason
    }
}

public struct DisarmResult: Equatable, Sendable {
    public var phase: Phase
    public var shouldRemoveTap: Bool
    public var stopReason: StopReason
    public var invalidReason: InvalidReason?

    public init(
        phase: Phase,
        shouldRemoveTap: Bool,
        stopReason: StopReason,
        invalidReason: InvalidReason? = nil
    ) {
        self.phase = phase
        self.shouldRemoveTap = shouldRemoveTap
        self.stopReason = stopReason
        self.invalidReason = invalidReason
    }
}

public struct CallbackBudgetResult: Equatable, Sendable {
    public var exceeded: Bool
    public var shouldRemoveTap: Bool
    public var stopReason: StopReason?
    public var invalidReason: InvalidReason?

    public init(
        exceeded: Bool,
        shouldRemoveTap: Bool = false,
        stopReason: StopReason? = nil,
        invalidReason: InvalidReason? = nil
    ) {
        self.exceeded = exceeded
        self.shouldRemoveTap = shouldRemoveTap
        self.stopReason = stopReason
        self.invalidReason = invalidReason
    }
}

// MARK: - Shortcut bindings

public enum BindingIssue: Equatable, Sendable {
    case modifierOnlyKey(keyCode: UInt16)
    case reservedKey(keyCode: UInt16)
    case emptyActionID(keyCode: UInt16, modifiers: ModifierSet)
    case duplicateChord(keyCode: UInt16, modifiers: ModifierSet)
}

public struct ShortcutBinding: Hashable, Sendable {
    public var keyCode: UInt16
    public var modifiers: ModifierSet
    public var actionID: String

    public init(keyCode: UInt16, modifiers: ModifierSet, actionID: String) {
        self.keyCode = keyCode
        self.modifiers = modifiers
        self.actionID = actionID
    }

    public static let fixtureDefault = ShortcutBinding(
        keyCode: 40, // physical K
        modifiers: [.command, .shift],
        actionID: "fixture-action"
    )

    /// The chord as a stable, non-event-describing label for counters/reporting.
    public var chordLabel: String {
        var parts: [String] = []
        if modifiers.contains(.control) { parts.append("ctrl") }
        if modifiers.contains(.option) { parts.append("opt") }
        if modifiers.contains(.shift) { parts.append("shift") }
        if modifiers.contains(.command) { parts.append("cmd") }
        parts.append("key\(keyCode)")
        return parts.joined(separator: "+")
    }
}

// MARK: - Configuration and counters

public struct RoutingConfiguration: Equatable, Sendable {
    public var allowedPID: Int32
    public var bindings: [ShortcutBinding]
    public var settleInterval: TimeInterval
    public var maxSessionDuration: TimeInterval
    public var drainDuration: TimeInterval
    public var perEventUTF16Limit: Int
    public var retainedUTF16Limit: Int
    public var callbackBudgetNanoseconds: UInt64
    public var uiReadInterval: TimeInterval

    public init(
        allowedPID: Int32 = 0,
        bindings: [ShortcutBinding] = [.fixtureDefault],
        settleInterval: TimeInterval = 0.250,
        maxSessionDuration: TimeInterval = 30.0,
        drainDuration: TimeInterval = 1.5,
        perEventUTF16Limit: Int = 128,
        retainedUTF16Limit: Int = 1024,
        callbackBudgetNanoseconds: UInt64 = 2_000_000,
        uiReadInterval: TimeInterval = 0.1
    ) {
        self.allowedPID = allowedPID
        self.bindings = bindings
        self.settleInterval = settleInterval
        self.maxSessionDuration = maxSessionDuration
        self.drainDuration = drainDuration
        self.perEventUTF16Limit = perEventUTF16Limit
        self.retainedUTF16Limit = retainedUTF16Limit
        self.callbackBudgetNanoseconds = callbackBudgetNanoseconds
        self.uiReadInterval = uiReadInterval
    }

    public static let `default` = RoutingConfiguration()

    public var bindingIssues: [BindingIssue] {
        var issues: [BindingIssue] = []
        var seen: Set<String> = []
        for binding in bindings {
            if KeyPolicy.isModifierKey(binding.keyCode) {
                issues.append(.modifierOnlyKey(keyCode: binding.keyCode))
            }
            if binding.keyCode == KeyPolicy.escapeKeyCode {
                issues.append(.reservedKey(keyCode: binding.keyCode))
            }
            if binding.actionID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                issues.append(.emptyActionID(keyCode: binding.keyCode, modifiers: binding.modifiers))
            }
            let chord = "\(binding.keyCode):\(binding.modifiers.rawValue)"
            if seen.contains(chord) {
                issues.append(.duplicateChord(keyCode: binding.keyCode, modifiers: binding.modifiers))
            }
            seen.insert(chord)
        }
        return issues
    }

    public var validBindings: [ShortcutBinding] {
        var seenChords: Set<String> = []
        var result: [ShortcutBinding] = []
        for binding in bindings {
            let chord = "\(binding.keyCode):\(binding.modifiers.rawValue)"
            let duplicate = seenChords.contains(chord)
            seenChords.insert(chord)

            let modifierOnly = KeyPolicy.isModifierKey(binding.keyCode)
            let reserved = binding.keyCode == KeyPolicy.escapeKeyCode
            let emptyAction = binding.actionID.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            if !duplicate && !modifierOnly && !reserved && !emptyAction {
                result.append(binding)
            }
        }
        return result
    }
}

public struct Counters: Equatable, Sendable {
    public var passed: Int = 0
    public var consumed: Int = 0
    public var actions: Int = 0
    public var repeatsConsumed: Int = 0
    public var textEvents: Int = 0
    public var modifierEvents: Int = 0
    public var navigationEvents: Int = 0
    public var controlEvents: Int = 0
    public var unicodeExtractions: Int = 0
    public var emptyUnicodePasses: Int = 0
    public var repeatWithoutOwnership: Int = 0
    public var settledInputsPassed: Int = 0
    public var drainOwnedKeyUps: Int = 0
    public var drainRepeatsConsumed: Int = 0
    public var selectedKeyDowns: Int = 0
    public var selectedKeyUps: Int = 0
    public var callbackSamples: Int = 0
    public var callbackBudgetViolations: Int = 0
    public var maxCallbackNanoseconds: UInt64 = 0

    public init() {}
}

public struct StatusSnapshot: Equatable, Sendable {
    public var phase: Phase
    public var mode: ArmMode?
    public var unavailableReason: UnavailableReason?
    public var stopReason: StopReason?
    public var invalidReason: InvalidReason?
    public var text: String
    public var textTruncated: Bool
    public var ownedKeyCodes: [UInt16]
    public var actionCount: Int
    public var lastActionID: String?
    public var counters: Counters
    public var remainingSessionSeconds: Double
    public var drainRemainingSeconds: Double?
    public var sessionDeadline: TimeInterval?
    public var registeredActionIDs: [String]

    public init(
        phase: Phase = .off,
        mode: ArmMode? = nil,
        unavailableReason: UnavailableReason? = nil,
        stopReason: StopReason? = nil,
        invalidReason: InvalidReason? = nil,
        text: String = "",
        textTruncated: Bool = false,
        ownedKeyCodes: [UInt16] = [],
        actionCount: Int = 0,
        lastActionID: String? = nil,
        counters: Counters = Counters(),
        remainingSessionSeconds: Double = 0,
        drainRemainingSeconds: Double? = nil,
        sessionDeadline: TimeInterval? = nil,
        registeredActionIDs: [String] = []
    ) {
        self.phase = phase
        self.mode = mode
        self.unavailableReason = unavailableReason
        self.stopReason = stopReason
        self.invalidReason = invalidReason
        self.text = text
        self.textTruncated = textTruncated
        self.ownedKeyCodes = ownedKeyCodes
        self.actionCount = actionCount
        self.lastActionID = lastActionID
        self.counters = counters
        self.remainingSessionSeconds = remainingSessionSeconds
        self.drainRemainingSeconds = drainRemainingSeconds
        self.sessionDeadline = sessionDeadline
        self.registeredActionIDs = registeredActionIDs
    }
}
