import Foundation

public enum RetainedStorage: String, Equatable {
    case inMemorySynthetic = "In-memory synthetic only — no disk data"

    public var label: String { rawValue }
}

/// A value snapshot of synthetic transcript, retrieval log and assistance.
/// It has no file, database or network representation.
public struct RetainedAggregate: Identifiable, Equatable {
    public let id: UUID
    public let conversationTitle: String
    public let transcript: [TranscriptEntry]
    public let retrievalLog: [RetrievalLogEntry]
    public let assistance: [AssistanceMessage]
    public let storage: RetainedStorage

    public init(
        id: UUID = UUID(),
        conversationTitle: String,
        transcript: [TranscriptEntry],
        retrievalLog: [RetrievalLogEntry],
        assistance: [AssistanceMessage],
        storage: RetainedStorage = .inMemorySynthetic
    ) {
        self.id = id
        self.conversationTitle = conversationTitle
        self.transcript = transcript
        self.retrievalLog = retrievalLog
        self.assistance = assistance
        self.storage = storage
    }
}

public struct ConversationState: Identifiable, Equatable {
    public let id: UUID
    public var title: String
    public private(set) var phase: ConversationPhase
    public private(set) var transcript: [TranscriptEntry]
    public private(set) var retrievalLog: [RetrievalLogEntry]
    public private(set) var assistance: [AssistanceMessage]
    public private(set) var reference: ReferenceState
    public private(set) var capabilities: ConversationCapabilities
    public private(set) var retainedAggregates: [RetainedAggregate]
    public private(set) var selectedRetainedAggregateID: UUID?
    public let runtimeStatus: PrototypeRuntimeStatus
    public let synthetic: Bool

    public init(
        id: UUID = UUID(),
        title: String,
        phase: ConversationPhase,
        transcript: [TranscriptEntry] = [],
        retrievalLog: [RetrievalLogEntry] = [],
        assistance: [AssistanceMessage] = [],
        reference: ReferenceState = ReferenceState(),
        capabilities: ConversationCapabilities = .prototypeDefault,
        retainedAggregates: [RetainedAggregate] = [],
        selectedRetainedAggregateID: UUID? = nil,
        runtimeStatus: PrototypeRuntimeStatus = .prototype,
        synthetic: Bool = true
    ) {
        self.id = id
        self.title = title
        self.phase = phase
        self.transcript = transcript
        self.retrievalLog = retrievalLog
        self.assistance = assistance
        self.reference = reference
        self.capabilities = capabilities
        self.retainedAggregates = retainedAggregates
        self.selectedRetainedAggregateID = selectedRetainedAggregateID
        self.runtimeStatus = runtimeStatus
        self.synthetic = synthetic
    }

    public static func synthetic(
        title: String,
        phase: ConversationPhase = .preparation
    ) -> ConversationState {
        ConversationState(title: title, phase: phase)
    }

    @discardableResult
    public mutating func startConversation() -> Bool {
        guard phase == .preparation else { return false }
        phase = .conversation
        return true
    }

    @discardableResult
    public mutating func appendTranscript(
        source: TranscriptSource,
        text: String
    ) -> TranscriptEntry {
        let entry = TranscriptEntry(
            source: source,
            text: text,
            sequence: transcript.count + 1
        )
        transcript.append(entry)
        return entry
    }

    @discardableResult
    public mutating func dispatchAssistanceAction(
        _ action: AssistanceAction
    ) -> RetrievalLogEntry {
        let entry = RetrievalLogEntry(
            action: action,
            route: action.route,
            summary: action.routingSummary
        )
        retrievalLog.append(entry)
        return entry
    }

    // MARK: Reference forwarding

    @discardableResult
    public mutating func arriveReferenceCandidate(_ candidate: ReferenceCandidate) -> Bool {
        reference.arrive(candidate)
    }

    @discardableResult
    public mutating func selectNextReference() -> ReferenceSelection? {
        reference.selectNext()
    }

    @discardableResult
    public mutating func selectPreviousReference() -> ReferenceSelection? {
        reference.selectPrevious()
    }

    @discardableResult
    public mutating func selectReferenceCandidate(id: String) -> ReferenceSelection? {
        reference.selectCandidate(id: id)
    }

    @discardableResult
    public mutating func removeReferenceCandidate(id: String) -> Bool {
        reference.removeCandidate(id: id)
    }

    // MARK: Mock per-conversation capabilities

    @discardableResult
    public mutating func setSelectedModel(id: String?) -> Bool {
        capabilities.setSelectedModel(id: id)
    }

    @discardableResult
    public mutating func toggleTool(id: String) -> Bool {
        capabilities.toggleTool(id: id)
    }

    @discardableResult
    public mutating func toggleSkill(id: String) -> Bool {
        capabilities.toggleSkill(id: id)
    }

    // MARK: Synthetic assistance stream

    @discardableResult
    public mutating func beginStreamingAssistance(kind: AssistanceKind) -> UUID {
        let message = AssistanceMessage(kind: kind, isStreaming: true)
        assistance.append(message)
        return message.id
    }

    @discardableResult
    public mutating func appendAssistanceChunk(_ chunk: String, to messageID: UUID) -> Bool {
        guard let index = assistance.firstIndex(where: { $0.id == messageID }) else {
            return false
        }
        return assistance[index].appendChunk(chunk)
    }

    @discardableResult
    public mutating func completeAssistanceMessage(_ messageID: UUID) -> Bool {
        guard let index = assistance.firstIndex(where: { $0.id == messageID }) else {
            return false
        }
        return assistance[index].markComplete()
    }

    @discardableResult
    public mutating func addCompleteLocalDiagram(_ diagram: LocalDiagram) -> AssistanceMessage {
        let message = AssistanceMessage(
            kind: .localImage,
            isStreaming: false,
            localDiagram: diagram
        )
        assistance.append(message)
        return message
    }

    // MARK: In-memory retained aggregates

    @discardableResult
    public mutating func retainSnapshot(selecting: Bool = true) -> RetainedAggregate {
        let aggregate = RetainedAggregate(
            conversationTitle: title,
            transcript: transcript,
            retrievalLog: retrievalLog,
            assistance: assistance
        )
        retainedAggregates.append(aggregate)
        if selecting {
            selectedRetainedAggregateID = aggregate.id
        }
        return aggregate
    }

    @discardableResult
    public mutating func selectRetainedAggregate(id: UUID) -> Bool {
        guard retainedAggregates.contains(where: { $0.id == id }) else { return false }
        selectedRetainedAggregateID = id
        return true
    }

    @discardableResult
    public mutating func deleteSelectedRetainedAggregate() -> Bool {
        guard let selectedRetainedAggregateID,
              let index = retainedAggregates.firstIndex(where: { $0.id == selectedRetainedAggregateID })
        else {
            return false
        }
        retainedAggregates.remove(at: index)
        self.selectedRetainedAggregateID = nil
        return true
    }
}
