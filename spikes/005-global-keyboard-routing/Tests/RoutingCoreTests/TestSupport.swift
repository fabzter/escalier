import XCTest
@testable import RoutingCore

enum Key {
    static let a: UInt16 = 0
    static let b: UInt16 = 11
    static let k: UInt16 = 40
    static let f1: UInt16 = 122
    static let returnKey: UInt16 = 36
    static let tab: UInt16 = 48
    static let space: UInt16 = 49
    static let backspace: UInt16 = 51
    static let escape: UInt16 = 53
    static let leftCommand: UInt16 = 55
    static let leftShift: UInt16 = 56
    static let leftOption: UInt16 = 58
    static let forwardDelete: UInt16 = 117
    static let leftArrow: UInt16 = 123
    static let rightArrow: UInt16 = 124
    static let home: UInt16 = 115
    static let pageDown: UInt16 = 121
}

let allowedPID: Int32 = 501
let settleAt: TimeInterval = 100.25

func flags(_ modifiers: ModifierSet, extra: UInt64 = 0) -> UInt64 {
    var raw: UInt64 = extra
    if modifiers.contains(.command) { raw |= RawModifierBits.command }
    if modifiers.contains(.shift) { raw |= RawModifierBits.shift }
    if modifiers.contains(.control) { raw |= RawModifierBits.control }
    if modifiers.contains(.option) { raw |= RawModifierBits.option }
    return raw
}

func allowedGate(
    pid: Int32? = allowedPID,
    permissions: Bool = true,
    secureInput: Bool = false
) -> GateContext {
    GateContext(
        foregroundPID: pid,
        permissionsAvailable: permissions,
        secureInputEnabled: secureInput
    )
}

final class UnicodeSupply {
    var calls = 0
    var value: String?

    init(_ value: String?) {
        self.value = value
    }

    func supply() -> String? {
        calls += 1
        return value
    }
}

func armedEngine(
    mode: ArmMode,
    configuration: RoutingConfiguration = RoutingConfiguration(allowedPID: allowedPID),
    file: StaticString = #filePath,
    line: UInt = #line
) -> RoutingEngine {
    var engine = RoutingEngine(configuration: configuration)
    let request = engine.beginArm(
        mode: mode,
        gate: allowedGate(),
        heldNonModifierKeys: false,
        now: 100
    )
    XCTAssertEqual(request, .installTap, file: file, line: line)
    XCTAssertTrue(engine.tapInstalled(at: 100), file: file, line: line)
    let tick = engine.tick(now: settleAt, gate: allowedGate())
    XCTAssertTrue(tick.phaseChanged, file: file, line: line)
    XCTAssertEqual(engine.phase, .armed, file: file, line: line)
    return engine
}

func down(
    _ keyCode: UInt16,
    _ modifiers: ModifierSet = [],
    extra: UInt64 = 0,
    repeat isRepeat: Bool = false
) -> KeyEvent {
    KeyEvent(kind: .keyDown, keyCode: keyCode, rawModifiers: flags(modifiers, extra: extra), isRepeat: isRepeat)
}

func up(_ keyCode: UInt16, _ modifiers: ModifierSet = [], extra: UInt64 = 0) -> KeyEvent {
    KeyEvent(kind: .keyUp, keyCode: keyCode, rawModifiers: flags(modifiers, extra: extra))
}

func modifierChanged(_ keyCode: UInt16, _ modifiers: ModifierSet) -> KeyEvent {
    KeyEvent(kind: .flagsChanged, keyCode: keyCode, rawModifiers: flags(modifiers))
}

@discardableResult
func press(
    _ engine: inout RoutingEngine,
    _ event: KeyEvent,
    gate: GateContext = allowedGate(),
    now: TimeInterval = 101,
    supply: UnicodeSupply? = nil
) -> RoutingDecision {
    engine.handle(event, gate: gate, now: now, unicode: { supply?.supply() })
}
