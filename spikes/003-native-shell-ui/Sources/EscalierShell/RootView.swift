import SwiftUI
import EscalierCore

struct RootView: View {
    @ObservedObject var store: ConversationStore

    var body: some View {
        HSplitView {
            SidebarView(store: store)
                .frame(minWidth: 250, idealWidth: 280, maxWidth: 330)

            if let conversation = store.currentConversation {
                ConversationDetailView(store: store, conversation: conversation)
                    .frame(minWidth: 820, maxWidth: .infinity, maxHeight: .infinity)
            } else {
                VStack(spacing: 8) {
                    Text("No synthetic conversation selected")
                        .font(.headline)
                    Text("This prototype has no persistent data to recover.")
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .frame(minWidth: 1100, minHeight: 700)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

struct SidebarView: View {
    @ObservedObject var store: ConversationStore

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Escalier")
                    .font(.title2.weight(.semibold))
                Text("Native shell spike · synthetic wireframe")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Badge(text: "ALL CONTENT INVENTED", color: .purple)
            }

            Divider()

            ScrollView {
                LazyVStack(alignment: .leading, spacing: 6) {
                    ForEach(store.conversations) { conversation in
                        Button {
                            _ = store.selectConversation(id: conversation.id)
                        } label: {
                            conversationRow(
                                conversation,
                                isSelected: conversation.id == store.selectedConversationID
                            )
                        }
                        .buttonStyle(.plain)
                    }
                }
            }

            Divider()

            VStack(alignment: .leading, spacing: 5) {
                Text("Prototype boundaries")
                    .font(.caption.weight(.semibold))
                Text("No files, microphone, screen capture, network, OMP call or persistent user-data deletion. Retained results and deleted aggregates are in memory only.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 4) {
                    Badge(text: "MOCK", color: .orange)
                    Badge(text: "NOT CONNECTED", color: .red)
                }
                Text("Global shortcuts are app-menu equivalents only. Related work: 005-global-keyboard-routing.")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
                Text("GUI visual, keyboard, focus and scroll behavior: NOT TESTED.")
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(.orange)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(12)
        .background(Color(nsColor: .underPageBackgroundColor))
    }

    private func conversationRow(_ conversation: ConversationState, isSelected: Bool) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Text(conversation.title)
                    .font(.callout.weight(.medium))
                    .lineLimit(2)
                    .foregroundStyle(.primary)
                Spacer(minLength: 2)
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.tint)
                }
            }
            HStack(spacing: 4) {
                Badge(text: conversation.phase.label.uppercased(), color: conversation.phase == .conversation ? .green : .blue)
                Badge(text: "SYNTHETIC", color: .purple)
            }
            Text("\(conversation.reference.candidates.count) sources · \(conversation.assistance.count) assistance items · \(conversation.retainedAggregates.count) retained")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            isSelected ? Color.accentColor.opacity(0.14) : Color.clear,
            in: RoundedRectangle(cornerRadius: 7)
        )
        .contentShape(Rectangle())
    }
}
