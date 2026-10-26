import Foundation

public enum ClickThroughMode: String, CaseIterable, Codable, Sendable {
    case intercept = "intercept-clicks"
    case passThrough = "pass-through-clicks"

    public var ignoresMouseEvents: Bool {
        self == .passThrough
    }

    public static func matching(ignoresMouseEvents: Bool) -> ClickThroughMode {
        ignoresMouseEvents ? .passThrough : .intercept
    }
}

public enum ClickThroughCounterError: Error, Equatable {
    case negativeValue
}

public struct ClickThroughCounters: Codable, Equatable, Sendable {
    public var mode: ClickThroughMode
    public var ignoresMouseEventsRequested: Bool
    public var panelHits: Int
    public var browserUnderlayHits: Int
    public let underlayCountSource: String
    public let note: String

    public init(
        mode: ClickThroughMode = .intercept,
        panelHits: Int = 0,
        browserUnderlayHits: Int = 0,
        underlayCountSource: String = "manual entry from the browser fixture's inert underlay button counter",
        note: String = "Clicks are inert test hits only; no real actions or external side effects."
    ) {
        self.mode = mode
        self.ignoresMouseEventsRequested = mode.ignoresMouseEvents
        self.panelHits = panelHits
        self.browserUnderlayHits = browserUnderlayHits
        self.underlayCountSource = underlayCountSource
        self.note = note
    }

    public mutating func setMode(_ mode: ClickThroughMode) {
        self.mode = mode
        self.ignoresMouseEventsRequested = mode.ignoresMouseEvents
    }

    public mutating func recordPanelHit() {
        panelHits += 1
    }

    public mutating func recordBrowserUnderlayHits(_ value: Int) throws {
        guard value >= 0 else {
            throw ClickThroughCounterError.negativeValue
        }
        browserUnderlayHits = value
    }
}
