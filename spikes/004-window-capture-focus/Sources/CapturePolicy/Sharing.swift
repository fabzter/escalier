import Foundation

public enum SharingPolicy: String, CaseIterable, Codable, Sendable {
    case sharingNone = "sharing-none"
    case sharingReadOnly = "sharing-readOnly"

    public var appKitRawValue: UInt {
        switch self {
        case .sharingNone:
            return 0
        case .sharingReadOnly:
            return 1
        }
    }

    public var summary: String {
        switch self {
        case .sharingNone:
            return "NSWindow.SharingType.none (legacy; not a modern capture guarantee)"
        case .sharingReadOnly:
            return "NSWindow.SharingType.readOnly"
        }
    }

    public var isLegacyNone: Bool {
        self == .sharingNone
    }

    public static func observedName(forRaw raw: UInt) -> String {
        switch raw {
        case 0:
            return SharingPolicy.sharingNone.rawValue
        case 1:
            return SharingPolicy.sharingReadOnly.rawValue
        case 2:
            return "sharing-readWrite-deprecated"
        default:
            return "sharing-unknown-\(raw)"
        }
    }
}

public enum FixtureWindowRole: String, CaseIterable, Codable, Sendable {
    case controlWindow = "control-window"
    case sharingNoneMarker = "marker-sharing-none"
    case sharingReadOnlyMarker = "marker-sharing-read-only"
    case auxiliaryPanel = "auxiliary-panel"
    case clickThroughPanel = "click-through-panel"

    public static let readbackOrder: [FixtureWindowRole] = [
        .controlWindow,
        .sharingNoneMarker,
        .sharingReadOnlyMarker,
        .auxiliaryPanel,
        .clickThroughPanel
    ]

    public var expectedSharing: SharingPolicy {
        switch self {
        case .sharingNoneMarker, .auxiliaryPanel:
            return .sharingNone
        case .controlWindow, .sharingReadOnlyMarker, .clickThroughPanel:
            return .sharingReadOnly
        }
    }

    public var displayLabel: String {
        switch self {
        case .controlWindow:
            return "Control window"
        case .sharingNoneMarker:
            return "Marker — sharing-none (treatment)"
        case .sharingReadOnlyMarker:
            return "Marker — sharing-readOnly (control)"
        case .auxiliaryPanel:
            return "Auxiliary panel (separate row)"
        case .clickThroughPanel:
            return "Click-through panel (inert)"
        }
    }

    public var isMarker: Bool {
        self == .sharingNoneMarker || self == .sharingReadOnlyMarker
    }

    public static func markerRole(for policy: SharingPolicy) -> FixtureWindowRole {
        switch policy {
        case .sharingNone:
            return .sharingNoneMarker
        case .sharingReadOnly:
            return .sharingReadOnlyMarker
        }
    }
}
