import SwiftUI
import EscalierCore

struct ReferencePanelView: View {
    @ObservedObject var store: ConversationStore
    let conversation: ConversationState

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Text("Reference")
                    .font(.headline)
                Badge(text: "ACTUAL SOURCE TEXT · SYNTHETIC", color: .green)
                Spacer()
                Text("\(conversation.reference.candidates.count) candidates")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 6) {
                Button("Previous") {
                    _ = store.selectPreviousReference()
                }
                Button("Next") {
                    _ = store.selectNextReference()
                }
                Button("Simulate new candidate arrival") {
                    _ = store.arriveReferenceCandidate(SampleContent.newArrivalCandidate)
                }
                .disabled(
                    conversation.reference.candidates.contains {
                        $0.id == SampleContent.newArrivalCandidate.id
                    }
                )
                Spacer()
            }
            .buttonStyle(.bordered)
            .controlSize(.small)

            Text("Selection is independent of new-candidate arrival. Navigation moves it explicitly and clears the new-candidate indicator.")
                .font(.caption2)
                .foregroundStyle(.secondary)

            if conversation.reference.hasNewCandidateIndicator {
                Label(
                    "New synthetic candidate(s) available. The selected passage was held; use Next or choose a candidate explicitly.",
                    systemImage: "bell.badge"
                )
                .font(.caption)
                .foregroundStyle(.orange)
                .padding(7)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.orange.opacity(0.08), in: RoundedRectangle(cornerRadius: 7))
            }

            if let unresolved = conversation.reference.unresolvedReason {
                Label(unresolved.label, systemImage: "exclamationmark.triangle")
                    .font(.caption)
                    .foregroundStyle(.red)
                    .padding(7)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.red.opacity(0.08), in: RoundedRectangle(cornerRadius: 7))
            }

            if let selected = conversation.reference.selectedCandidate {
                selectedCard(selected)
            } else {
                Text("No reference is resolved. Choose a synthetic candidate below; the prototype will not silently choose one.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 6)
            }

            Divider()

            Text("Other synthetic candidates")
                .font(.caption.weight(.semibold))
            VStack(alignment: .leading, spacing: 5) {
                ForEach(conversation.reference.candidates) { candidate in
                    Button {
                        _ = store.selectReferenceCandidate(id: candidate.id)
                    } label: {
                        HStack(alignment: .top, spacing: 7) {
                            Image(systemName: candidate.id == conversation.reference.selectedCandidateID
                                ? "largecircle.fill.circle"
                                : "circle")
                                .foregroundStyle(candidate.id == conversation.reference.selectedCandidateID ? Color.accentColor : Color.secondary)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(candidate.source.title)
                                    .font(.caption)
                                    .foregroundStyle(.primary)
                                Text("\(candidate.citation.locator) · anchor \(candidate.citation.anchor)")
                                    .font(.caption2)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer(minLength: 0)
                        }
                        .padding(6)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }

            Text("Source excerpts and citations stay outside the synthetic assistant history. Scroll-position stability is NOT TESTED until separately observed with interactive evidence.")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .cardSurface()
    }

    private func selectedCard(_ candidate: ReferenceCandidate) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(spacing: 6) {
                Badge(text: "SELECTED SOURCE", color: .green)
                Badge(text: candidate.source.synthetic ? "SYNTHETIC" : "UNKNOWN", color: .purple)
                Spacer()
                Button("Simulate candidate removal") {
                    _ = store.removeReferenceCandidate(id: candidate.id)
                }
                .buttonStyle(.bordered)
                .controlSize(.mini)
            }
            Text(candidate.source.title)
                .font(.callout.weight(.semibold))
            Text("\(candidate.source.kind.label) · \(candidate.citation.documentTitle) · \(candidate.citation.locator)")
                .font(.caption2)
                .foregroundStyle(.secondary)

            HighlightedExcerpt(excerpt: candidate.excerpt, range: candidate.range)
                .font(.callout)
                .lineSpacing(2)
                .textSelection(.enabled)
                .padding(9)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(nsColor: .textBackgroundColor), in: RoundedRectangle(cornerRadius: 7))

            HStack(spacing: 8) {
                Text("Source ID \(candidate.source.id)")
                Text("range \(candidate.range.start)…\(candidate.range.end)")
                Text("anchor \(candidate.selection.anchor)")
            }
            .font(.caption2)
            .foregroundStyle(.secondary)
            .textSelection(.enabled)
        }
        .padding(9)
        .background(Color.green.opacity(0.05), in: RoundedRectangle(cornerRadius: 8))
    }
}

struct HighlightedExcerpt: View {
    let excerpt: String
    let range: EscalierCore.TextRange

    @ViewBuilder
    var body: some View {
        if range.isValid(in: excerpt) {
            let nsExcerpt = excerpt as NSString
            let before = nsExcerpt.substring(to: range.start)
            let highlighted = nsExcerpt.substring(
                with: NSRange(location: range.start, length: range.length)
            )
            let after = nsExcerpt.substring(from: range.end)
            Text(before)
                + Text(highlighted).bold().foregroundColor(.accentColor)
                + Text(after)
        } else {
            Text(excerpt)
        }
    }
}
