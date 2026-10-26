import XCTest
import Foundation

final class PackagingScriptTests: XCTestCase {
    private var packageRoot: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent() // EscalierCoreTests
            .deletingLastPathComponent() // Tests
            .deletingLastPathComponent() // package root
    }

    private func text(at relativePath: String) throws -> String {
        try String(
            contentsOf: packageRoot.appendingPathComponent(relativePath),
            encoding: .utf8
        )
    }

    func testPackagingScriptAdHocSignsThenVerifiesAndGuardsFailureModes() throws {
        let packageScript = try text(at: "tools/package-app.sh")
        let signCommand = "codesign --force --sign - --timestamp=none \"$APP\""
        let verifyCommand = "codesign --verify --strict --verbose=2 \"$APP\""
        let plistCopy = "cp \"Resources/Info.plist\" \"$APP/Contents/Info.plist\""

        XCTAssertTrue(packageScript.contains("set -euo pipefail"))
        XCTAssertFalse(packageScript.contains("|| true"), "Signing/verify failures must not be swallowed")
        XCTAssertFalse(packageScript.contains("--deep"), "Ad-hoc signing must not use --deep")
        XCTAssertFalse(packageScript.contains("--keychain"), "No keychain/identity selection is allowed")
        XCTAssertFalse(packageScript.contains("--entitlements"), "No entitlement grants are part of signing")
        XCTAssertFalse(packageScript.contains("--options"), "No hardened-runtime option is requested")

        guard let plistCopyRange = packageScript.range(of: plistCopy) else {
            XCTFail("Package script no longer assembles Info.plist before signing")
            return
        }
        guard let signRange = packageScript.range(of: signCommand) else {
            XCTFail("Package script must ad-hoc sign the assembled bundle after assembly")
            return
        }
        guard let verifyRange = packageScript.range(of: verifyCommand) else {
            XCTFail("Package script must strictly verify the signed bundle")
            return
        }

        XCTAssertTrue(
            plistCopyRange.lowerBound < signRange.lowerBound,
            "Signing must happen after bundle assembly"
        )
        XCTAssertTrue(
            signRange.lowerBound < verifyRange.lowerBound,
            "Verification must happen after signing"
        )

        let harnessURL = packageRoot.appendingPathComponent("tools/test-package-signing.sh")
        guard FileManager.default.isExecutableFile(atPath: harnessURL.path) else {
            XCTFail("Missing executable signing failure-propagation harness")
            return
        }
        let harness = try text(at: "tools/test-package-signing.sh")
        XCTAssertTrue(harness.contains("FAKE_CODESIGN_MODE"))
        XCTAssertTrue(harness.contains("sign-fail"))
        XCTAssertTrue(harness.contains("verify-fail"))
        XCTAssertTrue(harness.contains(verifyCommand))
        XCTAssertTrue(harness.contains("Signature=adhoc"))
        XCTAssertTrue(harness.contains("TeamIdentifier=not set"))
        XCTAssertTrue(harness.contains("Info.plist entries="))
        XCTAssertTrue(harness.contains("Sealed Resources version="))
        XCTAssertFalse(harness.contains("--deep"))
        XCTAssertFalse(harness.contains("spctl"))
        XCTAssertFalse(harness.contains("xattr"))
        XCTAssertFalse(harness.contains("open .build"))
    }
}
