import Foundation
import CoreGraphics

public struct MarkerVisualFingerprint: Equatable, Sendable {
    public let headline: String
    public let subheadline: String
    public let backgroundColorHex: String
    public let roiColorHex: String
    public let roiRelativeRect: RectCodable
    public let windowWidth: Double
    public let windowHeight: Double
    public let styleMaskRaw: UInt
    public let levelRaw: Int
    public let alpha: Double
    public let hasShadow: Bool
    public let isOpaque: Bool
    public let collectionBehaviorRaw: UInt
    public let title: String

    public init(
        headline: String,
        subheadline: String,
        backgroundColorHex: String,
        roiColorHex: String,
        roiRelativeRect: RectCodable,
        windowWidth: Double,
        windowHeight: Double,
        styleMaskRaw: UInt,
        levelRaw: Int,
        alpha: Double,
        hasShadow: Bool,
        isOpaque: Bool,
        collectionBehaviorRaw: UInt,
        title: String
    ) {
        self.headline = headline
        self.subheadline = subheadline
        self.backgroundColorHex = backgroundColorHex
        self.roiColorHex = roiColorHex
        self.roiRelativeRect = roiRelativeRect
        self.windowWidth = windowWidth
        self.windowHeight = windowHeight
        self.styleMaskRaw = styleMaskRaw
        self.levelRaw = levelRaw
        self.alpha = alpha
        self.hasShadow = hasShadow
        self.isOpaque = isOpaque
        self.collectionBehaviorRaw = collectionBehaviorRaw
        self.title = title
    }
}

public struct MarkerSpec: Equatable, Sendable {
    public let role: FixtureWindowRole
    public let sharing: SharingPolicy
    public let frame: RectCodable
    public let visual: MarkerVisualFingerprint

    public init(
        role: FixtureWindowRole,
        sharing: SharingPolicy,
        frame: RectCodable,
        visual: MarkerVisualFingerprint
    ) {
        self.role = role
        self.sharing = sharing
        self.frame = frame
        self.visual = visual
    }

    public var markerID: String {
        role.rawValue
    }

    public var policy: FixtureWindowPolicy {
        FixturePolicies.marker(role: role, frame: frame)
    }
}

/// Two deliberately identical marker panels. Only the role, sharing type and
/// frame origin differ; a receiver's per-cell positive control is the
/// sharing-readOnly panel, not an inference from the sharing-none panel alone.
public struct MarkerPair: Equatable, Sendable {
    public let treatment: MarkerSpec
    public let control: MarkerSpec

    public init(treatment: MarkerSpec, control: MarkerSpec) {
        self.treatment = treatment
        self.control = control
    }

    public var visualsMatch: Bool {
        treatment.visual == control.visual
    }

    public var framesDisjoint: Bool {
        !treatment.frame.cgRect.intersects(control.frame.cgRect)
    }

    public static func layout(
        visibleFrame: CGRect,
        markerWidth: Double = 360,
        markerHeight: Double = 220,
        gap: Double = 24
    ) -> MarkerPair {
        let width = markerWidth
        let height = markerHeight
        let visual = MarkerVisualFingerprint(
            headline: "ESCALIER SYNTHETIC MARKER",
            subheadline: "Local capture/focus fixture — not a stealth claim",
            backgroundColorHex: "#10151C",
            roiColorHex: "#FF00AA",
            roiRelativeRect: RectCodable(x: 24, y: 24, width: 96, height: 72),
            windowWidth: width,
            windowHeight: height,
            styleMaskRaw: WindowOptionNames.nonactivatingPanelStyleMaskRaw,
            levelRaw: WindowOptionNames.floatingLevelRaw,
            alpha: 1,
            hasShadow: false,
            isOpaque: true,
            collectionBehaviorRaw: FixturePolicies.markerCollectionBehaviorRaw,
            title: FixturePolicies.markerTitle
        )

        let sideBySideWidth = width * 2 + gap * 3
        let treatmentFrame: RectCodable
        let controlFrame: RectCodable

        if Double(visibleFrame.width) >= sideBySideWidth {
            let y = Double(visibleFrame.midY) - height / 2
            treatmentFrame = RectCodable(
                x: Double(visibleFrame.minX) + gap,
                y: y,
                width: width,
                height: height
            )
            controlFrame = RectCodable(
                x: Double(visibleFrame.maxX) - width - gap,
                y: y,
                width: width,
                height: height
            )
        } else {
            let x = Double(visibleFrame.midX) - width / 2
            let treatmentY = Double(visibleFrame.midY) + gap / 2
            let controlY = Double(visibleFrame.midY) - height - gap / 2
            let minY = Double(visibleFrame.minY)
            let maxY = Double(visibleFrame.maxY) - height
            treatmentFrame = RectCodable(
                x: x,
                y: min(max(treatmentY, minY), maxY),
                width: width,
                height: height
            )
            controlFrame = RectCodable(
                x: x,
                y: min(max(controlY, minY), maxY),
                width: width,
                height: height
            )
        }

        return MarkerPair(
            treatment: MarkerSpec(
                role: .sharingNoneMarker,
                sharing: .sharingNone,
                frame: treatmentFrame,
                visual: visual
            ),
            control: MarkerSpec(
                role: .sharingReadOnlyMarker,
                sharing: .sharingReadOnly,
                frame: controlFrame,
                visual: visual
            )
        )
    }
}
