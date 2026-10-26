import Foundation

public enum ConversationPhase: String, Equatable, CaseIterable {
    case preparation
    case conversation

    public var label: String {
        switch self {
        case .preparation: return "Preparation"
        case .conversation: return "Live conversation"
        }
    }
}

public enum TranscriptSource: String, Equatable, CaseIterable, Identifiable {
    case me
    case otherSide

    public var id: String { rawValue }

    public var displayName: String {
        switch self {
        case .me: return "Me"
        case .otherSide: return "Other side"
        }
    }

    public var badge: String {
        switch self {
        case .me: return "ME"
        case .otherSide: return "OTHER SIDE"
        }
    }
}

public struct TranscriptEntry: Identifiable, Equatable {
    public let id: UUID
    public let source: TranscriptSource
    public let text: String
    public let sequence: Int
    public let synthetic: Bool

    public init(
        id: UUID = UUID(),
        source: TranscriptSource,
        text: String,
        sequence: Int,
        synthetic: Bool = true
    ) {
        self.id = id
        self.source = source
        self.text = text
        self.sequence = sequence
        self.synthetic = synthetic
    }
}

public enum SourceKind: String, Equatable {
    case document
    case note

    public var label: String {
        switch self {
        case .document: return "Document"
        case .note: return "Note"
        }
    }
}

public struct SourceIdentity: Identifiable, Equatable {
    public let id: String
    public let title: String
    public let kind: SourceKind
    public let synthetic: Bool

    public init(id: String, title: String, kind: SourceKind, synthetic: Bool = true) {
        self.id = id
        self.title = title
        self.kind = kind
        self.synthetic = synthetic
    }
}

public struct Citation: Equatable {
    public let documentTitle: String
    public let locator: String
    public let anchor: String
    public let synthetic: Bool

    public init(
        documentTitle: String,
        locator: String,
        anchor: String,
        synthetic: Bool = true
    ) {
        self.documentTitle = documentTitle
        self.locator = locator
        self.anchor = anchor
        self.synthetic = synthetic
    }
}

/// UTF-16 offsets, matching NSString/AppKit text ranges. Synthetic samples are ASCII,
/// and the UI validates bounds before highlighting.
public struct TextRange: Equatable {
    public let start: Int
    public let length: Int

    public init(start: Int, length: Int) {
        self.start = start
        self.length = length
    }

    public var end: Int { start + length }

    public func isValid(in text: String) -> Bool {
        start >= 0 && length > 0 && end <= (text as NSString).length
    }
}

public struct ReferenceSelection: Equatable {
    public let candidateID: String
    public let range: TextRange
    public let anchor: String

    public init(candidateID: String, range: TextRange, anchor: String) {
        self.candidateID = candidateID
        self.range = range
        self.anchor = anchor
    }
}

public struct ReferenceCandidate: Identifiable, Equatable {
    public let id: String
    public let source: SourceIdentity
    public let citation: Citation
    public let excerpt: String
    public let range: TextRange

    public init(
        id: String,
        source: SourceIdentity,
        citation: Citation,
        excerpt: String,
        range: TextRange
    ) {
        self.id = id
        self.source = source
        self.citation = citation
        self.excerpt = excerpt
        self.range = range
    }

    public var selection: ReferenceSelection {
        ReferenceSelection(
            candidateID: id,
            range: range,
            anchor: "\(citation.anchor)#L\(range.start)"
        )
    }
}

public enum ReferenceUnresolvedReason: String, Equatable {
    case selectedCandidateRemoved

    public var label: String {
        switch self {
        case .selectedCandidateRemoved:
            return "The selected synthetic reference was removed. Choose another candidate explicitly; the prototype did not jump to one."
        }
    }
}

/// Pure reference-panel presentation state. Candidate arrival never moves a selected
/// source. Navigation moves it explicitly. Removal of the selected source is unresolved.
public struct ReferenceState: Equatable {
    public private(set) var candidates: [ReferenceCandidate]
    public private(set) var selectedSelection: ReferenceSelection?
    public private(set) var unseenCandidateIDs: Set<String>
    public private(set) var unresolvedReason: ReferenceUnresolvedReason?

    public init(candidates: [ReferenceCandidate] = [], selectedCandidateID: String? = nil) {
        var uniqueCandidates: [ReferenceCandidate] = []
        var seenIDs = Set<String>()
        for candidate in candidates where seenIDs.insert(candidate.id).inserted {
            uniqueCandidates.append(candidate)
        }
        self.candidates = uniqueCandidates
        self.unseenCandidateIDs = []
        self.unresolvedReason = nil
        if let selectedCandidateID,
           let selected = uniqueCandidates.first(where: { $0.id == selectedCandidateID }) {
            self.selectedSelection = selected.selection
        } else {
            self.selectedSelection = nil
        }
    }

    public var selectedCandidateID: String? { selectedSelection?.candidateID }
    public var selectedRange: TextRange? { selectedSelection?.range }
    public var selectedAnchor: String? { selectedSelection?.anchor }
    public var selectedCandidate: ReferenceCandidate? {
        guard let selectedCandidateID else { return nil }
        return candidates.first { $0.id == selectedCandidateID }
    }
    public var hasNewCandidateIndicator: Bool { !unseenCandidateIDs.isEmpty }

    /// Adds another synthetic candidate without changing the passage currently read.
    /// The only automatic selection is the first selection in an empty, unresolved-free panel.
    @discardableResult
    public mutating func arrive(_ candidate: ReferenceCandidate) -> Bool {
        guard !candidates.contains(where: { $0.id == candidate.id }) else { return false }
        candidates.append(candidate)
        if selectedSelection == nil && unresolvedReason == nil {
            selectedSelection = candidate.selection
        } else {
            unseenCandidateIDs.insert(candidate.id)
        }
        return true
    }

    @discardableResult
    public mutating func selectNext() -> ReferenceSelection? {
        guard !candidates.isEmpty else { return nil }
        let currentIndex = candidates.firstIndex { $0.id == selectedSelection?.candidateID }
        let nextIndex = currentIndex.map { ($0 + 1) % candidates.count } ?? 0
        selectedSelection = candidates[nextIndex].selection
        unresolvedReason = nil
        unseenCandidateIDs.removeAll()
        return selectedSelection
    }

    @discardableResult
    public mutating func selectPrevious() -> ReferenceSelection? {
        guard !candidates.isEmpty else { return nil }
        let currentIndex = candidates.firstIndex { $0.id == selectedSelection?.candidateID }
        let previousIndex = currentIndex.map { ($0 - 1 + candidates.count) % candidates.count }
            ?? (candidates.count - 1)
        selectedSelection = candidates[previousIndex].selection
        unresolvedReason = nil
        unseenCandidateIDs.removeAll()
        return selectedSelection
    }

    @discardableResult
    public mutating func selectCandidate(id: String) -> ReferenceSelection? {
        guard let candidate = candidates.first(where: { $0.id == id }) else { return nil }
        selectedSelection = candidate.selection
        unresolvedReason = nil
        unseenCandidateIDs.removeAll()
        return selectedSelection
    }

    @discardableResult
    public mutating func removeCandidate(id: String) -> Bool {
        guard let index = candidates.firstIndex(where: { $0.id == id }) else { return false }
        let wasSelected = selectedSelection?.candidateID == id
        candidates.remove(at: index)
        unseenCandidateIDs.remove(id)
        if wasSelected {
            selectedSelection = nil
            unresolvedReason = .selectedCandidateRemoved
        }
        return true
    }
}

public enum IntegrationStatus: String, Equatable {
    case mock = "MOCK"
    case notConnected = "NOT CONNECTED"
}

/// The prototype never claims a connected runtime capability. The related
/// 005-global-keyboard-routing spike owns active interception outside this shell.
public struct PrototypeRuntimeStatus: Equatable {
    public let modelSelection: IntegrationStatus
    public let toolSkillSelection: IntegrationStatus
    public let input: IntegrationStatus
    public let permissions: IntegrationStatus
    public let omp: IntegrationStatus
    public let screenshotCapture: IntegrationStatus
    public let globalShortcutRouting: IntegrationStatus

    public init(
        modelSelection: IntegrationStatus,
        toolSkillSelection: IntegrationStatus,
        input: IntegrationStatus,
        permissions: IntegrationStatus,
        omp: IntegrationStatus,
        screenshotCapture: IntegrationStatus,
        globalShortcutRouting: IntegrationStatus
    ) {
        self.modelSelection = modelSelection
        self.toolSkillSelection = toolSkillSelection
        self.input = input
        self.permissions = permissions
        self.omp = omp
        self.screenshotCapture = screenshotCapture
        self.globalShortcutRouting = globalShortcutRouting
    }

    public static let prototype = PrototypeRuntimeStatus(
        modelSelection: .mock,
        toolSkillSelection: .mock,
        input: .notConnected,
        permissions: .notConnected,
        omp: .notConnected,
        screenshotCapture: .notConnected,
        globalShortcutRouting: .notConnected
    )
}
