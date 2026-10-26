import XCTest
@testable import RoutingCore

final class ShortcutTests: XCTestCase {
    func testExactChordFiresOnceAndRepeatsAreConsumed() {
        var engine = armedEngine(mode: .shortcut)
        let supply = UnicodeSupply("k")

        let first = press(&engine, down(Key.k, [.command, .shift]), supply: supply)
        XCTAssertEqual(first.disposition, .consume)
        XCTAssertEqual(first.eventClass, .shortcutAction)
        XCTAssertEqual(first.actionID, "fixture-action")
        XCTAssertEqual(engine.actionCount, 1)
        XCTAssertEqual(engine.lastActionID, "fixture-action")
        XCTAssertEqual(engine.ownedKeyCodes, [Key.k])
        XCTAssertEqual(supply.calls, 0)

        let repeatDown = press(&engine, down(Key.k, [.command, .shift], repeat: true))
        XCTAssertEqual(repeatDown.disposition, .consume)
        XCTAssertEqual(repeatDown.eventClass, .ownedRepeat)
        XCTAssertNil(repeatDown.actionID)
        XCTAssertEqual(engine.actionCount, 1)
        XCTAssertEqual(engine.counters.repeatsConsumed, 1)

        let release = press(&engine, up(Key.k))
        XCTAssertEqual(release.disposition, .consume)
        XCTAssertEqual(release.eventClass, .ownedKeyUp)
        XCTAssertEqual(engine.ownedKeyCodes, [])
        XCTAssertEqual(engine.counters.selectedKeyUps, 1)
    }

    func testCapsLockFnNumericPadAndDeviceBitsAreIgnored() {
        var engine = armedEngine(mode: .shortcut)
        let ignored = RawModifierBits.capsLock
            | RawModifierBits.function
            | RawModifierBits.numericPad
            | RawModifierBits.help
            | RawModifierBits.nonCoalesced
            | RawModifierBits.deviceLeftCommand
            | RawModifierBits.deviceLeftShift

        let decision = press(
            &engine,
            down(Key.k, [.command, .shift], extra: ignored)
        )
        XCTAssertEqual(decision.disposition, .consume)
        XCTAssertEqual(decision.eventClass, .shortcutAction)
    }

    func testMissingOrExtraRelevantModifierDoesNotMatch() {
        var engine = armedEngine(mode: .shortcut)
        let supply = UnicodeSupply("k")

        let missingShift = press(&engine, down(Key.k, [.command]), supply: supply)
        XCTAssertEqual(missingShift.disposition, .pass)
        XCTAssertEqual(missingShift.eventClass, .passThrough)

        let extraControl = press(&engine, down(Key.k, [.command, .shift, .control]))
        XCTAssertEqual(extraControl.disposition, .pass)
        XCTAssertEqual(engine.actionCount, 0)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.ownedKeyCodes, [])
    }

    func testFlagsChangedAlwaysPassesAndIsCountedSeparately() {
        var engine = armedEngine(mode: .shortcut)
        let supply = UnicodeSupply("x")

        let decision = press(&engine, modifierChanged(Key.leftShift, [.shift]), supply: supply)
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.eventClass, .modifierPassThrough)
        XCTAssertEqual(engine.counters.modifierEvents, 1)
        XCTAssertEqual(engine.actionCount, 0)
        XCTAssertEqual(engine.ownedKeyCodes, [])
        XCTAssertEqual(supply.calls, 0)
    }

    func testUnrelatedKeyPassesInShortcutMode() {
        var engine = armedEngine(mode: .shortcut)
        let supply = UnicodeSupply("a")

        let decision = press(&engine, down(Key.a), supply: supply)
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.eventClass, .passThrough)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.ownedKeyCodes, [])
    }

    func testUnownedRepeatPassesAndInvalidatesHeldAtArmCase() {
        var engine = armedEngine(mode: .shortcut)

        let decision = press(&engine, down(Key.a, repeat: true))
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.eventClass, .unownedRepeatInvalid)
        XCTAssertEqual(decision.stopReason, .repeatWithoutOwnedDown)
        XCTAssertEqual(decision.invalidReason, .repeatWithoutOwnedDown)
        XCTAssertTrue(decision.shouldRemoveTap)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(engine.counters.repeatWithoutOwnership, 1)
    }

    func testModifierOnlyEscapeAndEmptyActionBindingsAreRejected() {
        let configuration = RoutingConfiguration(
            allowedPID: allowedPID,
            bindings: [
                ShortcutBinding(keyCode: Key.leftCommand, modifiers: [.command], actionID: "modifier-only"),
                ShortcutBinding(keyCode: Key.escape, modifiers: [.command], actionID: "escape"),
                ShortcutBinding(keyCode: Key.k, modifiers: [.command], actionID: "   ")
            ]
        )

        XCTAssertTrue(configuration.bindingIssues.contains(.modifierOnlyKey(keyCode: Key.leftCommand)))
        XCTAssertTrue(configuration.bindingIssues.contains(.reservedKey(keyCode: Key.escape)))
        XCTAssertTrue(configuration.bindingIssues.contains(.emptyActionID(keyCode: Key.k, modifiers: [.command])))
        XCTAssertTrue(configuration.validBindings.isEmpty)
    }

    func testDuplicateChordIsReported() {
        let binding = ShortcutBinding.fixtureDefault
        let configuration = RoutingConfiguration(allowedPID: allowedPID, bindings: [binding, binding])
        XCTAssertTrue(
            configuration.bindingIssues.contains(
                .duplicateChord(keyCode: binding.keyCode, modifiers: binding.modifiers)
            )
        )
    }
}
