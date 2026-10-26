import XCTest
@testable import RoutingCore

final class TextPolicyTests: XCTestCase {
    func testPrintableIsConsumedAndKeyUpFollowsOwnership() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")

        let decision = press(&engine, down(Key.a), supply: supply)
        XCTAssertEqual(decision.disposition, .consume)
        XCTAssertEqual(decision.eventClass, .textInput)
        XCTAssertTrue(decision.textChanged)
        XCTAssertEqual(decision.appendResult?.appendedUTF16, 1)
        XCTAssertEqual(engine.retainedText, "a")
        XCTAssertEqual(engine.ownedKeyCodes, [Key.a])
        XCTAssertEqual(engine.counters.textEvents, 1)
        XCTAssertEqual(engine.counters.unicodeExtractions, 1)
        XCTAssertEqual(supply.calls, 1)

        // Key-up ownership is independent of the current modifier flags.
        let release = press(&engine, up(Key.a, [.command, .shift]))
        XCTAssertEqual(release.disposition, .consume)
        XCTAssertEqual(release.eventClass, .ownedKeyUp)
        XCTAssertEqual(engine.ownedKeyCodes, [])
        XCTAssertEqual(supply.calls, 1)
    }

    func testRepeatDoesNotExtractOrAppendAgain() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        _ = press(&engine, down(Key.a), supply: supply)
        let repeatDown = press(&engine, down(Key.a, repeat: true), supply: supply)

        XCTAssertEqual(repeatDown.disposition, .consume)
        XCTAssertEqual(repeatDown.eventClass, .ownedRepeat)
        XCTAssertEqual(supply.calls, 1)
        XCTAssertEqual(engine.retainedText, "a")
        XCTAssertEqual(engine.counters.repeatsConsumed, 1)
    }

    func testShiftedPrintableIsPermitted() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("A")
        let decision = press(&engine, down(Key.a, [.shift]), supply: supply)
        XCTAssertEqual(decision.disposition, .consume)
        XCTAssertEqual(engine.retainedText, "A")
    }

    func testUnregisteredCommandControlOrOptionCombinationPassesWithoutExtraction() {
        for modifiers in [ModifierSet.command, .control, .option, [.command, .option]] {
            var engine = armedEngine(mode: .text)
            let supply = UnicodeSupply("a")
            let decision = press(&engine, down(Key.a, modifiers), supply: supply)
            XCTAssertEqual(decision.disposition, .pass, "\(modifiers)")
            XCTAssertEqual(supply.calls, 0, "\(modifiers)")
            XCTAssertEqual(engine.retainedText, "", "\(modifiers)")
            XCTAssertEqual(engine.ownedKeyCodes, [], "\(modifiers)")
        }
    }

    func testUnregisteredModifiedControlAndNavigationKeysPassWithoutPolicyEffects() {
        let cases: [(UInt16, ModifierSet)] = [
            (Key.backspace, .command),
            (Key.returnKey, .control),
            (Key.tab, .option),
            (Key.leftArrow, .command),
            (Key.space, .command)
        ]
        for (keyCode, modifiers) in cases {
            var engine = armedEngine(mode: .text)
            let supply = UnicodeSupply("a")
            let decision = press(&engine, down(keyCode, modifiers), supply: supply)
            XCTAssertEqual(decision.disposition, .pass, "\(keyCode) \(modifiers)")
            XCTAssertEqual(decision.eventClass, .passThrough, "\(keyCode) \(modifiers)")
            XCTAssertEqual(supply.calls, 0, "\(keyCode) \(modifiers)")
            XCTAssertEqual(engine.retainedText, "", "\(keyCode) \(modifiers)")
            XCTAssertEqual(engine.ownedKeyCodes, [], "\(keyCode) \(modifiers)")
            XCTAssertEqual(engine.phase, .armed, "\(keyCode) \(modifiers)")
        }
    }

    func testUnregisteredCommandBackspaceDoesNotEditBuffer() {
        var engine = armedEngine(mode: .text)
        _ = press(&engine, down(Key.a), supply: UnicodeSupply("ab"))
        XCTAssertEqual(engine.retainedText, "ab")

        let decision = press(&engine, down(Key.backspace, [.command]), supply: UnicodeSupply("x"))
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(engine.retainedText, "ab")
        XCTAssertTrue(engine.ownedKeyCodes.contains(Key.a))
        XCTAssertFalse(engine.ownedKeyCodes.contains(Key.backspace))
    }

    func testReservedActionPrecedesTextCapture() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("k")
        let decision = press(&engine, down(Key.k, [.command, .shift]), supply: supply)

        XCTAssertEqual(decision.disposition, .consume)
        XCTAssertEqual(decision.eventClass, .shortcutAction)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.actionCount, 1)
    }

    func testReturnTabDeleteNavigationAndBackspacePolicy() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        _ = press(&engine, down(Key.a), supply: supply)

        let returnDecision = press(&engine, down(Key.returnKey))
        XCTAssertEqual(returnDecision.disposition, .consume)
        XCTAssertEqual(returnDecision.eventClass, .textControl)
        XCTAssertEqual(engine.retainedText, "a")

        let tabDecision = press(&engine, down(Key.tab))
        XCTAssertEqual(tabDecision.disposition, .consume)
        XCTAssertEqual(tabDecision.eventClass, .textControl)
        XCTAssertEqual(engine.retainedText, "a")

        let deleteDecision = press(&engine, down(Key.forwardDelete))
        XCTAssertEqual(deleteDecision.disposition, .consume)
        XCTAssertEqual(deleteDecision.eventClass, .textControl)
        XCTAssertEqual(engine.retainedText, "a")

        let arrowDecision = press(&engine, down(Key.leftArrow))
        XCTAssertEqual(arrowDecision.disposition, .consume)
        XCTAssertEqual(arrowDecision.eventClass, .navigationIgnored)
        XCTAssertEqual(engine.counters.navigationEvents, 1)
        XCTAssertEqual(engine.retainedText, "a")

        let backspaceDecision = press(&engine, down(Key.backspace))
        XCTAssertEqual(backspaceDecision.disposition, .consume)
        XCTAssertEqual(backspaceDecision.eventClass, .textControl)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(supply.calls, 1)
    }

    func testBackspaceRemovesOneExtendedGrapheme() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("e\u{301}")
        _ = press(&engine, down(Key.a), supply: supply)
        XCTAssertEqual(engine.retainedText.utf16.count, 2)
        XCTAssertEqual(engine.retainedText.count, 1)

        _ = press(&engine, down(Key.backspace))
        XCTAssertEqual(engine.retainedText, "")
    }

    func testEmptyUnicodeExtractionPassesInsteadOfSwallowingTheKey() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply(nil)

        let decision = press(&engine, down(Key.a), supply: supply)
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(decision.eventClass, .passThrough)
        XCTAssertEqual(supply.calls, 1)
        XCTAssertEqual(engine.counters.emptyUnicodePasses, 1)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(engine.ownedKeyCodes, [])

        let release = press(&engine, up(Key.a))
        XCTAssertEqual(release.disposition, .pass)
    }

    func testUnknownControlPassesWithoutExtraction() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("x")
        let decision = press(&engine, down(Key.f1), supply: supply)

        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.ownedKeyCodes, [])
    }

    func testPerEventLimitTruncatesAtScalarBoundary() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply(String(repeating: "a", count: 130))
        let decision = press(&engine, down(Key.a), supply: supply)

        XCTAssertTrue(decision.appendResult?.eventTruncated ?? false)
        XCTAssertEqual(engine.retainedText.utf16.count, 128)
        XCTAssertTrue(engine.textWasTruncated)

        var scalarEngine = armedEngine(mode: .text)
        let scalarSupply = UnicodeSupply(String(repeating: "a", count: 127) + "\u{1F600}")
        let scalarDecision = press(&scalarEngine, down(Key.a), supply: scalarSupply)
        XCTAssertTrue(scalarDecision.appendResult?.eventTruncated ?? false)
        XCTAssertEqual(scalarEngine.retainedText.utf16.count, 127)
        XCTAssertEqual(scalarEngine.retainedText, String(repeating: "a", count: 127))
    }

    func testRetainedLimitNeverGrowsAndMarksOverflow() {
        var engine = armedEngine(mode: .text)
        for _ in 0..<8 {
            let supply = UnicodeSupply(String(repeating: "a", count: 128))
            _ = press(&engine, down(Key.a), supply: supply)
            _ = press(&engine, up(Key.a))
        }
        XCTAssertEqual(engine.retainedText.utf16.count, 1024)
        XCTAssertFalse(engine.textWasTruncated)

        let overflowSupply = UnicodeSupply("b")
        let decision = press(&engine, down(Key.a), supply: overflowSupply)
        XCTAssertTrue(decision.appendResult?.bufferOverflowed ?? false)
        XCTAssertEqual(decision.appendResult?.appendedUTF16, 0)
        XCTAssertEqual(engine.retainedText.utf16.count, 1024)
        XCTAssertTrue(engine.textWasTruncated)
        XCTAssertEqual(engine.retainedText, String(repeating: "a", count: 1024))
    }

    func testEscapeInTextModeConsumesAndDrainsItsOwnKeyUp() {
        var engine = armedEngine(mode: .text)
        let supply = UnicodeSupply("a")
        _ = press(&engine, down(Key.a), supply: supply)

        let stop = press(&engine, down(Key.escape), supply: supply)
        XCTAssertEqual(stop.disposition, .consume)
        XCTAssertEqual(stop.eventClass, .emergencyStop)
        XCTAssertEqual(stop.stopReason, .emergencyEscape)
        XCTAssertEqual(engine.phase, .draining)
        XCTAssertEqual(engine.retainedText, "")
        XCTAssertEqual(supply.calls, 1)
        XCTAssertTrue(engine.ownedKeyCodes.contains(Key.escape))

        let escapeUp = press(&engine, up(Key.escape))
        XCTAssertEqual(escapeUp.disposition, .consume)
        XCTAssertEqual(escapeUp.eventClass, .drainKeyUp)
        XCTAssertEqual(engine.phase, .draining)

        let keyUp = press(&engine, up(Key.a))
        XCTAssertEqual(keyUp.disposition, .consume)
        XCTAssertEqual(engine.phase, .closed)
        XCTAssertEqual(keyUp.shouldRemoveTap, true)
        XCTAssertEqual(keyUp.stopReason, .drainComplete)
    }

    func testEscapeWhileOffPasses() {
        var engine = RoutingEngine(configuration: RoutingConfiguration(allowedPID: allowedPID))
        let supply = UnicodeSupply("x")
        let decision = press(&engine, down(Key.escape), supply: supply)
        XCTAssertEqual(decision.disposition, .pass)
        XCTAssertEqual(supply.calls, 0)
        XCTAssertEqual(engine.phase, .off)
    }
}
