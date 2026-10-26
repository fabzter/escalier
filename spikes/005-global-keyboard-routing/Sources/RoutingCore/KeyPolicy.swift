import Foundation

/// Fixed physical-key universe for a US-layout manual probe. Key codes outside this
/// universe pass through untouched and never trigger Unicode extraction.
public enum KeyRole: String, Equatable, Sendable {
    case printable
    case backspace
    case forwardDelete
    case returnKey
    case tab
    case escape
    case navigation
    case modifier
    case unknown
}

public enum KeyPolicy {
    public static let escapeKeyCode: UInt16 = 53
    public static let backspaceKeyCode: UInt16 = 51
    public static let forwardDeleteKeyCode: UInt16 = 117
    public static let returnKeyCode: UInt16 = 36
    public static let tabKeyCode: UInt16 = 48
    public static let spaceKeyCode: UInt16 = 49

    /// Left/right command, shift, option, control, caps lock and fn.
    public static let modifierKeyCodes: Set<UInt16> = [
        54, 55, 56, 57, 58, 59, 60, 61, 62, 63
    ]

    /// Arrow keys, Home/End and PageUp/PageDown.
    public static let navigationKeyCodes: Set<UInt16> = [
        123, 124, 125, 126, 115, 119, 116, 121
    ]

    /// US-layout printable physical keys: letters, digits, punctuation and Space.
    public static let printableKeyCodes: Set<UInt16> = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17,
        18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
        30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47,
        49, 50
    ]

    public static func role(for keyCode: UInt16) -> KeyRole {
        if modifierKeyCodes.contains(keyCode) { return .modifier }
        if keyCode == escapeKeyCode { return .escape }
        if keyCode == backspaceKeyCode { return .backspace }
        if keyCode == forwardDeleteKeyCode { return .forwardDelete }
        if keyCode == returnKeyCode { return .returnKey }
        if keyCode == tabKeyCode { return .tab }
        if navigationKeyCodes.contains(keyCode) { return .navigation }
        if printableKeyCodes.contains(keyCode) { return .printable }
        return .unknown
    }

    public static func isModifierKey(_ keyCode: UInt16) -> Bool {
        modifierKeyCodes.contains(keyCode)
    }

    public static func isPrintable(_ keyCode: UInt16) -> Bool {
        role(for: keyCode) == .printable
    }
}
