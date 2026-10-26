import Foundation
import Combine

/// Headless presentation store. All state is synthetic and in memory. Mutations are
/// scoped to the selected conversation; this class performs no persistence or I/O.
public final class ConversationStore: ObservableObject {
    @Published public private(set) var conversations: [ConversationState]
    @Published public private(set) var selectedConversationID: UUID?

    public init(conversations: [ConversationState], selectedConversationID: UUID? = nil) {
        self.conversations = conversations
        if let selectedConversationID,
           conversations.contains(where: { $0.id == selectedConversationID }) {
            self.selectedConversationID = selectedConversationID
        } else {
            self.selectedConversationID = conversations.first?.id
        }
    }

    public var currentConversation: ConversationState? {
        guard let selectedConversationID else { return nil }
        return conversations.first { $0.id == selectedConversationID }
    }

    private var currentIndex: Int? {
        guard let selectedConversationID else { return nil }
        return conversations.firstIndex { $0.id == selectedConversationID }
    }

    @discardableResult
    private func mutateCurrent<T>(_ body: (inout ConversationState) -> T) -> T? {
        guard let index = currentIndex else { return nil }
        var conversation = conversations[index]
        let result = body(&conversation)
        conversations[index] = conversation
        return result
    }

    @discardableResult
    public func selectConversation(id: UUID) -> Bool {
        guard conversations.contains(where: { $0.id == id }) else { return false }
        selectedConversationID = id
        return true
    }

    @discardableResult
    public func startConversation() -> Bool {
        mutateCurrent { $0.startConversation() } ?? false
    }

    @discardableResult
    public func arriveReferenceCandidate(_ candidate: ReferenceCandidate) -> Bool {
        mutateCurrent { $0.arriveReferenceCandidate(candidate) } ?? false
    }

    @discardableResult
    public func selectNextReference() -> ReferenceSelection? {
        guard let selection = mutateCurrent({ $0.selectNextReference() }) else { return nil }
        return selection
    }

    @discardableResult
    public func selectPreviousReference() -> ReferenceSelection? {
        guard let selection = mutateCurrent({ $0.selectPreviousReference() }) else { return nil }
        return selection
    }

    @discardableResult
    public func selectReferenceCandidate(id: String) -> ReferenceSelection? {
        guard let selection = mutateCurrent({ $0.selectReferenceCandidate(id: id) }) else {
            return nil
        }
        return selection
    }

    @discardableResult
    public func removeReferenceCandidate(id: String) -> Bool {
        mutateCurrent { $0.removeReferenceCandidate(id: id) } ?? false
    }

    @discardableResult
    public func setModel(id: String?) -> Bool {
        mutateCurrent { $0.setSelectedModel(id: id) } ?? false
    }

    @discardableResult
    public func toggleTool(id: String) -> Bool {
        mutateCurrent { $0.toggleTool(id: id) } ?? false
    }

    @discardableResult
    public func toggleSkill(id: String) -> Bool {
        mutateCurrent { $0.toggleSkill(id: id) } ?? false
    }

    @discardableResult
    public func dispatchAssistanceAction(_ action: AssistanceAction) -> RetrievalLogEntry? {
        mutateCurrent { $0.dispatchAssistanceAction(action) }
    }

    @discardableResult
    public func beginStreamingAssistance(kind: AssistanceKind) -> UUID? {
        mutateCurrent { $0.beginStreamingAssistance(kind: kind) }
    }

    @discardableResult
    public func appendAssistanceChunk(_ chunk: String, to messageID: UUID) -> Bool {
        mutateCurrent { $0.appendAssistanceChunk(chunk, to: messageID) } ?? false
    }

    @discardableResult
    public func completeAssistanceMessage(_ messageID: UUID) -> Bool {
        mutateCurrent { $0.completeAssistanceMessage(messageID) } ?? false
    }

    @discardableResult
    public func addCompleteLocalDiagram(_ diagram: LocalDiagram) -> AssistanceMessage? {
        mutateCurrent { $0.addCompleteLocalDiagram(diagram) }
    }

    @discardableResult
    public func retainCurrentSnapshot() -> RetainedAggregate? {
        mutateCurrent { $0.retainSnapshot() }
    }

    @discardableResult
    public func selectRetainedAggregate(id: UUID) -> Bool {
        mutateCurrent { $0.selectRetainedAggregate(id: id) } ?? false
    }

    @discardableResult
    public func deleteSelectedRetainedAggregate() -> Bool {
        mutateCurrent { $0.deleteSelectedRetainedAggregate() } ?? false
    }

    /// Manual synthetic demo: one stable message receives the next invented chunk.
    /// This is not streaming from a runtime and uses no timer or network.
    @discardableResult
    public func advanceSyntheticStream() -> UUID? {
        guard let index = currentIndex else { return nil }
        var conversation = conversations[index]

        if let messageIndex = conversation.assistance.lastIndex(where: { $0.isStreaming }) {
            let messageID = conversation.assistance[messageIndex].id
            let chunkCount = conversation.assistance[messageIndex].chunks.count
            if chunkCount < SyntheticStreamDemo.steps.count {
                _ = conversation.appendAssistanceChunk(
                    SyntheticStreamDemo.steps[chunkCount],
                    to: messageID
                )
                if chunkCount + 1 >= SyntheticStreamDemo.steps.count {
                    _ = conversation.completeAssistanceMessage(messageID)
                }
            }
            conversations[index] = conversation
            return messageID
        }

        let messageID = conversation.beginStreamingAssistance(kind: .suggestedWording)
        if let firstChunk = SyntheticStreamDemo.steps.first {
            _ = conversation.appendAssistanceChunk(firstChunk, to: messageID)
        }
        if SyntheticStreamDemo.steps.count <= 1 {
            _ = conversation.completeAssistanceMessage(messageID)
        }
        conversations[index] = conversation
        return messageID
    }
}
