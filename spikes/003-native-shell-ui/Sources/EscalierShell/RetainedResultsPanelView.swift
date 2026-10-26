import SwiftUI
import EscalierCore

struct RetainedResultsPanelView: View {
    @ObservedObject var store: ConversationStore
    let conversation: ConversationState
    @State private var confirmingDelete = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Retained results")
                    .font(.headline)
                Badge(text: "IN-MEMORY SYNTHETIC", color: .blue)
                Spacer()
                Text("\(conversation.retainedAggregates.count) snapshots")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            Text("A snapshot stores the synthetic transcript, retrieval log and assistance together. It is not written to disk. Deleting removes only the selected snapshot in this conversation; sibling conversations and source excerpts remain.")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            if conversation.retainedAggregates.isEmpty {
                Text("No synthetic snapshot retained in this conversation.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 5)
            } else {
                VStack(alignment: .leading, spacing: 5) {
                    ForEach(conversation.retainedAggregates) { aggregate in
                        Button {
                            _ = store.selectRetainedAggregate(id: aggregate.id)
                        } label: {
                            HStack(alignment: .top, spacing: 7) {
                                Image(systemName: aggregate.id == conversation.selectedRetainedAggregateID
                                    ? "largecircle.fill.circle"
                                    : "circle")
                                    .foregroundStyle(aggregate.id == conversation.selectedRetainedAggregateID ? Color.accentColor : Color.secondary)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(aggregate.conversationTitle)
                                        .font(.caption.weight(.medium))
                                        .foregroundStyle(.primary)
                                    Text("\(aggregate.transcript.count) transcript · \(aggregate.retrievalLog.count) retrieval · \(aggregate.assistance.count) assistance")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                    Text(aggregate.storage.label)
                                        .font(.caption2)
                                        .foregroundStyle(.blue)
                                }
                                Spacer(minLength: 0)
                            }
                            .padding(6)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(
                                aggregate.id == conversation.selectedRetainedAggregateID
                                    ? Color.accentColor.opacity(0.10)
                                    : Color.clear,
                                in: RoundedRectangle(cornerRadius: 6)
                            )
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            if let selected = conversation.retainedAggregates.first(
                where: { $0.id == conversation.selectedRetainedAggregateID }
            ) {
                DisclosureGroup("Inspect selected synthetic snapshot") {
                    VStack(alignment: .leading, spacing: 6) {
                        snapshotSectionTitle("Transcript (\(selected.transcript.count))")
                        ForEach(selected.transcript) { entry in
                            Text("\(entry.source.badge): \(entry.text)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }

                        snapshotSectionTitle("Retrieval log (\(selected.retrievalLog.count))")
                        ForEach(selected.retrievalLog) { entry in
                            Text("\(entry.route) — \(entry.summary)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }

                        snapshotSectionTitle("Assistance (\(selected.assistance.count))")
                        ForEach(selected.assistance) { message in
                            Text("\(message.kind.provenanceLabel) · \(message.chunks.count) chunks\(message.isStreaming ? " · streaming" : "")")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }

                        Text(selected.storage.label)
                            .font(.caption2)
                            .foregroundStyle(.blue)
                    }
                    .padding(.top, 4)
                }
                .font(.caption)
            }

            HStack(spacing: 8) {
                Button("Retain synthetic snapshot") {
                    _ = store.retainCurrentSnapshot()
                }
                .buttonStyle(.bordered)
                .controlSize(.small)

                Button("Delete selected synthetic result", role: .destructive) {
                    confirmingDelete = true
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .disabled(conversation.selectedRetainedAggregateID == nil)
            }

            Text("This deletion is an in-memory state change only. No files, chat history, audio, screenshots or user data on disk are deleted.")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .cardSurface()
        .alert("Delete selected synthetic retained result?", isPresented: $confirmingDelete) {
            Button("Delete in-memory snapshot", role: .destructive) {
                _ = store.deleteSelectedRetainedAggregate()
            }
            Button("Cancel", role: .cancel) {}
        } message: {
            Text("Only the selected in-memory synthetic aggregate is removed. Sibling conversations and source excerpts stay. No disk data is touched.")
        }
    }

    private func snapshotSectionTitle(_ text: String) -> some View {
        Text(text)
            .font(.caption2.weight(.semibold))
    }
}
