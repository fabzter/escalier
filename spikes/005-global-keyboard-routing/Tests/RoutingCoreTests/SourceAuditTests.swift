import XCTest
@testable import RoutingCore

final class SourceAuditTests: XCTestCase {
    private var packageRoot: URL {
        if let override = ProcessInfo.processInfo.environment["GUARD_ROOT"] {
            return URL(fileURLWithPath: override, isDirectory: true)
        }
        return URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
    }

    private func files(under relative: String, extension ext: String) -> [URL] {
        let root = packageRoot.appendingPathComponent(relative, isDirectory: true)
        guard let enumerator = FileManager.default.enumerator(
            at: root,
            includingPropertiesForKeys: [.isRegularFileKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }
        var result: [URL] = []
        for case let url as URL in enumerator where url.pathExtension == ext {
            result.append(url)
        }
        return result.sorted { $0.path < $1.path }
    }

    private func read(_ url: URL) throws -> String {
        try String(contentsOf: url, encoding: .utf8)
    }

    private func violations(in text: String, patterns: [String]) -> [String] {
        patterns.filter { text.contains($0) }
    }

    private func audit(
        files: [URL],
        patterns: [String],
        file: StaticString = #filePath,
        line: UInt = #line
    ) throws {
        XCTAssertFalse(files.isEmpty, "expected auditable files", file: file, line: line)
        for url in files {
            let text = try read(url)
            let found = violations(in: text, patterns: patterns)
            XCTAssertTrue(found.isEmpty, "\(url.lastPathComponent): \(found)", file: file, line: line)
        }
    }

    private func combined(_ files: [URL]) throws -> String {
        try files.map(read).joined(separator: "\n")
    }

    private func region(_ text: String, from start: String, to end: String) -> String? {
        guard let startRange = text.range(of: start),
              let endRange = text.range(of: end, range: startRange.upperBound..<text.endIndex) else {
            return nil
        }
        return String(text[startRange.upperBound..<endRange.lowerBound])
    }

    // MARK: - Swift source guards

    func testCoreContainsNoNativeOrSideEffectSymbols() throws {
        try audit(
            files: files(under: "Sources/RoutingCore", extension: "swift"),
            patterns: [
                "import AppKit", "import Cocoa", "import CoreGraphics",
                "import ApplicationServices", "import Carbon",
                "CGEvent.tapCreate", "CGEvent(", "CGEventPost", "CGEventCreateKeyboardEvent",
                "postToPid", "keyboardSetUnicodeString", "tapPostEvent",
                "NSPasteboard", "AXUIElement", "URLSession", "FileHandle",
                "DispatchQueue", "NSLog(", "print(", "os_log", "UserDefaults",
                "SMAppService", "NSApplication", "NSWorkspace", "CFRunLoop"
            ]
        )
    }

    func testAdapterLibraryContainsNoNativeOrSideEffectSymbols() throws {
        try audit(
            files: files(under: "Sources/RoutingAdapter", extension: "swift"),
            patterns: [
                "import AppKit", "import Cocoa", "import CoreGraphics",
                "import ApplicationServices", "import Carbon",
                "CGEvent.tapCreate", "CGEvent(", "CGEventPost", "CGEventCreateKeyboardEvent",
                "postToPid", "keyboardSetUnicodeString", "tapPostEvent",
                "NSPasteboard", "AXUIElement", "URLSession", "FileHandle",
                "DispatchQueue", "NSLog(", "print(", "os_log", "UserDefaults",
                "SMAppService", "NSApplication", "NSWorkspace", "CFRunLoop"
            ]
        )
    }

    func testFixtureContainsNoPromptInjectionPersistenceOrRawLogging() throws {
        try audit(
            files: files(under: "Sources/RoutingFixture", extension: "swift"),
            patterns: [
                "kAXTrustedCheckOptionPrompt", "AXIsProcessTrustedWithOptions",
                "CGRequestListenEventAccess", "CGRequestPostEventAccess",
                "CGEventPost", "CGEventCreateKeyboardEvent", "postToPid",
                "keyboardSetUnicodeString", "AXUIElementSetAttributeValue",
                "NSPasteboard", "URLSession", "NSLog(", "print(", "os_log",
                "FileHandle", "UserDefaults", "SMAppService", "launchctl",
                "String(describing", "CFShow", "NSApp.activate",
                "activateIgnoringOtherApps", "EnableSecureEventInput",
                "DisableSecureEventInput", ".listenOnly"
            ]
        )
    }

    func testFixtureUsesPinnedActiveTapConfiguration() throws {
        let fixture = try combined(files(under: "Sources/RoutingFixture", extension: "swift"))
        for required in [
            ".cgSessionEventTap",
            ".headInsertEventTap",
            ".defaultTap",
            "eventsOfInterest",
            "return nil",
            "Unmanaged.passUnretained(event)",
            "Unmanaged.passRetained(self)",
            "CGEventType.tapDisabledByTimeout",
            ".tapDisabledByUserInput",
            "AXIsProcessTrusted()",
            "CGPreflightListenEventAccess()",
            "IsSecureEventInputEnabled()",
            "NSPanel",
            ".nonactivatingPanel",
            "becomesKeyOnlyIfNeeded",
            "AdapterCoordinator(",
            "TerminationGate",
            "applicationShouldTerminate",
            "onTeardownComplete"
        ] {
            XCTAssertTrue(fixture.contains(required), "missing \(required)")
        }
    }

    func testDisabledNotificationsAreNotMaskBits() throws {
        let fixture = try combined(files(under: "Sources/RoutingFixture", extension: "swift"))
        guard let maskLine = fixture.split(separator: "\n").first(where: { $0.contains("eventsOfInterest") }) else {
            return XCTFail("no eventsOfInterest line")
        }
        XCTAssertFalse(maskLine.contains("tapDisabled"))
        XCTAssertFalse(maskLine.contains("0xFFFF"))
    }

    func testCallbackBoundaryDoesNotDispatchLogOrReadFiles() throws {
        let fixture = try combined(files(under: "Sources/RoutingFixture", extension: "swift"))
        guard let body = region(fixture, from: "// CALLBACK-BEGIN", to: "// CALLBACK-END") else {
            return XCTFail("callback boundary markers missing")
        }
        XCTAssertFalse(body.isEmpty)
        let forbidden = [
            "DispatchQueue", "print(", "NSLog", "os_log", "FileHandle", "String(describing",
            "CFShow", "await", "try?"
        ]
        XCTAssertTrue(violations(in: body, patterns: forbidden).isEmpty)
    }

    func testStartupDoesNotArmOrCreateATap() throws {
        let fixture = try combined(files(under: "Sources/RoutingFixture", extension: "swift"))
        guard let startup = region(fixture, from: "// STARTUP-BEGIN", to: "// STARTUP-END") else {
            return XCTFail("startup boundary markers missing")
        }
        XCTAssertFalse(startup.contains(".start("))
        XCTAssertFalse(startup.contains("beginArm("))
        XCTAssertFalse(startup.contains("tapCreate"))
    }

    func testLifetimeDrainAndTextBoundsArePreRegistered() throws {
        let core = try combined(files(under: "Sources/RoutingCore", extension: "swift"))
        for required in [
            "maxSessionDuration: TimeInterval = 30.0",
            "drainDuration: TimeInterval = 1.5",
            "settleInterval: TimeInterval = 0.250",
            "perEventUTF16Limit: Int = 128",
            "retainedUTF16Limit: Int = 1024",
            "callbackBudgetNanoseconds: UInt64 = 2_000_000",
            "uiReadInterval: TimeInterval = 0.1"
        ] {
            XCTAssertTrue(core.contains(required), "missing \(required)")
        }
    }

    // MARK: - Browser oracle source guards

    func testBrowserOracleDoesNotSuppressOrExfiltrateInput() throws {
        let webFiles = files(under: "web", extension: "html")
            + files(under: "web", extension: "mjs")
            + files(under: "web", extension: "css")
        XCTAssertFalse(webFiles.isEmpty)
        try audit(
            files: webFiles,
            patterns: [
                "preventDefault", "stopPropagation", "stopImmediatePropagation",
                "returnValue", "fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon",
                "localStorage", "sessionStorage", "indexedDB", "console.",
                "http://", "https://", "eval(", "new Function", "document.cookie"
            ]
        )
    }

    func testBrowserOracleHasRequiredCountersFieldAndControls() throws {
        let web = try combined(
            files(under: "web", extension: "html")
                + files(under: "web", extension: "mjs")
        )
        for required in [
            "test-field",
            "keydown", "keyup", "beforeinput", "input",
            "compositionstart", "compositionend",
            "focus", "blur", "visibilitychange", "scroll",
            "positive control", "same chord", "OFF",
            "{ capture: true, passive: true }",
            "default-src 'none'"
        ] {
            XCTAssertTrue(web.contains(required), "missing \(required)")
        }
        XCTAssertTrue(web.contains("<input") || web.contains("<textarea"))
        XCTAssertFalse(web.contains("disabled"))
        XCTAssertFalse(web.contains("readonly"))
    }

    // MARK: - Guard tamper checks (pure scanner negative samples)

    func testScannerDetectsInjectedLoggingAndSuppressionSamples() {
        let logging = "let x = 1\nprint(\"raw\")\n"
        XCTAssertEqual(violations(in: logging, patterns: ["print("]), ["print("])

        let unpinned = "field.addEventListener('keydown', handler, { capture: true });"
        XCTAssertEqual(violations(in: unpinned, patterns: ["{ capture: true, passive: true }"]), [])

        let injected = "document.addEventListener('keydown', e => e.preventDefault())"
        XCTAssertEqual(violations(in: injected, patterns: ["preventDefault"]), ["preventDefault"])
    }
}
