import Foundation
import CoreGraphics

public struct RectCodable: Codable, Equatable, Sendable {
    public let x: Double
    public let y: Double
    public let width: Double
    public let height: Double

    public init(x: Double, y: Double, width: Double, height: Double) {
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    }

    public init(_ rect: CGRect) {
        self.init(
            x: Double(rect.origin.x),
            y: Double(rect.origin.y),
            width: Double(rect.size.width),
            height: Double(rect.size.height)
        )
    }

    public var cgRect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }

    public var isEmpty: Bool {
        width <= 0 || height <= 0
    }
}

/// Raw AppKit option values used by the pure policy layer. Tests compare these
/// constants against AppKit's own raw values without constructing windows.
public enum WindowOptionNames {
    public static let borderlessStyleMaskRaw: UInt = 0
    public static let titledStyleMaskRaw: UInt = 1
    public static let closableStyleMaskRaw: UInt = 2
    public static let miniaturizableStyleMaskRaw: UInt = 4
    public static let resizableStyleMaskRaw: UInt = 8
    public static let utilityWindowStyleMaskRaw: UInt = 16
    public static let nonactivatingPanelStyleMaskRaw: UInt = 128
    public static let unifiedTitleAndToolbarStyleMaskRaw: UInt = 4_096
    public static let hudWindowStyleMaskRaw: UInt = 8_192
    public static let fullScreenStyleMaskRaw: UInt = 16_384
    public static let fullSizeContentViewStyleMaskRaw: UInt = 32_768

    public static let normalLevelRaw: Int = 0
    public static let floatingLevelRaw: Int = 3
    public static let statusBarLevelRaw: Int = 25

    public static let canJoinAllSpacesRaw: UInt = 1
    public static let moveToActiveSpaceRaw: UInt = 2
    public static let stationaryRaw: UInt = 16
    public static let participatesInCycleRaw: UInt = 32
    public static let ignoresCycleRaw: UInt = 64
    public static let fullScreenPrimaryRaw: UInt = 128
    public static let fullScreenAuxiliaryRaw: UInt = 256

    public static let regularActivationRaw: Int = 0
    public static let accessoryActivationRaw: Int = 1
    public static let prohibitedActivationRaw: Int = 2

    private static let styleMaskFlags: [(raw: UInt, name: String)] = [
        (titledStyleMaskRaw, "titled"),
        (closableStyleMaskRaw, "closable"),
        (miniaturizableStyleMaskRaw, "miniaturizable"),
        (resizableStyleMaskRaw, "resizable"),
        (utilityWindowStyleMaskRaw, "utilityWindow"),
        (nonactivatingPanelStyleMaskRaw, "nonactivatingPanel"),
        (unifiedTitleAndToolbarStyleMaskRaw, "unifiedTitleAndToolbar"),
        (hudWindowStyleMaskRaw, "hudWindow"),
        (fullScreenStyleMaskRaw, "fullScreen"),
        (fullSizeContentViewStyleMaskRaw, "fullSizeContentView")
    ]

    private static let collectionBehaviorFlags: [(raw: UInt, name: String)] = [
        (canJoinAllSpacesRaw, "canJoinAllSpaces"),
        (moveToActiveSpaceRaw, "moveToActiveSpace"),
        (stationaryRaw, "stationary"),
        (participatesInCycleRaw, "participatesInCycle"),
        (ignoresCycleRaw, "ignoresCycle"),
        (fullScreenPrimaryRaw, "fullScreenPrimary"),
        (fullScreenAuxiliaryRaw, "fullScreenAuxiliary")
    ]

    public static func styleMaskNames(forRaw raw: UInt) -> [String] {
        if raw == 0 {
            return ["borderless"]
        }
        var names = styleMaskFlags.filter { raw & $0.raw != 0 }.map(\.name)
        if raw & titledStyleMaskRaw == 0 {
            names.insert("borderless", at: 0)
        }
        let known = styleMaskFlags.reduce(UInt(0)) { $0 | $1.raw }
        let unknown = raw & ~known
        if unknown != 0 {
            names.append("unknown-bits-\(unknown)")
        }
        return names
    }

    public static func levelName(forRaw raw: Int) -> String {
        switch raw {
        case normalLevelRaw:
            return "normal"
        case floatingLevelRaw:
            return "floating"
        case statusBarLevelRaw:
            return "statusBar"
        default:
            return "level-\(raw)"
        }
    }

    public static func collectionBehaviorNames(forRaw raw: UInt) -> [String] {
        if raw == 0 {
            return ["default"]
        }
        var names = collectionBehaviorFlags.filter { raw & $0.raw != 0 }.map(\.name)
        let known = collectionBehaviorFlags.reduce(UInt(0)) { $0 | $1.raw }
        let unknown = raw & ~known
        if unknown != 0 {
            names.append("unknown-bits-\(unknown)")
        }
        return names
    }

    public static func activationPolicyName(forRaw raw: Int) -> String {
        switch raw {
        case regularActivationRaw:
            return "regular"
        case accessoryActivationRaw:
            return "accessory"
        case prohibitedActivationRaw:
            return "prohibited"
        default:
            return "unknown-\(raw)"
        }
    }
}
