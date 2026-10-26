import Foundation

/// All names, excerpts, transcripts, logs and diagrams in this type are invented for
/// the prototype. They are not the owner's history, files, accomplishments or opinions.
public enum SampleContent {
    private static func candidate(
        id: String,
        sourceID: String,
        title: String,
        kind: SourceKind,
        documentTitle: String,
        locator: String,
        anchor: String,
        excerpt: String,
        phrase: String
    ) -> ReferenceCandidate {
        let nsExcerpt = excerpt as NSString
        let phraseRange = nsExcerpt.range(of: phrase)
        precondition(phraseRange.location != NSNotFound, "Synthetic sample phrase missing")
        return ReferenceCandidate(
            id: id,
            source: SourceIdentity(
                id: sourceID,
                title: "\(title) (invented)",
                kind: kind
            ),
            citation: Citation(
                documentTitle: documentTitle,
                locator: locator,
                anchor: anchor
            ),
            excerpt: excerpt,
            range: TextRange(start: phraseRange.location, length: phraseRange.length)
        )
    }

    public static let referenceCandidates: [ReferenceCandidate] = [
        candidate(
            id: "sample-candidate-collaboration",
            sourceID: "sample-source-alpha-notes",
            title: "Synthetic alpha notes",
            kind: .note,
            documentTitle: "Synthetic alpha notes",
            locator: "Section 2, paragraph 3",
            anchor: "alpha-collaboration",
            excerpt: "The invented team values small, reversible steps and evidence over confident claims.",
            phrase: "small, reversible steps"
        ),
        candidate(
            id: "sample-candidate-latency",
            sourceID: "sample-source-beta-brief",
            title: "Synthetic beta brief",
            kind: .document,
            documentTitle: "Synthetic beta brief",
            locator: "Page 4, latency budget",
            anchor: "beta-latency",
            excerpt: "The invented latency budget is thirty milliseconds for this synthetic demonstration.",
            phrase: "latency budget"
        ),
        candidate(
            id: "sample-candidate-rollback",
            sourceID: "sample-source-gamma-appendix",
            title: "Synthetic gamma appendix",
            kind: .document,
            documentTitle: "Synthetic gamma appendix",
            locator: "Appendix A, bullet 2",
            anchor: "gamma-rollback",
            excerpt: "A rollback plan is invented for this synthetic note and is not a real commitment.",
            phrase: "rollback plan"
        )
    ]

    /// Used only by the manual "simulate new candidate arrival" control so a reviewer can
    /// see the selected passage stay fixed and the new-candidate indicator appear.
    public static let newArrivalCandidate: ReferenceCandidate = candidate(
        id: "sample-candidate-new-arrival",
        sourceID: "sample-source-delta-checklist",
        title: "Synthetic delta checklist",
        kind: .note,
        documentTitle: "Synthetic delta checklist",
        locator: "Bullet 5",
        anchor: "delta-checkpoint",
        excerpt: "A newly arrived synthetic candidate mentions an invented review checkpoint.",
        phrase: "review checkpoint"
    )

    public static let localDiagram = LocalDiagram(
        title: "Synthetic source → reference → assistance flow",
        altText: "Synthetic vector diagram: two invented source excerpts flow into one stable reference selection, then into an assistance panel marked MOCK. No real data, file or image is shown."
    )

    public static func liveConversation() -> ConversationState {
        var conversation = ConversationState(
            title: "Synthetic interview — invented demo",
            phase: .conversation
        )

        conversation.appendTranscript(
            source: .me,
            text: "Synthetic prep note: I want to describe a small, reversible rollout."
        )
        conversation.appendTranscript(
            source: .otherSide,
            text: "Synthetic interviewer question: which invented trade-off mattered most?"
        )
        conversation.appendTranscript(
            source: .me,
            text: "Synthetic answer: we measured the invented latency budget and chose the smaller slice."
        )

        for candidate in referenceCandidates {
            _ = conversation.arriveReferenceCandidate(candidate)
        }
        _ = conversation.selectReferenceCandidate(id: referenceCandidates[0].id)

        let sourceMessageID = conversation.beginStreamingAssistance(kind: .sourceBacked)
        _ = conversation.appendAssistanceChunk(
            "Source-backed synthetic excerpt: ",
            to: sourceMessageID
        )
        _ = conversation.appendAssistanceChunk(
            "“small, reversible steps”.",
            to: sourceMessageID
        )
        _ = conversation.completeAssistanceMessage(sourceMessageID)

        let suggestionMessageID = conversation.beginStreamingAssistance(kind: .suggestedWording)
        _ = conversation.appendAssistanceChunk(
            "Synthetic suggested wording: ",
            to: suggestionMessageID
        )
        _ = conversation.appendAssistanceChunk(
            "“We can ship a small slice first and measure it.”",
            to: suggestionMessageID
        )
        _ = conversation.completeAssistanceMessage(suggestionMessageID)

        let generalMessageID = conversation.beginStreamingAssistance(kind: .generalInformation)
        _ = conversation.appendAssistanceChunk(
            "This is invented general information, not a personal fact or accomplishment.",
            to: generalMessageID
        )
        _ = conversation.completeAssistanceMessage(generalMessageID)

        _ = conversation.addCompleteLocalDiagram(localDiagram)
        _ = conversation.dispatchAssistanceAction(.findSource)
        _ = conversation.retainSnapshot()
        return conversation
    }

    public static func preparationConversation() -> ConversationState {
        var conversation = ConversationState(
            title: "Synthetic preparation — invented planning",
            phase: .preparation
        )
        for candidate in referenceCandidates {
            _ = conversation.arriveReferenceCandidate(candidate)
        }
        _ = conversation.selectReferenceCandidate(id: referenceCandidates[1].id)
        return conversation
    }

    public static func demoConversations() -> [ConversationState] {
        [liveConversation(), preparationConversation()]
    }

    public static func demoStore() -> ConversationStore {
        ConversationStore(conversations: demoConversations())
    }
}
