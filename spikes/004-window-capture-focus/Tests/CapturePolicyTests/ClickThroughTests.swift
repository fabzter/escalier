import Foundation
import XCTest
import CapturePolicy

final class ClickThroughTests: XCTestCase {
    func testClickThroughModeMapsToAppKitIgnoreMouseEventsSemantics() {
        XCTAssertEqual(ClickThroughMode.intercept.ignoresMouseEvents, false)
        XCTAssertEqual(ClickThroughMode.passThrough.ignoresMouseEvents, true)
        XCTAssertEqual(ClickThroughMode.matching(ignoresMouseEvents: false), .intercept)
        XCTAssertEqual(ClickThroughMode.matching(ignoresMouseEvents: true), .passThrough)
    }

    func testClickThroughPanelPolicyFollowsMode() {
        XCTAssertEqual(FixturePolicies.clickThroughPanel(intercept: true).ignoresMouseEvents, false)
        XCTAssertEqual(FixturePolicies.clickThroughPanel(intercept: false).ignoresMouseEvents, true)
    }

    func testCountersAreInertAndExplicitlyManual() {
        var counters = ClickThroughCounters()
        XCTAssertEqual(counters.mode, .intercept)
        XCTAssertEqual(counters.panelHits, 0)
        XCTAssertEqual(counters.browserUnderlayHits, 0)
        XCTAssertFalse(counters.ignoresMouseEventsRequested)
        XCTAssertTrue(counters.note.lowercased().contains("inert"))
        XCTAssertTrue(counters.note.lowercased().contains("no real actions"))
        XCTAssertTrue(counters.underlayCountSource.lowercased().contains("manual"))
        XCTAssertTrue(counters.underlayCountSource.lowercased().contains("browser"))

        counters.recordPanelHit()
        counters.recordPanelHit()
        XCTAssertEqual(counters.panelHits, 2)

        try? counters.recordBrowserUnderlayHits(3)
        XCTAssertEqual(counters.browserUnderlayHits, 3)

        counters.setMode(.passThrough)
        XCTAssertEqual(counters.mode, .passThrough)
        XCTAssertTrue(counters.ignoresMouseEventsRequested)
    }

    func testNegativeUnderlayCountIsRejectedWithoutMutation() {
        var counters = ClickThroughCounters()
        XCTAssertThrowsError(try counters.recordBrowserUnderlayHits(-1)) { error in
            XCTAssertEqual(error as? ClickThroughCounterError, .negativeValue)
        }
        XCTAssertEqual(counters.browserUnderlayHits, 0)
    }

    func testCountersEncodeAllFieldsAndNoPixelOrAutomationClaim() throws {
        var counters = ClickThroughCounters()
        counters.recordPanelHit()
        let data = try JSONEncoder().encode(counters)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        for key in [
            "mode", "ignoresMouseEventsRequested", "panelHits", "browserUnderlayHits",
            "underlayCountSource", "note"
        ] {
            XCTAssertNotNil(object[key], "missing counter field: \(key)")
        }
        let text = try XCTUnwrap(String(data: data, encoding: .utf8)).lowercased()
        XCTAssertFalse(text.contains("automation"))
        XCTAssertFalse(text.contains("protected"))
    }
}
