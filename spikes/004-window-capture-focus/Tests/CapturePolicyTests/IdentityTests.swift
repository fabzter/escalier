import XCTest
import CapturePolicy

final class IdentityTests: XCTestCase {
    func testDefaultIdentityIsSyntheticAndCarriesNoStealthClaim() {
        let identity = FixtureIdentity(
            appName: "Escalier Synthetic Capture Fixture",
            buildKind: .unbundledExecutable,
            bundleIdentifier: nil
        )
        XCTAssertTrue(identity.synthetic)
        XCTAssertEqual(identity.spikeID, "004-window-capture-focus")
        XCTAssertEqual(identity.buildKind, .unbundledExecutable)
        let text = identity.claimBoundary.lowercased()
        XCTAssertTrue(text.contains("synthetic"))
        XCTAssertTrue(text.contains("not receiver-pixel evidence"))
        XCTAssertTrue(text.contains("no stealth"))
    }

    func testBundledBuildKindIsRepresentedExplicitly() {
        let identity = FixtureIdentity(
            appName: "Escalier Synthetic Capture Fixture",
            buildKind: .appBundle,
            bundleIdentifier: "test.escalier.spike004.fixture"
        )
        XCTAssertEqual(identity.buildKind.rawValue, "app-bundle")
        XCTAssertEqual(identity.bundleIdentifier, "test.escalier.spike004.fixture")
    }
}
