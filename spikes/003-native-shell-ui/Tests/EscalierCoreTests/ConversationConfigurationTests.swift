import XCTest
import EscalierCore

final class ConversationConfigurationTests: XCTestCase {
    func testModelToolAndSkillSelectionsAreIsolatedPerConversation() {
        let (first, second) = TestFixtures.conversationPair()
        let store = ConversationStore(
            conversations: [first, second],
            selectedConversationID: first.id
        )

        XCTAssertTrue(store.setModel(id: "mock-model-fast"))
        XCTAssertTrue(store.toggleTool(id: "mock-notes")) // Start default has mock-notes, toggle off.
        XCTAssertTrue(store.toggleTool(id: "mock-search"))
        XCTAssertTrue(store.toggleSkill(id: "mock-tone"))

        let firstAfter = store.conversations[0]
        XCTAssertEqual(firstAfter.capabilities.selectedModelID, "mock-model-fast")
        XCTAssertFalse(firstAfter.capabilities.enabledToolIDs.contains("mock-notes"))
        XCTAssertTrue(firstAfter.capabilities.enabledToolIDs.contains("mock-search"))
        XCTAssertTrue(firstAfter.capabilities.enabledSkillIDs.contains("mock-tone"))

        XCTAssertTrue(store.selectConversation(id: second.id))
        let secondAfter = store.conversations[1]
        XCTAssertEqual(secondAfter.capabilities.selectedModelID, "mock-model-balanced")
        XCTAssertEqual(secondAfter.capabilities.enabledToolIDs, Set(["mock-notes"]))
        XCTAssertEqual(secondAfter.capabilities.enabledSkillIDs, Set(["mock-briefing"]))

        XCTAssertTrue(store.selectConversation(id: first.id))
        XCTAssertEqual(store.currentConversation?.capabilities.selectedModelID, "mock-model-fast")
        XCTAssertTrue(
            store.currentConversation?.capabilities.enabledToolIDs.contains("mock-search") == true
        )
    }

    func testUnknownMockSelectionsAreRejectedWithoutChange() {
        var conversation = TestFixtures.conversation()
        let original = conversation.capabilities

        XCTAssertFalse(conversation.setSelectedModel(id: "not-a-mock-model"))
        XCTAssertFalse(conversation.toggleTool(id: "not-a-mock-tool"))
        XCTAssertFalse(conversation.toggleSkill(id: "not-a-mock-skill"))

        XCTAssertEqual(conversation.capabilities, original)
    }

    func testPhaseAndReferenceStateAreIsolatedAcrossConversations() {
        let (first, second) = TestFixtures.conversationPair()
        let store = ConversationStore(
            conversations: [first, second],
            selectedConversationID: first.id
        )

        XCTAssertTrue(store.startConversation())
        XCTAssertTrue(store.arriveReferenceCandidate(TestFixtures.firstCandidate))
        XCTAssertEqual(store.currentConversation?.reference.selectedCandidateID, "candidate-1")

        XCTAssertTrue(store.selectConversation(id: second.id))
        XCTAssertEqual(store.currentConversation?.phase, .preparation)
        XCTAssertTrue(store.currentConversation?.reference.candidates.isEmpty == true)
        XCTAssertTrue(store.startConversation())
        XCTAssertTrue(store.arriveReferenceCandidate(TestFixtures.secondCandidate))

        XCTAssertTrue(store.selectConversation(id: first.id))
        XCTAssertEqual(store.currentConversation?.phase, .conversation)
        XCTAssertEqual(store.currentConversation?.reference.candidates.map(\.id), ["candidate-1"])
        XCTAssertEqual(store.currentConversation?.reference.selectedCandidateID, "candidate-1")
        XCTAssertEqual(store.conversations[1].reference.selectedCandidateID, "candidate-2")
    }

    func testMockConfigurationNeverClaimsRuntimeEnforcement() {
        let conversation = TestFixtures.conversation()
        XCTAssertEqual(conversation.runtimeStatus.modelSelection, .mock)
        XCTAssertEqual(conversation.runtimeStatus.toolSkillSelection, .mock)
        XCTAssertFalse(conversation.synthetic == false)
        XCTAssertTrue(conversation.synthetic)
    }
}
