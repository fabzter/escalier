import Foundation

public struct FixtureWindowPolicy: Equatable, Sendable {
    public let role: FixtureWindowRole
    public let sharing: SharingPolicy
    public let styleMaskRaw: UInt
    public let levelRaw: Int
    public let alpha: Double
    public let hasShadow: Bool
    public let isOpaque: Bool
    public let ignoresMouseEvents: Bool
    public let hidesOnDeactivate: Bool
    public let becomesKeyOnlyIfNeeded: Bool
    public let isFloatingPanel: Bool
    public let collectionBehaviorRaw: UInt
    public let title: String

    public init(
        role: FixtureWindowRole,
        sharing: SharingPolicy,
        styleMaskRaw: UInt,
        levelRaw: Int,
        alpha: Double = 1,
        hasShadow: Bool = false,
        isOpaque: Bool = true,
        ignoresMouseEvents: Bool = false,
        hidesOnDeactivate: Bool = false,
        becomesKeyOnlyIfNeeded: Bool = true,
        isFloatingPanel: Bool = true,
        collectionBehaviorRaw: UInt = 0,
        title: String
    ) {
        self.role = role
        self.sharing = sharing
        self.styleMaskRaw = styleMaskRaw
        self.levelRaw = levelRaw
        self.alpha = alpha
        self.hasShadow = hasShadow
        self.isOpaque = isOpaque
        self.ignoresMouseEvents = ignoresMouseEvents
        self.hidesOnDeactivate = hidesOnDeactivate
        self.becomesKeyOnlyIfNeeded = becomesKeyOnlyIfNeeded
        self.isFloatingPanel = isFloatingPanel
        self.collectionBehaviorRaw = collectionBehaviorRaw
        self.title = title
    }
}

public enum FixturePolicies {
    public static let allWindowRoles = FixtureWindowRole.readbackOrder

    public static let markerCollectionBehaviorRaw =
        WindowOptionNames.canJoinAllSpacesRaw | WindowOptionNames.fullScreenAuxiliaryRaw

    public static let controlWindowStyleMaskRaw =
        WindowOptionNames.titledStyleMaskRaw
            | WindowOptionNames.closableStyleMaskRaw
            | WindowOptionNames.miniaturizableStyleMaskRaw
            | WindowOptionNames.resizableStyleMaskRaw

    public static let neutralTitlePresets: [String] = [
        "Escalier Synthetic Capture/Focus Fixture — NOT A STEALTH CLAIM",
        "Notes (Escalier synthetic fixture)"
    ]

    public static let defaultControlTitle = neutralTitlePresets[0]
    public static let markerTitle = "Escalier synthetic marker"
    public static let auxiliaryTitle = "Escalier auxiliary synthetic panel"
    public static let clickThroughTitle = "Escalier click-through synthetic panel"

    public static func marker(
        role: FixtureWindowRole,
        frame: RectCodable
    ) -> FixtureWindowPolicy {
        FixtureWindowPolicy(
            role: role,
            sharing: role.expectedSharing,
            styleMaskRaw: WindowOptionNames.nonactivatingPanelStyleMaskRaw,
            levelRaw: WindowOptionNames.floatingLevelRaw,
            alpha: 1,
            hasShadow: false,
            isOpaque: true,
            ignoresMouseEvents: false,
            hidesOnDeactivate: false,
            becomesKeyOnlyIfNeeded: true,
            isFloatingPanel: true,
            collectionBehaviorRaw: markerCollectionBehaviorRaw,
            title: markerTitle
        )
    }

    public static func controlWindow(title: String = defaultControlTitle) -> FixtureWindowPolicy {
        FixtureWindowPolicy(
            role: .controlWindow,
            sharing: .sharingReadOnly,
            styleMaskRaw: controlWindowStyleMaskRaw,
            levelRaw: WindowOptionNames.normalLevelRaw,
            alpha: 1,
            hasShadow: true,
            isOpaque: true,
            ignoresMouseEvents: false,
            hidesOnDeactivate: false,
            becomesKeyOnlyIfNeeded: false,
            isFloatingPanel: false,
            collectionBehaviorRaw: 0,
            title: title
        )
    }

    public static func auxiliaryPanel(
        nonactivating: Bool,
        title: String = auxiliaryTitle
    ) -> FixtureWindowPolicy {
        FixtureWindowPolicy(
            role: .auxiliaryPanel,
            sharing: .sharingNone,
            styleMaskRaw: WindowOptionNames.titledStyleMaskRaw
                | (nonactivating ? WindowOptionNames.nonactivatingPanelStyleMaskRaw : 0),
            levelRaw: WindowOptionNames.floatingLevelRaw,
            alpha: 1,
            hasShadow: true,
            isOpaque: true,
            ignoresMouseEvents: false,
            hidesOnDeactivate: false,
            becomesKeyOnlyIfNeeded: true,
            isFloatingPanel: true,
            collectionBehaviorRaw: markerCollectionBehaviorRaw,
            title: title
        )
    }

    public static func clickThroughPanel(
        intercept: Bool,
        title: String = clickThroughTitle
    ) -> FixtureWindowPolicy {
        FixtureWindowPolicy(
            role: .clickThroughPanel,
            sharing: .sharingReadOnly,
            styleMaskRaw: WindowOptionNames.nonactivatingPanelStyleMaskRaw,
            levelRaw: WindowOptionNames.floatingLevelRaw,
            alpha: 1,
            hasShadow: false,
            isOpaque: true,
            ignoresMouseEvents: !intercept,
            hidesOnDeactivate: false,
            becomesKeyOnlyIfNeeded: true,
            isFloatingPanel: true,
            collectionBehaviorRaw: markerCollectionBehaviorRaw,
            title: title
        )
    }
}
