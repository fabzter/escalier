import Foundation

/// Bounded in-memory text store. It never grows beyond the configured UTF-16 budget
/// and never splits a Unicode scalar while truncating.
public struct TextBuffer: Equatable, Sendable {
    public private(set) var text: String
    public private(set) var isTruncated: Bool
    public let perEventUTF16Limit: Int
    public let retainedUTF16Limit: Int

    public init(perEventUTF16Limit: Int = 128, retainedUTF16Limit: Int = 1024) {
        self.text = ""
        self.isTruncated = false
        self.perEventUTF16Limit = perEventUTF16Limit
        self.retainedUTF16Limit = retainedUTF16Limit
    }

    public var utf16Count: Int {
        text.utf16.count
    }

    public mutating func clear() {
        text = ""
        isTruncated = false
    }

    /// Accepts at most `perEventUTF16Limit` UTF-16 units from one supplied event,
    /// stopping before a scalar that would cross the boundary. Then appends only what
    /// fits in the retained budget. Every drop is surfaced, never silent.
    @discardableResult
    public mutating func append(_ supplied: String) -> TextAppendResult {
        var accepted = String.UnicodeScalarView()
        var eventUnits = 0
        var eventTruncated = false

        for scalar in supplied.unicodeScalars {
            let width = UTF16.width(scalar)
            if eventUnits + width > perEventUTF16Limit {
                eventTruncated = true
                break
            }
            eventUnits += width
            accepted.append(scalar)
        }

        var remaining = retainedUTF16Limit - text.utf16.count
        var appendedUnits = 0
        var overflowed = false
        var toAppend = String.UnicodeScalarView()

        for scalar in accepted {
            let width = UTF16.width(scalar)
            if width > remaining {
                overflowed = true
                break
            }
            remaining -= width
            appendedUnits += width
            toAppend.append(scalar)
        }

        if appendedUnits > 0 {
            text.unicodeScalars.append(contentsOf: toAppend)
        }
        if eventTruncated || overflowed {
            isTruncated = true
        }

        return TextAppendResult(
            appendedUTF16: appendedUnits,
            eventTruncated: eventTruncated,
            bufferOverflowed: overflowed,
            textUTF16Count: text.utf16.count
        )
    }

    /// Removes the previous complete extended grapheme cluster. Empty buffer is a no-op.
    @discardableResult
    public mutating func removePreviousGrapheme() -> Bool {
        guard !text.isEmpty else { return false }
        text.removeLast()
        return true
    }

    /// Forward Delete is documented as an end-of-buffer no-op in this fixture.
    @discardableResult
    public mutating func forwardDeleteAtEnd() -> Bool {
        false
    }
}
