import SwiftUI
import EscalierCore

struct ConversationDetailView: View {
    @ObservedObject var store: ConversationStore
    let conversation: ConversationState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                header
                RuntimeStatusStrip(status: conversation.runtimeStatus)

                if conversation.phase == .preparation {
                    PreparationCard(store: store, conversation: conversation)
                }

                HStack(alignment: .top, spacing: 14) {
                    VStack(alignment: .leading, spacing: 14) {
                        TranscriptCard(conversation: conversation)
                        ReferencePanelView(store: store, conversation: conversation)
                    }
                    .frame(maxWidth: .infinity, alignment: .topLeading)

                    VStack(alignment: .leading, spacing: 14) {
                        AssistancePanelView(store: store, conversation: conversation)
                        RetainedResultsPanelView(store: store, conversation: conversation)
                    }
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                }
            }
            .padding(16)
        }
        .background(Color(nsColor: .windowBackgroundColor))
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text(conversation.title)
                    .font(.title2.weight(.semibold))
                Badge(
                    text: conversation.phase.label.uppercased(),
                    color: conversation.phase == .conversation ? .green : .blue
                )
                Badge(text: "SYNTHETIC", color: .purple)
            }
            Text("Two invented source identities, invented references and mock controls. No real files, history, audio, screenshot, OMP session or network is present.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

struct PreparationCard: View {
    @ObservedObject var store: ConversationStore
    let conversation: ConversationState

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(alignment: .leading, spacing: 5) {
                Text("Preparation → live conversation")
                    .font(.headline)
                Text("This is an explicit synthetic phase transition. It creates no transcript, audio, OMP request or network activity; reference candidates and mock selections stay in this conversation.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            Spacer(minLength: 8)
            Button("Start live conversation (synthetic)") {
                _ = store.startConversation()
            }
            .buttonStyle(.borderedProminent)
            .disabled(conversation.phase != .preparation)
        }
        .cardSurface()
    }
}

struct TranscriptCard: View {
    let conversation: ConversationState

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Transcript")
                    .font(.headline)
                Badge(text: "TWO SYNTHETIC SOURCE IDENTITIES", color: .purple)
                Spacer()
                Text("\(conversation.transcript.count) entries")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            Text("Source labels are fixed as ME and OTHER SIDE. Text is invented and never transcribed from audio.")
                .font(.caption2)
                .foregroundStyle(.secondary)

            if conversation.transcript.isEmpty {
                Text("No synthetic transcript in preparation. Start the conversation to use the invented live sample.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 10)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 6) {
                        ForEach(conversation.transcript) { entry in
                            HStack(alignment: .top, spacing: 8) {
                                Badge(text: entry.source.badge, color: sourceColor(entry.source))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(entry.text)
                                        .font(.callout)
                                        .textSelection(.enabled)
                                    Text("synthetic · sequence \(entry.sequence)")
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer(minLength: 0)
                            }
                            .padding(7)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(
                                sourceColor(entry.source).opacity(0.06),
                                in: RoundedRectangle(cornerRadius: 7)
                            )
                        }
                    }
                }
                .frame(maxHeight: 210)
            }
        }
        .cardSurface()
    }
}
