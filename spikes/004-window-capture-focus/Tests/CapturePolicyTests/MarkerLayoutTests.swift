import CoreGraphics
import XCTest
import CapturePolicy

final class MarkerLayoutTests: XCTestCase {
    func testMarkerPairIsVisuallyIdenticalAndDiffersOnlyInIdentityPositionAndSharing() {
        let pair = MarkerPair.layout(visibleFrame: CGRect(x: 0, y: 0, width: 1440, height: 900))
        XCTAssertTrue(pair.visualsMatch)
        XCTAssertEqual(pair.treatment.visual, pair.control.visual)
        XCTAssertEqual(pair.treatment.role, .sharingNoneMarker)
        XCTAssertEqual(pair.control.role, .sharingReadOnlyMarker)
        XCTAssertEqual(pair.treatment.sharing, .sharingNone)
        XCTAssertEqual(pair.control.sharing, .sharingReadOnly)
        XCTAssertNotEqual(pair.treatment.frame, pair.control.frame)
        XCTAssertEqual(pair.treatment.visual.headline, pair.control.visual.headline)
        XCTAssertEqual(pair.treatment.visual.roiColorHex, pair.control.visual.roiColorHex)
        XCTAssertEqual(pair.treatment.visual.roiRelativeRect, pair.control.visual.roiRelativeRect)
    }

    func testWideLayoutPlacesMarkersSideBySideInsideVisibleFrame() {
        let visible = CGRect(x: 0, y: 0, width: 1440, height: 900)
        let pair = MarkerPair.layout(visibleFrame: visible)
        XCTAssertFalse(pair.treatment.frame.cgRect.intersects(pair.control.frame.cgRect))
        XCTAssertTrue(visible.contains(pair.treatment.frame.cgRect))
        XCTAssertTrue(visible.contains(pair.control.frame.cgRect))
        XCTAssertLessThan(pair.treatment.frame.x, pair.control.frame.x)
        XCTAssertEqual(pair.treatment.frame.width, 360)
        XCTAssertEqual(pair.treatment.frame.height, 220)
    }

    func testNarrowLayoutStacksWithoutIntersectionOrOverflow() {
        let visible = CGRect(x: 0, y: 0, width: 500, height: 900)
        let pair = MarkerPair.layout(visibleFrame: visible)
        XCTAssertFalse(pair.treatment.frame.cgRect.intersects(pair.control.frame.cgRect))
        XCTAssertTrue(visible.contains(pair.treatment.frame.cgRect))
        XCTAssertTrue(visible.contains(pair.control.frame.cgRect))
        XCTAssertGreaterThan(pair.treatment.frame.y, pair.control.frame.y)
    }

    func testMarkerVisualFingerprintStatesSyntheticScopeWithoutProtectionClaims() {
        let pair = MarkerPair.layout(visibleFrame: CGRect(x: 0, y: 0, width: 1440, height: 900))
        let text = "\(pair.treatment.visual.headline) \(pair.treatment.visual.subheadline)".lowercased()
        XCTAssertTrue(text.contains("synthetic"))
        XCTAssertTrue(text.contains("not a stealth claim"))
        XCTAssertFalse(text.contains("protected"))
        XCTAssertFalse(text.contains("unprotected"))
        XCTAssertEqual(pair.treatment.visual.roiColorHex, "#FF00AA")
        XCTAssertEqual(pair.treatment.visual.backgroundColorHex, "#10151C")
    }

    func testMarkerPairIDsRemainMachineReadableAndDistinct() {
        let pair = MarkerPair.layout(visibleFrame: CGRect(x: 0, y: 0, width: 1440, height: 900))
        XCTAssertEqual(pair.treatment.markerID, "marker-sharing-none")
        XCTAssertEqual(pair.control.markerID, "marker-sharing-read-only")
        XCTAssertNotEqual(pair.treatment.markerID, pair.control.markerID)
    }

    func testRectCodableRoundTrip() {
        let rect = CGRect(x: 1.5, y: -2.5, width: 100, height: 200)
        let codable = RectCodable(rect)
        XCTAssertEqual(codable.x, 1.5)
        XCTAssertEqual(codable.y, -2.5)
        XCTAssertEqual(codable.width, 100)
        XCTAssertEqual(codable.height, 200)
        XCTAssertEqual(codable.cgRect, rect)
        XCTAssertFalse(codable.isEmpty)
    }
}
