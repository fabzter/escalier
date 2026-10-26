import SwiftUI
import EscalierCore

struct AssistancePanelView: View {
    @ObservedObject var store: ConversationStore
    let conversation: ConversationState

    private let actionColumns = [
        GridItem(.flexible(), spacing: 6, alignment: .topLeading),
        GridItem(.flexible(), spacing: 6, alignment: .topLeading)
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Text("Assistance")
                    .font(.headline)
                Badge(text: "SYNTHETIC BUFFER", color: .purple)
                Spacer()
                Text("\(conversation.assistance.count) items")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            Text("MOCK model, tool and skill choices are per-conversation presentation state. They are not sent to OMP and enforce no runtime policy.")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)

            mockConfiguration

            Divider()

            HStack(spacing: 6) {
                Text("FR-07 routes")
                    .font(.caption.weight(.semibold))
                Badge(text: "MOCK · NO GENERATION", color: .orange)
                Spacer()
                Text("App-menu shortcuts are in-app only and provisional")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            LazyVGrid(columns: actionColumns, alignment: .leading, spacing: 6) {
                ForEach(AssistanceAction.allCases) { action in
                    Button {
                        _ = store.dispatchAssistanceAction(action)
                    } label: {
                        VStack(alignment: .leading, spacing: 2) {
                            HStack(spacing: 4) {
                                Text(action.label)
                                    .font(.caption.weight(.medium))
                                    .lineLimit(2)
                                Spacer(minLength: 0)
                                Text(action.shortcutHint)
                                    .font(.caption2.monospaced())
                                    .foregroundStyle(.secondary)
                            }
                            Text(action.route)
                                .font(.caption2.monospaced())
                                .foregroundStyle(.secondary)
                        }
                        .padding(6)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                    .disabled(conversation.phase != .conversation)
                }
            }

            if let last = conversation.retrievalLog.last {
                Text("Last synthetic route: \(last.route)")
                    .font(.caption2.monospaced())
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
            Text("The screenshot route only logs a placeholder. No screenshot is captured, stored or sent. Capture is NOT CONNECTED.")
                .font(.caption2)
                .foregroundStyle(.orange)

            Divider()

            HStack {
                Text("Streamed synthetic text")
                    .font(.caption.weight(.semibold))
                Badge(text: "MANUAL CHUNKS", color: .blue)
                Spacer()
                Button("Advance synthetic stream") {
                    _ = store.advanceSyntheticStream()
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .disabled(conversation.phase != .conversation)
            }

            ScrollView {
                LazyVStack(alignment: .leading, spacing: 7) {
                    ForEach(conversation.assistance) { message in
                        AssistanceMessageRow(message: message)
                    }
                }
            }
            .frame(minHeight: 180, maxHeight: 340)
            .background(Color(nsColor: .textBackgroundColor).opacity(0.55), in: RoundedRectangle(cornerRadius: 7))
            .overlay(
                RoundedRectangle(cornerRadius: 7)
                    .stroke(Color(nsColor: .separatorColor), lineWidth: 0.5)
            )

            Text("This preview is local vector content, not a generated or downloaded image. Its text alternative is visible and is also the accessibility label.")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .cardSurface()
    }

    private var mockConfiguration: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Text("Conversation capability selection")
                    .font(.caption.weight(.semibold))
                Badge(text: conversation.runtimeStatus.modelSelection.rawValue, color: .orange)
                Badge(text: conversation.runtimeStatus.toolSkillSelection.rawValue, color: .orange)
            }

            Picker(
                "MOCK model",
                selection: Binding(
                    get: { conversation.capabilities.selectedModelID ?? "" },
                    set: { newValue in
                        _ = store.setModel(id: newValue.isEmpty ? nil : newValue)
                    }
                )
            ) {
                Text("No model").tag("")
                ForEach(MockCapabilityCatalog.models) { model in
                    Text(model.name).tag(model.id)
                }
            }
            .pickerStyle(.menu)
            .frame(maxWidth: 310, alignment: .leading)

            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("MOCK tools")
                        .font(.caption2.weight(.semibold))
                    ForEach(MockCapabilityCatalog.tools) { tool in
                        Toggle(tool.name, isOn: toolBinding(tool))
                            .toggleStyle(.checkbox)
                            .font(.caption)
                    }
                }
                VStack(alignment: .leading, spacing: 3) {
                    Text("MOCK skills")
                        .font(.caption2.weight(.semibold))
                    ForEach(MockCapabilityCatalog.skills) { skill in
                        Toggle(skill.name, isOn: skillBinding(skill))
                            .toggleStyle(.checkbox)
                            .font(.caption)
                    }
                }
            }

            Text("No runtime policy is enforced. Unknown IDs are rejected by the pure model.")
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .padding(8)
        .background(Color.orange.opacity(0.05), in: RoundedRectangle(cornerRadius: 7))
    }

    private func toolBinding(_ tool: MockCapability) -> Binding<Bool> {
        Binding(
            get: { conversation.capabilities.enabledToolIDs.contains(tool.id) },
            set: { newValue in
                let current = conversation.capabilities.enabledToolIDs.contains(tool.id)
                if newValue != current {
                    _ = store.toggleTool(id: tool.id)
                }
            }
        )
    }

    private func skillBinding(_ skill: MockCapability) -> Binding<Bool> {
        Binding(
            get: { conversation.capabilities.enabledSkillIDs.contains(skill.id) },
            set: { newValue in
                let current = conversation.capabilities.enabledSkillIDs.contains(skill.id)
                if newValue != current {
                    _ = store.toggleSkill(id: skill.id)
                }
            }
        )
    }
}

struct AssistanceMessageRow: View {
    let message: AssistanceMessage

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 5) {
                Badge(text: message.kind.provenanceLabel, color: assistanceColor(message.kind))
                if message.isStreaming {
                    Badge(text: "STREAMING", color: .blue)
                }
                Spacer()
                Text("\(message.chunks.count) synthetic chunks")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            if let diagram = message.localDiagram {
                SyntheticDiagramView(diagram: diagram)
            } else if message.text.isEmpty {
                Text("Awaiting a synthetic chunk.")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            } else {
                Text(message.text)
                    .font(.callout)
                    .textSelection(.enabled)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .padding(8)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            assistanceColor(message.kind).opacity(0.06),
            in: RoundedRectangle(cornerRadius: 7)
        )
    }
}

struct SyntheticDiagramView: View {
    let diagram: LocalDiagram

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 5) {
                Text(diagram.title)
                    .font(.caption.weight(.semibold))
                Spacer()
                Badge(text: "LOCAL VECTOR", color: .purple)
                Badge(text: diagram.completeness.label, color: .purple)
                Badge(text: "SYNTHETIC", color: .purple)
            }

            VStack(spacing: 4) {
                flowBox("Invented source excerpt A", color: .green)
                Image(systemName: "arrow.down")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                flowBox("Stable synthetic reference selection", color: .blue)
                Image(systemName: "arrow.down")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                flowBox("Assistance panel · MOCK", color: .orange)
            }
            .padding(7)
            .frame(maxWidth: .infinity)
            .background(Color.purple.opacity(0.05), in: RoundedRectangle(cornerRadius: 7))

            Text(diagram.altText)
                .font(.caption2)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .textSelection(.enabled)
        }
        .padding(8)
        .background(Color.purple.opacity(0.05), in: RoundedRectangle(cornerRadius: 7))
        .overlay(
            RoundedRectangle(cornerRadius: 7)
                .stroke(Color.purple.opacity(0.25), lineWidth: 0.5)
        )
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(diagram.altText)
    }

    private func flowBox(_ label: String, color: Color) -> some View {
        Text(label)
            .font(.caption2)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 4)
            .background(color.opacity(0.10), in: RoundedRectangle(cornerRadius: 5))
            .overlay(RoundedRectangle(cornerRadius: 5).stroke(color.opacity(0.35), lineWidth: 0.5))
    }
}
