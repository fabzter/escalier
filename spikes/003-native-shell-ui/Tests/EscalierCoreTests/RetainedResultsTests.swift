import XCTest
import EscalierCore

final class RetainedResultsTests: XCTestCase {
    func testRetainSnapshotCapturesTranscriptRetrievalLogAndAssistance() {
        var conversation = TestFixtures.conversation(phase: .conversation)
        conversation.appendTranscript(source: .me, text: "Synthetic me transcript.")
        conversation.appendTranscript(source: .otherSide, text: "Synthetic other-side transcript.")
        _ = conversation.dispatchAssistanceAction(.answerLatestQuestion)
        let messageID = conversation.beginStreamingAssistance(kind: .suggestedWording)
        XCTAssertTrue(conversation.appendAssistanceChunk("Synthetic ", to: messageID))
        XCTAssertTrue(conversation.appendAssistanceChunk("assistance.", to: messageID))
        XCTAssertTrue(conversation.completeAssistanceMessage(messageID))
        _ = conversation.addCompleteLocalDiagram(SampleContent.localDiagram)

        let retained = conversation.retainSnapshot()

        XCTAssertEqual(retained.transcript, conversation.transcript)
        XCTAssertEqual(retained.retrievalLog, conversation.retrievalLog)
        XCTAssertEqual(retained.assistance, conversation.assistance)
        XCTAssertEqual(retained.transcript.count, 2)
        XCTAssertEqual(retained.retrievalLog.count, 1)
        XCTAssertEqual(retained.assistance.count, 2)
        XCTAssertEqual(retained.storage, .inMemorySynthetic)
        XCTAssertTrue(retained.storage.rawValue.contains("In-memory"))
        XCTAssertTrue(retained.storage.rawValue.lowercased().contains("no disk"))
        XCTAssertEqual(conversation.selectedRetainedAggregateID, retained.id)
    }

    func testRetainedSnapshotIsImmutableAfterLiveMutations() {
        var conversation = TestFixtures.conversation(phase: .conversation)
        conversation.appendTranscript(source: .me, text: "Synthetic original line.")
        let retained = conversation.retainSnapshot()

        conversation.appendTranscript(source: .otherSide, text: "Synthetic later line.")
        _ = conversation.dispatchAssistanceAction(.findSource)

        XCTAssertEqual(retained.transcript.count, 1)
        XCTAssertEqual(retained.transcript.first?.text, "Synthetic original line.")
        XCTAssertTrue(retained.retrievalLog.isEmpty)
    }

    func testDeletingSelectedAggregateLeavesOtherAggregatesSiblingsAndSourcesIntact() {
        var alpha = TestFixtures.conversation(title: "Synthetic alpha", phase: .conversation)
        alpha.appendTranscript(source: .me, text: "Synthetic alpha line.")
        alpha.arriveReferenceCandidate(TestFixtures.firstCandidate)
        alpha.arriveReferenceCandidate(TestFixtures.secondCandidate)
        let alphaSourceIDs = alpha.reference.candidates.map(\.id)

        var beta = TestFixtures.conversation(title: "Synthetic beta", phase: .conversation)
        beta.appendTranscript(source: .otherSide, text: "Synthetic beta line.")

        let store = ConversationStore(conversations: [alpha, beta], selectedConversationID: alpha.id)

        let firstRetained = store.retainCurrentSnapshot()
        let secondRetained = store.retainCurrentSnapshot()
        XCTAssertNotNil(firstRetained)
        XCTAssertNotNil(secondRetained)
        guard let firstRetained, let secondRetained else { return }

        XCTAssertTrue(store.selectRetainedAggregate(id: firstRetained.id))
        XCTAssertTrue(store.deleteSelectedRetainedAggregate())

        XCTAssertEqual(store.conversations[0].retainedAggregates.map(\.id), [secondRetained.id])
        XCTAssertEqual(store.conversations[0].reference.candidates.map(\.id), alphaSourceIDs)
        XCTAssertEqual(store.conversations[0].transcript.count, 1)
        XCTAssertTrue(store.conversations[1].retainedAggregates.isEmpty)
        XCTAssertEqual(store.conversations[1].transcript.first?.text, "Synthetic beta line.")

        // A sibling conversation can retain and delete independently.
        XCTAssertTrue(store.selectConversation(id: beta.id))
        let betaRetained = store.retainCurrentSnapshot()
        XCTAssertNotNil(betaRetained)
        XCTAssertEqual(store.conversations[1].retainedAggregates.count, 1)
        XCTAssertTrue(store.deleteSelectedRetainedAggregate())
        XCTAssertTrue(store.conversations[1].retainedAggregates.isEmpty)
        XCTAssertEqual(store.conversations[0].retainedAggregates.map(\.id), [secondRetained.id])
        XCTAssertEqual(store.conversations[0].reference.candidates.map(\.id), alphaSourceIDs)
    }

    func testDeletionRequiresAnExplicitSelectionAndKeepsTranscriptAndSources() {
        var conversation = TestFixtures.conversation(phase: .conversation)
        conversation.appendTranscript(source: .me, text: "Synthetic retained line.")
        conversation.arriveReferenceCandidate(TestFixtures.firstCandidate)
        let retained = conversation.retainSnapshot(selecting: false)
        let sourcesBefore = conversation.reference.candidates

        XCTAssertNil(conversation.selectedRetainedAggregateID)
        XCTAssertFalse(conversation.deleteSelectedRetainedAggregate())
        XCTAssertEqual(conversation.retainedAggregates.map(\.id), [retained.id])
        XCTAssertEqual(conversation.transcript.count, 1)
        XCTAssertEqual(conversation.reference.candidates, sourcesBefore)

        XCTAssertTrue(conversation.selectRetainedAggregate(id: retained.id))
        XCTAssertTrue(conversation.deleteSelectedRetainedAggregate())
        XCTAssertTrue(conversation.retainedAggregates.isEmpty)
        XCTAssertEqual(conversation.transcript.count, 1)
        XCTAssertEqual(conversation.reference.candidates, sourcesBefore)
    }

    func testSelectionCannotEscapeTheCurrentConversation() {
        var alpha = TestFixtures.conversation(title: "Synthetic alpha", phase: .conversation)
        alpha.appendTranscript(source: .me, text: "Synthetic alpha line.")
        let store = ConversationStore(conversations: [alpha], selectedConversationID: alpha.id)
        let retained = store.retainCurrentSnapshot()
        XCTAssertNotNil(retained)
        guard let retained else { return }

        XCTAssertFalse(store.selectRetainedAggregate(id: UUID()))
        XCTAssertEqual(store.currentConversation?.selectedRetainedAggregateID, retained.id)
        XCTAssertTrue(store.selectRetainedAggregate(id: retained.id))
    }
}
