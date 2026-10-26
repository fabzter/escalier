import XCTest
import EscalierCore

final class PhaseAndRoutingTests: XCTestCase {
    func testPreparationTransitionsToConversationExplicitlyAndPreservesContent() {
        var conversation = TestFixtures.conversation(phase: .preparation)
        XCTAssertEqual(conversation.phase, .preparation)

        let entry = conversation.appendTranscript(source: .me, text: "Synthetic preparation note.")

        XCTAssertTrue(conversation.startConversation())
        XCTAssertEqual(conversation.phase, .conversation)
        XCTAssertEqual(conversation.transcript.map(\.id), [entry.id])
        XCTAssertFalse(conversation.startConversation(), "Repeated transition must be idempotent")
        XCTAssertEqual(conversation.phase, .conversation)
        XCTAssertEqual(conversation.transcript.count, 1)
    }

    func testFiveFR07ActionsHaveDistinctNonemptyRoutesAndHints() {
        let actions = AssistanceAction.allCases
        XCTAssertEqual(actions.count, 5)
        XCTAssertEqual(Set(actions.map(\.route)).count, 5)
        XCTAssertEqual(Set(actions.map(\.label)).count, 5)
        XCTAssertEqual(Set(actions.map(\.shortcutHint)).count, 5)
        XCTAssertEqual(Set(actions.map(\.keyEquivalent)).count, 5)
        XCTAssertEqual(
            Set(actions.map(\.rawValue)),
            Set([
                "find-source",
                "answer-latest-question",
                "formulate-point",
                "way-forward",
                "interpret-screenshot"
            ])
        )

        for action in actions {
            XCTAssertFalse(action.route.isEmpty)
            XCTAssertTrue(action.route.hasPrefix("/assist/"))
            XCTAssertFalse(action.shortcutHint.isEmpty)
            XCTAssertFalse(action.label.isEmpty)
        }
    }

    func testDispatchingEveryActionLogsItsDistinctRoute() {
        var conversation = TestFixtures.conversation(phase: .conversation)

        for action in AssistanceAction.allCases {
            let entry = conversation.dispatchAssistanceAction(action)
            XCTAssertEqual(entry.action, action)
            XCTAssertEqual(entry.route, action.route)
            XCTAssertTrue(entry.synthetic)
            XCTAssertFalse(entry.summary.isEmpty)
        }

        XCTAssertEqual(conversation.retrievalLog.count, 5)
        XCTAssertEqual(Set(conversation.retrievalLog.map(\.route)).count, 5)
    }

    func testRuntimeStatusesAreExplicitlyMockOrNotConnected() {
        let status = PrototypeRuntimeStatus.prototype

        XCTAssertEqual(status.modelSelection, .mock)
        XCTAssertEqual(status.toolSkillSelection, .mock)
        XCTAssertEqual(status.input, .notConnected)
        XCTAssertEqual(status.permissions, .notConnected)
        XCTAssertEqual(status.omp, .notConnected)
        XCTAssertEqual(status.screenshotCapture, .notConnected)
        XCTAssertEqual(status.globalShortcutRouting, .notConnected)
        XCTAssertEqual(IntegrationStatus.mock.rawValue, "MOCK")
        XCTAssertEqual(IntegrationStatus.notConnected.rawValue, "NOT CONNECTED")
    }

    func testScreenshotRouteIsALoggedPlaceholderNotCapture() {
        var conversation = TestFixtures.conversation(phase: .conversation)

        let entry = conversation.dispatchAssistanceAction(.interpretScreenshot)

        XCTAssertEqual(entry.action, .interpretScreenshot)
        XCTAssertEqual(entry.route, "/assist/interpret-screenshot")
        XCTAssertTrue(entry.summary.lowercased().contains("no screenshot"))
        XCTAssertEqual(conversation.runtimeStatus.screenshotCapture, .notConnected)
    }

    func testRoutingIsPerConversation() {
        let first = TestFixtures.conversation(title: "Synthetic first", phase: .conversation)
        let second = TestFixtures.conversation(title: "Synthetic second", phase: .conversation)
        let store = ConversationStore(
            conversations: [first, second],
            selectedConversationID: first.id
        )

        _ = store.dispatchAssistanceAction(.findSource)
        XCTAssertEqual(store.conversations[0].retrievalLog.count, 1)
        XCTAssertTrue(store.conversations[1].retrievalLog.isEmpty)

        XCTAssertTrue(store.selectConversation(id: second.id))
        _ = store.dispatchAssistanceAction(.wayForward)
        XCTAssertEqual(store.conversations[0].retrievalLog.count, 1)
        XCTAssertEqual(store.conversations[1].retrievalLog.map(\.action), [.wayForward])
    }
}
