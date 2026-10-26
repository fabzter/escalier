import XCTest
import EscalierCore

final class AssistanceAndStreamingTests: XCTestCase {
    func testStreamingChunksAppendInOrderUnderStableMessageID() {
        var conversation = TestFixtures.conversation(phase: .conversation)

        let messageID = conversation.beginStreamingAssistance(kind: .suggestedWording)
        XCTAssertNotNil(conversation.assistance.first(where: { $0.id == messageID }))
        XCTAssertTrue(conversation.appendAssistanceChunk("Synthetic ", to: messageID))
        XCTAssertTrue(conversation.appendAssistanceChunk("streamed ", to: messageID))
        XCTAssertTrue(conversation.appendAssistanceChunk("wording.", to: messageID))
        XCTAssertTrue(conversation.completeAssistanceMessage(messageID))

        guard let message = conversation.assistance.first(where: { $0.id == messageID }) else {
            return XCTFail("Stable streaming message identity was lost")
        }
        XCTAssertEqual(message.chunks, ["Synthetic ", "streamed ", "wording."])
        XCTAssertEqual(message.text, "Synthetic streamed wording.")
        XCTAssertFalse(message.isStreaming)
        XCTAssertEqual(message.kind, .suggestedWording)
        XCTAssertEqual(conversation.assistance.count, 1)
    }

    func testUnknownOrCompletedStreamingMessageRejectsLateChunks() {
        var conversation = TestFixtures.conversation(phase: .conversation)
        XCTAssertFalse(conversation.appendAssistanceChunk("orphan", to: UUID()))
        XCTAssertFalse(conversation.completeAssistanceMessage(UUID()))
        XCTAssertTrue(conversation.assistance.isEmpty)

        let messageID = conversation.beginStreamingAssistance(kind: .sourceBacked)
        XCTAssertTrue(conversation.appendAssistanceChunk("First.", to: messageID))
        XCTAssertTrue(conversation.completeAssistanceMessage(messageID))
        XCTAssertFalse(conversation.appendAssistanceChunk(" Late.", to: messageID))
        XCTAssertFalse(conversation.completeAssistanceMessage(messageID))
        XCTAssertEqual(conversation.assistance.first?.text, "First.")
    }

    func testCompleteLocalDiagramHasAltTextAndNoProgressiveDelivery() {
        var conversation = TestFixtures.conversation(phase: .conversation)
        let diagram = SampleContent.localDiagram

        let message = conversation.addCompleteLocalDiagram(diagram)

        XCTAssertEqual(message.kind, .localImage)
        XCTAssertFalse(message.isStreaming)
        XCTAssertTrue(message.chunks.isEmpty)
        XCTAssertEqual(message.localDiagram?.altText, diagram.altText)
        XCTAssertFalse(diagram.altText.isEmpty)
        XCTAssertEqual(diagram.completeness, .complete)
        XCTAssertTrue(diagram.synthetic)
        XCTAssertEqual(conversation.assistance.count, 1)
    }

    func testAssistanceProvenanceKindsAreDistinctAndLabelled() {
        let labels = Set(AssistanceKind.allCases.map(\.label))
        XCTAssertEqual(labels.count, AssistanceKind.allCases.count)
        XCTAssertTrue(AssistanceKind.sourceBacked.label.lowercased().contains("source"))
        XCTAssertTrue(AssistanceKind.suggestedWording.label.lowercased().contains("suggest"))
        XCTAssertTrue(AssistanceKind.generalInformation.label.lowercased().contains("general"))
        XCTAssertTrue(AssistanceKind.localImage.label.lowercased().contains("image"))

        let sample = SampleContent.liveConversation()
        let sampleKinds = Set(sample.assistance.map(\.kind))
        XCTAssertTrue(sampleKinds.isSuperset(of: [
            .sourceBacked,
            .suggestedWording,
            .generalInformation,
            .localImage
        ]))
    }

    func testAssistanceHistoryPreservesInsertionOrder() {
        var conversation = TestFixtures.conversation(phase: .conversation)
        let sourceID = conversation.beginStreamingAssistance(kind: .sourceBacked)
        XCTAssertTrue(conversation.appendAssistanceChunk("Source-backed.", to: sourceID))
        XCTAssertTrue(conversation.completeAssistanceMessage(sourceID))
        _ = conversation.addCompleteLocalDiagram(SampleContent.localDiagram)
        let generalID = conversation.beginStreamingAssistance(kind: .generalInformation)
        XCTAssertTrue(conversation.appendAssistanceChunk("General.", to: generalID))
        XCTAssertTrue(conversation.completeAssistanceMessage(generalID))

        XCTAssertEqual(
            conversation.assistance.map(\.kind),
            [.sourceBacked, .localImage, .generalInformation]
        )
    }

    func testSyntheticStreamAdvancesIncrementallyUnderOneStableIdentity() {
        let conversation = TestFixtures.conversation(phase: .conversation)
        let store = ConversationStore(
            conversations: [conversation],
            selectedConversationID: conversation.id
        )

        var messageIDs: [UUID] = []
        for _ in 0..<SyntheticStreamDemo.steps.count {
            guard let messageID = store.advanceSyntheticStream() else {
                return XCTFail("Synthetic stream step did not return a message identity")
            }
            messageIDs.append(messageID)
        }

        XCTAssertEqual(Set(messageIDs).count, 1)
        guard let message = store.currentConversation?.assistance.first else {
            return XCTFail("Synthetic stream message missing")
        }
        XCTAssertEqual(message.chunks, SyntheticStreamDemo.steps)
        XCTAssertEqual(message.text, SyntheticStreamDemo.steps.joined())
        XCTAssertFalse(message.isStreaming)
        XCTAssertEqual(store.currentConversation?.assistance.count, 1)
    }
}
