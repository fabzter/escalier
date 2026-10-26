import XCTest
import Foundation
import EscalierCore

/// Static audit scoped to spike 003's UI prototype. A separate, independently reviewed
/// 005-global-keyboard-routing spike owns any active interception work. This audit does not
/// make a project-wide policy claim and intentionally does not constrain that related spike.
final class SourceAuditTests: XCTestCase {
    private var packageRoot: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent() // EscalierCoreTests
            .deletingLastPathComponent() // Tests
            .deletingLastPathComponent() // package root
    }

    private let forbiddenTokens = [
        "addGlobalMonitorForEvents",
        "addLocalMonitorForEvents",
        "NSEvent.addGlobal",
        "NSEvent.addLocal",
        "CGEvent",
        "eventTap",
        "AXIsProcessTrusted",
        "AXUIElement",
        "CGRequestListenEventAccess",
        "CGPreflightListenEventAccess",
        "CGRequestPostEventAccess",
        "IOHID",
        "CGWindowListCreateImage",
        "SCShareableContent",
        "SCStream",
        "AVCapture",
        "getDisplayMedia",
        "URLSession",
        "NSURLConnection",
        "NWConnection",
        "import Network",
        "Process(",
        "NSAppleScript",
        "UserDefaults",
        "FileManager.default.removeItem",
        ".write(to:"
    ]

    private func swiftSourceFiles() throws -> [URL] {
        let sources = packageRoot.appendingPathComponent("Sources", isDirectory: true)
        guard let enumerator = FileManager.default.enumerator(
            at: sources,
            includingPropertiesForKeys: [.isRegularFileKey]
        ) else {
            return []
        }
        var files: [URL] = []
        for case let url as URL in enumerator where url.pathExtension == "swift" {
            files.append(url)
        }
        return files.sorted { $0.path < $1.path }
    }

    private func matches(in text: String) -> [String] {
        forbiddenTokens.filter { text.contains($0) }
    }

    func test003SourcesContainNoGlobalInputHooksPermissionRequestsCaptureOrNetworking() throws {
        let files = try swiftSourceFiles()
        XCTAssertGreaterThanOrEqual(files.count, 2, "Expected core and shell source files")

        for file in files {
            let text = try String(contentsOf: file, encoding: .utf8)
            let hits = matches(in: text)
            XCTAssertTrue(
                hits.isEmpty,
                "\(file.lastPathComponent) contains forbidden 003 UI-prototype token(s): \(hits)"
            )
        }
    }

    func testForbiddenTokenAuditDetectsAPositiveControl() {
        XCTAssertFalse(forbiddenTokens.isEmpty)
        XCTAssertEqual(Set(forbiddenTokens).count, forbiddenTokens.count)

        let planted = "NSEvent.addGlobalMonitorForEvents; URLSession; CGEvent; AXUIElement"
        let hits = matches(in: planted)

        XCTAssertTrue(hits.contains("addGlobalMonitorForEvents"))
        XCTAssertTrue(hits.contains("URLSession"))
        XCTAssertTrue(hits.contains("CGEvent"))
        XCTAssertTrue(hits.contains("AXUIElement"))
        XCTAssertTrue(matches(in: "entirely harmless synthetic UI copy").isEmpty)
    }

    func testInfoPlistDeclaresNoSensitiveCapturePermissionUsage() throws {
        let plistURL = packageRoot.appendingPathComponent("Resources/Info.plist")
        let text = try String(contentsOf: plistURL, encoding: .utf8)
        let sensitiveKeys = [
            "NSAccessibilityUsageDescription",
            "NSInputMonitoringUsageDescription",
            "NSScreenCaptureUsageDescription",
            "NSMicrophoneUsageDescription",
            "NSCameraUsageDescription"
        ]
        for key in sensitiveKeys {
            XCTAssertFalse(text.contains(key), "Info.plist must not request \(key) in spike 003")
        }
    }

    func testPackageHasNoRemoteDependency() throws {
        let manifest = try String(
            contentsOf: packageRoot.appendingPathComponent("Package.swift"),
            encoding: .utf8
        )
        XCTAssertFalse(manifest.contains(".package("))
        XCTAssertFalse(manifest.contains("http://"))
        XCTAssertFalse(manifest.contains("https://"))
    }
}
