import Foundation
import EscalierCore

enum TestFixtures {
    static func candidate(
        id: String,
        sourceID: String? = nil,
        documentTitle: String = "Synthetic test notes",
        locator: String = "Section 1, paragraph 1",
        anchor: String = "section-1",
        excerpt: String,
        phrase: String
    ) -> ReferenceCandidate {
        let source = excerpt as NSString
        let range = source.range(of: phrase)
        precondition(range.location != NSNotFound, "Test phrase must exist in the synthetic excerpt")
        return ReferenceCandidate(
            id: id,
            source: SourceIdentity(
                id: sourceID ?? "source-\(id)",
                title: "\(documentTitle) (invented)",
                kind: .document,
                synthetic: true
            ),
            citation: Citation(
                documentTitle: documentTitle,
                locator: locator,
                anchor: anchor,
                synthetic: true
            ),
            excerpt: excerpt,
            range: TextRange(start: range.location, length: range.length)
        )
    }

    static var firstCandidate: ReferenceCandidate {
        candidate(
            id: "candidate-1",
            sourceID: "source-alpha",
            documentTitle: "Synthetic alpha notes",
            locator: "Section 2, paragraph 3",
            anchor: "alpha-collaboration",
            excerpt: "The invented team values small, reversible steps and evidence over confident claims.",
            phrase: "small, reversible steps"
        )
    }

    static var secondCandidate: ReferenceCandidate {
        candidate(
            id: "candidate-2",
            sourceID: "source-beta",
            documentTitle: "Synthetic beta brief",
            locator: "Page 4, latency budget",
            anchor: "beta-latency",
            excerpt: "The invented latency budget is thirty milliseconds for this synthetic demonstration.",
            phrase: "latency budget"
        )
    }

    static var thirdCandidate: ReferenceCandidate {
        candidate(
            id: "candidate-3",
            sourceID: "source-gamma",
            documentTitle: "Synthetic gamma appendix",
            locator: "Appendix A, bullet 2",
            anchor: "gamma-rollback",
            excerpt: "A rollback plan is invented for this synthetic note and is not a real commitment.",
            phrase: "rollback plan"
        )
    }

    static func conversation(
        title: String = "Synthetic test conversation",
        phase: ConversationPhase = .preparation
    ) -> ConversationState {
        ConversationState.synthetic(title: title, phase: phase)
    }

    static func conversationPair() -> (ConversationState, ConversationState) {
        (
            conversation(title: "Synthetic alpha conversation", phase: .preparation),
            conversation(title: "Synthetic beta conversation", phase: .preparation)
        )
    }
}
