import AppKit

enum HexColor {
    static func color(_ hexadecimal: String, fallback: NSColor = .magenta) -> NSColor {
        let cleaned = hexadecimal.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        guard cleaned.count == 6 else { return fallback }
        var value: UInt64 = 0
        guard Scanner(string: cleaned).scanHexInt64(&value) else { return fallback }
        let red = CGFloat((value >> 16) & 0xFF) / 255
        let green = CGFloat((value >> 8) & 0xFF) / 255
        let blue = CGFloat(value & 0xFF) / 255
        return NSColor(srgbRed: red, green: green, blue: blue, alpha: 1)
    }
}
