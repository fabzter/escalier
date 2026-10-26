import XCTest
import EscalierCore

final class ReferenceStabilityTests: XCTestCase {
    func testSampleSourceIdentitiesAndCitationsAreStableAndDistinct() {
        let candidates = SampleContent.referenceCandidates
        XCTAssertGreaterThanOrEqual(candidates.count, 3)

        for candidate in candidates {
            XCTAssertFalse(candidate.source.id.isEmpty)
            XCTAssertFalse(candidate.source.title.isEmpty)
            XCTAssertFalse(candidate.citation.documentTitle.isEmpty)
            XCTAssertFalse(candidate.citation.locator.isEmpty)
            XCTAssertFalse(candidate.citation.anchor.isEmpty)
            XCTAssertTrue(candidate.source.synthetic)
            XCTAssertTrue(candidate.citation.synthetic)
            XCTAssertGreaterThan(candidate.range.length, 0)
            XCTAssertLessThanOrEqual(
                candidate.range.end,
                (candidate.excerpt as NSString).length,
                "A synthetic citation range must point inside its source excerpt"
            )
        }

        XCTAssertEqual(Set(candidates.map(\.source.id)).count, candidates.count)
        XCTAssertEqual(Set(candidates.map(\.id)).count, candidates.count)
        XCTAssertEqual(Set(candidates.map(\.selection.anchor)).count, candidates.count)

        let arrival = SampleContent.newArrivalCandidate
        XCTAssertFalse(candidates.map(\.id).contains(arrival.id))
        XCTAssertTrue(arrival.source.synthetic)
        XCTAssertTrue(arrival.citation.synthetic)
        XCTAssertTrue(arrival.range.isValid(in: arrival.excerpt))
    }

    func testInitialSelectionCarriesCandidateIDRangeAndAnchor() {
        let candidate = TestFixtures.firstCandidate
        let state = ReferenceState(candidates: [candidate], selectedCandidateID: candidate.id)

        XCTAssertEqual(state.selectedCandidateID, candidate.id)
        XCTAssertEqual(state.selectedRange, candidate.range)
        XCTAssertEqual(state.selectedAnchor, candidate.selection.anchor)
        XCTAssertEqual(state.selectedSelection, candidate.selection)
        XCTAssertNil(state.unresolvedReason)
        XCTAssertFalse(state.hasNewCandidateIndicator)
    }

    func testCandidateArrivalPreservesSelectedIDRangeAndAnchor() {
        let first = TestFixtures.firstCandidate
        let second = TestFixtures.secondCandidate
        var state = ReferenceState(candidates: [first], selectedCandidateID: first.id)
        let selectionBefore = state.selectedSelection

        let added = state.arrive(second)

        XCTAssertTrue(added)
        XCTAssertEqual(state.candidates.map(\.id), [first.id, second.id])
        XCTAssertEqual(state.selectedSelection, selectionBefore)
        XCTAssertEqual(state.selectedCandidateID, first.id)
        XCTAssertEqual(state.selectedRange, first.range)
        XCTAssertEqual(state.selectedAnchor, first.selection.anchor)
        XCTAssertTrue(state.hasNewCandidateIndicator)
        XCTAssertEqual(state.unseenCandidateIDs, Set([second.id]))
    }

    func testNextNavigationChangesSelectionAndClearsNewCandidateIndicator() {
        let first = TestFixtures.firstCandidate
        let second = TestFixtures.secondCandidate
        let third = TestFixtures.thirdCandidate
        var state = ReferenceState(candidates: [first], selectedCandidateID: first.id)
        XCTAssertTrue(state.arrive(second))
        XCTAssertTrue(state.arrive(third))
        XCTAssertTrue(state.hasNewCandidateIndicator)

        let next = state.selectNext()

        XCTAssertEqual(next?.candidateID, second.id)
        XCTAssertEqual(state.selectedRange, second.range)
        XCTAssertEqual(state.selectedAnchor, second.selection.anchor)
        XCTAssertFalse(state.hasNewCandidateIndicator)
        XCTAssertTrue(state.unseenCandidateIDs.isEmpty)

        let previous = state.selectPrevious()
        XCTAssertEqual(previous?.candidateID, first.id)
        XCTAssertEqual(state.selectedRange, first.range)
    }

    func testRemovingSelectedCandidateYieldsUnresolvedStateWithoutSilentJump() {
        let first = TestFixtures.firstCandidate
        let second = TestFixtures.secondCandidate
        var state = ReferenceState(candidates: [first, second], selectedCandidateID: first.id)

        let removed = state.removeCandidate(id: first.id)

        XCTAssertTrue(removed)
        XCTAssertNil(state.selectedSelection)
        XCTAssertNil(state.selectedCandidateID)
        XCTAssertNil(state.selectedRange)
        XCTAssertNil(state.selectedAnchor)
        XCTAssertEqual(state.unresolvedReason, .selectedCandidateRemoved)
        XCTAssertEqual(state.candidates.map(\.id), [second.id])
        XCTAssertNil(state.selectedCandidate, "Removal must not silently jump to a sibling candidate")
    }

    func testRemovingNonSelectedCandidateKeepsSelection() {
        let first = TestFixtures.firstCandidate
        let second = TestFixtures.secondCandidate
        var state = ReferenceState(candidates: [first, second], selectedCandidateID: first.id)

        XCTAssertTrue(state.removeCandidate(id: second.id))

        XCTAssertEqual(state.selectedCandidateID, first.id)
        XCTAssertEqual(state.selectedSelection, first.selection)
        XCTAssertNil(state.unresolvedReason)
    }

    func testExplicitSelectionClearsUnresolvedAndNewCandidateIndicator() {
        let first = TestFixtures.firstCandidate
        let second = TestFixtures.secondCandidate
        var state = ReferenceState(candidates: [first, second], selectedCandidateID: first.id)
        XCTAssertTrue(state.arrive(TestFixtures.thirdCandidate))
        XCTAssertTrue(state.removeCandidate(id: first.id))
        XCTAssertEqual(state.unresolvedReason, .selectedCandidateRemoved)

        let selected = state.selectCandidate(id: second.id)

        XCTAssertEqual(selected?.candidateID, second.id)
        XCTAssertEqual(state.selectedRange, second.range)
        XCTAssertNil(state.unresolvedReason)
        XCTAssertFalse(state.hasNewCandidateIndicator)
    }

    func testDuplicateCandidateArrivalIsIgnoredAndDoesNotMoveSelection() {
        let first = TestFixtures.firstCandidate
        var state = ReferenceState(candidates: [first], selectedCandidateID: first.id)
        let duplicate = TestFixtures.candidate(
            id: first.id,
            excerpt: "Different invented text under the same synthetic identity.",
            phrase: "Different invented text"
        )

        let added = state.arrive(duplicate)

        XCTAssertFalse(added)
        XCTAssertEqual(state.candidates.count, 1)
        XCTAssertEqual(state.selectedSelection, first.selection)
        XCTAssertFalse(state.hasNewCandidateIndicator)
    }

    func testArrivalAfterSelectedRemovalDoesNotAutoSelect() {
        let first = TestFixtures.firstCandidate
        var state = ReferenceState(candidates: [first], selectedCandidateID: first.id)
        XCTAssertTrue(state.removeCandidate(id: first.id))
        XCTAssertEqual(state.unresolvedReason, .selectedCandidateRemoved)

        XCTAssertTrue(state.arrive(TestFixtures.secondCandidate))

        XCTAssertNil(state.selectedSelection)
        XCTAssertEqual(state.unresolvedReason, .selectedCandidateRemoved)
        XCTAssertTrue(state.hasNewCandidateIndicator)
    }

    func testConversationForwardsStableSelectionArrivalNavigationAndRemoval() {
        let first = TestFixtures.firstCandidate
        let second = TestFixtures.secondCandidate
        var conversation = TestFixtures.conversation(phase: .conversation)

        XCTAssertTrue(conversation.arriveReferenceCandidate(first))
        let heldSelection = conversation.reference.selectedSelection
        XCTAssertEqual(heldSelection?.candidateID, first.id)

        XCTAssertTrue(conversation.arriveReferenceCandidate(second))
        XCTAssertEqual(conversation.reference.selectedSelection, heldSelection)
        XCTAssertTrue(conversation.reference.hasNewCandidateIndicator)

        XCTAssertEqual(conversation.selectNextReference()?.candidateID, second.id)
        XCTAssertFalse(conversation.reference.hasNewCandidateIndicator)
        XCTAssertEqual(conversation.reference.selectedAnchor, second.selection.anchor)

        XCTAssertTrue(conversation.removeReferenceCandidate(id: second.id))
        XCTAssertNil(conversation.reference.selectedSelection)
        XCTAssertEqual(conversation.reference.unresolvedReason, .selectedCandidateRemoved)
        XCTAssertEqual(conversation.reference.candidates.map(\.id), [first.id])
    }
}
