import SwiftUI
import EscalierCore

enum NativeTheme {
    static let cardRadius: CGFloat = 10
}

struct Badge: View {
    let text: String
    let color: Color

    var body: some View {
        Text(text)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .foregroundStyle(color)
            .background(color.opacity(0.12), in: Capsule())
            .overlay(Capsule().stroke(color.opacity(0.35), lineWidth: 0.5))
    }
}

extension View {
    func cardSurface() -> some View {
        padding(12)
            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: NativeTheme.cardRadius))
            .overlay(
                RoundedRectangle(cornerRadius: NativeTheme.cardRadius)
                    .stroke(Color(nsColor: .separatorColor).opacity(0.8), lineWidth: 0.5)
            )
    }
}

func sourceColor(_ source: TranscriptSource) -> Color {
    switch source {
    case .me: return .green
    case .otherSide: return .blue
    }
}

func assistanceColor(_ kind: AssistanceKind) -> Color {
    switch kind {
    case .sourceBacked: return .green
    case .suggestedWording: return .orange
    case .generalInformation: return .blue
    case .localImage: return .purple
    }
}

func integrationColor(_ status: IntegrationStatus) -> Color {
    switch status {
    case .mock: return .orange
    case .notConnected: return .red
    }
}

struct RuntimeStatusStrip: View {
    let status: PrototypeRuntimeStatus

    private let columns = [GridItem(.adaptive(minimum: 160), spacing: 8, alignment: .topLeading)]

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text("Prototype integration status")
                    .font(.caption.weight(.semibold))
                Badge(text: "NO RUNTIME CLAIM", color: .secondary)
            }
            LazyVGrid(columns: columns, alignment: .leading, spacing: 8) {
                statusCell("Model selection", status.modelSelection, "selection UI only")
                statusCell("Tools & skills", status.toolSkillSelection, "no policy enforcement")
                statusCell("Mic / computer audio", status.input, "no input device opened")
                statusCell("Permissions", status.permissions, "nothing requested")
                statusCell("OMP assistance", status.omp, "no RPC or model call")
                statusCell("Screenshot capture", status.screenshotCapture, "route only")
                statusCell("Global shortcut routing", status.globalShortcutRouting, "related spike 005")
            }
            Text("Global-shortcut routing is NOT CONNECTED in this UI prototype. The separate 005-global-keyboard-routing spike owns any active interception and its independent review/approval; no hook is implemented here.")
                .font(.caption2)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .cardSurface()
    }

    private func statusCell(_ label: String, _ value: IntegrationStatus, _ note: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.caption2.weight(.medium))
            Badge(text: value.rawValue, color: integrationColor(value))
            Text(note)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
