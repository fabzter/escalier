import Foundation

public enum AssistanceKind: String, CaseIterable, Identifiable, Equatable {
    case sourceBacked
    case suggestedWording
    case generalInformation
    case localImage

    public var id: String { rawValue }

    public var label: String {
        switch self {
        case .sourceBacked: return "Source-backed knowledge"
        case .suggestedWording: return "Suggested wording"
        case .generalInformation: return "General information"
        case .localImage: return "Local vector image"
        }
    }

    public var provenanceLabel: String {
        switch self {
        case .sourceBacked: return "SOURCE-BACKED"
        case .suggestedWording: return "SUGGESTED WORDING"
        case .generalInformation: return "GENERAL INFORMATION"
        case .localImage: return "LOCAL IMAGE"
        }
    }

    public var isImage: Bool { self == .localImage }
}

public enum ImageCompleteness: String, Equatable {
    case complete

    public var label: String {
        switch self {
        case .complete: return "COMPLETE"
        }
    }
}

/// A local, harmlessly invented vector diagram. The shell draws it from native shapes;
/// no image is generated, downloaded or streamed progressively.
public struct LocalDiagram: Identifiable, Equatable {
    public let id: UUID
    public let title: String
    public let altText: String
    public let completeness: ImageCompleteness
    public let synthetic: Bool

    public init(
        id: UUID = UUID(),
        title: String,
        altText: String,
        completeness: ImageCompleteness = .complete,
        synthetic: Bool = true
    ) {
        self.id = id
        self.title = title
        self.altText = altText
        self.completeness = completeness
        self.synthetic = synthetic
    }
}

public struct AssistanceMessage: Identifiable, Equatable {
    public let id: UUID
    public let kind: AssistanceKind
    public private(set) var chunks: [String]
    public private(set) var isStreaming: Bool
    public let localDiagram: LocalDiagram?

    public init(
        id: UUID = UUID(),
        kind: AssistanceKind,
        chunks: [String] = [],
        isStreaming: Bool = false,
        localDiagram: LocalDiagram? = nil
    ) {
        self.id = id
        self.kind = kind
        self.chunks = chunks
        self.isStreaming = isStreaming
        self.localDiagram = localDiagram
    }

    public var text: String { chunks.joined() }

    @discardableResult
    mutating func appendChunk(_ chunk: String) -> Bool {
        guard isStreaming else { return false }
        chunks.append(chunk)
        return true
    }

    @discardableResult
    mutating func markComplete() -> Bool {
        guard isStreaming else { return false }
        isStreaming = false
        return true
    }
}

public enum AssistanceAction: String, CaseIterable, Identifiable, Equatable {
    case findSource = "find-source"
    case answerLatestQuestion = "answer-latest-question"
    case formulatePoint = "formulate-point"
    case wayForward = "way-forward"
    case interpretScreenshot = "interpret-screenshot"

    public var id: String { rawValue }

    public var label: String {
        switch self {
        case .findSource: return "Find relevant source material"
        case .answerLatestQuestion: return "Answer latest question"
        case .formulatePoint: return "Formulate my recent point"
        case .wayForward: return "Find a way forward"
        case .interpretScreenshot: return "Interpret screenshot"
        }
    }

    public var route: String { "/assist/\(rawValue)" }

    public var shortcutHint: String {
        switch self {
        case .findSource: return "⌘1"
        case .answerLatestQuestion: return "⌘2"
        case .formulatePoint: return "⌘3"
        case .wayForward: return "⌘4"
        case .interpretScreenshot: return "⌘5"
        }
    }

    public var keyEquivalent: String {
        switch self {
        case .findSource: return "1"
        case .answerLatestQuestion: return "2"
        case .formulatePoint: return "3"
        case .wayForward: return "4"
        case .interpretScreenshot: return "5"
        }
    }

    public var routingSummary: String {
        switch self {
        case .interpretScreenshot:
            return "Interpret screenshot → \(route) (synthetic log only; no screenshot is captured)"
        default:
            return "\(label) → \(route) (synthetic log only; no assistance generated)"
        }
    }
}

public struct RetrievalLogEntry: Identifiable, Equatable {
    public let id: UUID
    public let action: AssistanceAction
    public let route: String
    public let summary: String
    public let synthetic: Bool

    public init(
        id: UUID = UUID(),
        action: AssistanceAction,
        route: String,
        summary: String,
        synthetic: Bool = true
    ) {
        self.id = id
        self.action = action
        self.route = route
        self.summary = summary
        self.synthetic = synthetic
    }
}

/// Fixed invented chunks used only by the manual "advance synthetic stream" control.
public enum SyntheticStreamDemo {
    public static let steps = [
        "Synthetic ",
        "suggested ",
        "wording ",
        "arrives ",
        "incrementally."
    ]
}
