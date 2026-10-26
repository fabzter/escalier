import AppKit
import XCTest
import CapturePolicy

final class PolicyTests: XCTestCase {
    func testSharingPolicyRawValuesMatchAppKit() {
        XCTAssertEqual(SharingPolicy.sharingNone.appKitRawValue, NSWindow.SharingType.none.rawValue)
        XCTAssertEqual(SharingPolicy.sharingReadOnly.appKitRawValue, NSWindow.SharingType.readOnly.rawValue)
    }

    func testSharingLabelsDoNotUseProtectionWording() {
        for policy in SharingPolicy.allCases {
            let text = "\(policy.rawValue) \(policy.summary)".lowercased()
            XCTAssertFalse(text.contains("protected"))
            XCTAssertFalse(text.contains("unprotected"))
        }
    }

    func testObservedSharingNamesAreExplicit() {
        XCTAssertEqual(SharingPolicy.observedName(forRaw: 0), "sharing-none")
        XCTAssertEqual(SharingPolicy.observedName(forRaw: 1), "sharing-readOnly")
        XCTAssertEqual(SharingPolicy.observedName(forRaw: 2), "sharing-readWrite-deprecated")
        XCTAssertEqual(SharingPolicy.observedName(forRaw: 99), "sharing-unknown-99")
    }

    func testFixtureRolesHaveExpectedSharingAndStableOrder() {
        XCTAssertEqual(FixtureWindowRole.controlWindow.expectedSharing, .sharingReadOnly)
        XCTAssertEqual(FixtureWindowRole.sharingNoneMarker.expectedSharing, .sharingNone)
        XCTAssertEqual(FixtureWindowRole.sharingReadOnlyMarker.expectedSharing, .sharingReadOnly)
        XCTAssertEqual(FixtureWindowRole.auxiliaryPanel.expectedSharing, .sharingNone)
        XCTAssertEqual(FixtureWindowRole.clickThroughPanel.expectedSharing, .sharingReadOnly)
        XCTAssertEqual(
            FixtureWindowRole.readbackOrder,
            [
                .controlWindow,
                .sharingNoneMarker,
                .sharingReadOnlyMarker,
                .auxiliaryPanel,
                .clickThroughPanel
            ]
        )
        XCTAssertEqual(FixturePolicies.allWindowRoles, FixtureWindowRole.readbackOrder)
    }

    func testMarkerRolesMapToSharingPolicies() {
        XCTAssertEqual(FixtureWindowRole.markerRole(for: .sharingNone), .sharingNoneMarker)
        XCTAssertEqual(FixtureWindowRole.markerRole(for: .sharingReadOnly), .sharingReadOnlyMarker)
    }

    func testWindowOptionConstantsMatchAppKit() {
        XCTAssertEqual(WindowOptionNames.titledStyleMaskRaw, NSWindow.StyleMask.titled.rawValue)
        XCTAssertEqual(WindowOptionNames.closableStyleMaskRaw, NSWindow.StyleMask.closable.rawValue)
        XCTAssertEqual(WindowOptionNames.miniaturizableStyleMaskRaw, NSWindow.StyleMask.miniaturizable.rawValue)
        XCTAssertEqual(WindowOptionNames.resizableStyleMaskRaw, NSWindow.StyleMask.resizable.rawValue)
        XCTAssertEqual(
            WindowOptionNames.nonactivatingPanelStyleMaskRaw,
            NSWindow.StyleMask.nonactivatingPanel.rawValue
        )
        XCTAssertEqual(WindowOptionNames.normalLevelRaw, NSWindow.Level.normal.rawValue)
        XCTAssertEqual(WindowOptionNames.floatingLevelRaw, NSWindow.Level.floating.rawValue)
        XCTAssertEqual(WindowOptionNames.statusBarLevelRaw, NSWindow.Level.statusBar.rawValue)
        XCTAssertEqual(
            WindowOptionNames.canJoinAllSpacesRaw,
            NSWindow.CollectionBehavior.canJoinAllSpaces.rawValue
        )
        XCTAssertEqual(
            WindowOptionNames.fullScreenAuxiliaryRaw,
            NSWindow.CollectionBehavior.fullScreenAuxiliary.rawValue
        )
        XCTAssertEqual(
            WindowOptionNames.regularActivationRaw,
            NSApplication.ActivationPolicy.regular.rawValue
        )
        XCTAssertEqual(
            WindowOptionNames.accessoryActivationRaw,
            NSApplication.ActivationPolicy.accessory.rawValue
        )
        XCTAssertEqual(
            WindowOptionNames.prohibitedActivationRaw,
            NSApplication.ActivationPolicy.prohibited.rawValue
        )
    }

    func testStyleMaskNamesReadBackUnknownBits() {
        let titledAndNonactivating = WindowOptionNames.titledStyleMaskRaw
            | WindowOptionNames.nonactivatingPanelStyleMaskRaw
        XCTAssertEqual(
            WindowOptionNames.styleMaskNames(forRaw: titledAndNonactivating),
            ["titled", "nonactivatingPanel"]
        )
        XCTAssertEqual(
            WindowOptionNames.styleMaskNames(
                forRaw: WindowOptionNames.nonactivatingPanelStyleMaskRaw
            ),
            ["borderless", "nonactivatingPanel"]
        )
        XCTAssertEqual(WindowOptionNames.styleMaskNames(forRaw: 0), ["borderless"])
        XCTAssertTrue(
            WindowOptionNames.styleMaskNames(forRaw: 1 << 20).contains("unknown-bits-\(1 << 20)")
        )
    }

    func testLevelAndActivationNames() {
        XCTAssertEqual(WindowOptionNames.levelName(forRaw: 0), "normal")
        XCTAssertEqual(WindowOptionNames.levelName(forRaw: 3), "floating")
        XCTAssertEqual(WindowOptionNames.levelName(forRaw: 999), "level-999")
        XCTAssertEqual(WindowOptionNames.activationPolicyName(forRaw: 0), "regular")
        XCTAssertEqual(WindowOptionNames.activationPolicyName(forRaw: 1), "accessory")
        XCTAssertEqual(WindowOptionNames.activationPolicyName(forRaw: 2), "prohibited")
        XCTAssertEqual(WindowOptionNames.activationPolicyName(forRaw: 7), "unknown-7")
    }

    func testFixturePoliciesHaveExpectedSharingAndStyle() {
        let control = FixturePolicies.controlWindow(title: "Fixture")
        XCTAssertEqual(control.role, .controlWindow)
        XCTAssertEqual(control.sharing, .sharingReadOnly)
        XCTAssertEqual(control.styleMaskRaw, 15)
        XCTAssertEqual(control.levelRaw, 0)
        XCTAssertFalse(control.ignoresMouseEvents)
        XCTAssertFalse(control.isFloatingPanel)

        let marker = TestFixtures.markerPolicy
        XCTAssertEqual(marker.sharing, .sharingNone)
        XCTAssertEqual(marker.styleMaskRaw, WindowOptionNames.nonactivatingPanelStyleMaskRaw)
        XCTAssertEqual(marker.levelRaw, WindowOptionNames.floatingLevelRaw)
        XCTAssertEqual(marker.ignoresMouseEvents, false)
        XCTAssertEqual(marker.becomesKeyOnlyIfNeeded, true)
        XCTAssertEqual(marker.isFloatingPanel, true)
        XCTAssertEqual(
            marker.collectionBehaviorRaw,
            WindowOptionNames.canJoinAllSpacesRaw | WindowOptionNames.fullScreenAuxiliaryRaw
        )

        let auxNormal = FixturePolicies.auxiliaryPanel(nonactivating: false)
        XCTAssertEqual(auxNormal.role, .auxiliaryPanel)
        XCTAssertEqual(auxNormal.sharing, .sharingNone)
        XCTAssertEqual(auxNormal.styleMaskRaw, WindowOptionNames.titledStyleMaskRaw)

        let auxNonactivating = FixturePolicies.auxiliaryPanel(nonactivating: true)
        XCTAssertEqual(
            auxNonactivating.styleMaskRaw,
            WindowOptionNames.titledStyleMaskRaw | WindowOptionNames.nonactivatingPanelStyleMaskRaw
        )

        let intercept = FixturePolicies.clickThroughPanel(intercept: true)
        let passThrough = FixturePolicies.clickThroughPanel(intercept: false)
        XCTAssertEqual(intercept.role, .clickThroughPanel)
        XCTAssertEqual(passThrough.role, .clickThroughPanel)
        XCTAssertEqual(intercept.sharing, .sharingReadOnly)
        XCTAssertEqual(intercept.ignoresMouseEvents, false)
        XCTAssertEqual(passThrough.ignoresMouseEvents, true)
    }

    func testNeutralTitlePresetsAreSyntheticAndDoNotImpersonateTrustedApps() {
        XCTAssertGreaterThanOrEqual(FixturePolicies.neutralTitlePresets.count, 2)
        let banned = [
            "zoom", "slack", "teams", "google meet", "meet", "hackerrank",
            "discord", "notion", "browser", "safari", "chrome", "firefox"
        ]
        for title in FixturePolicies.neutralTitlePresets {
            let lowercased = title.lowercased()
            XCTAssertTrue(lowercased.contains("escalier"), "title must remain clearly owned: \(title)")
            XCTAssertTrue(lowercased.contains("synthetic"), "title must remain clearly synthetic: \(title)")
            for word in banned {
                XCTAssertFalse(lowercased.contains(word), "title impersonates \(word): \(title)")
            }
        }
    }
}
