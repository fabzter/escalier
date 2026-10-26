import Foundation

public struct MockModel: Identifiable, Equatable {
    public let id: String
    public let name: String

    public init(id: String, name: String) {
        self.id = id
        self.name = name
    }
}

public struct MockCapability: Identifiable, Equatable {
    public let id: String
    public let name: String

    public init(id: String, name: String) {
        self.id = id
        self.name = name
    }
}

/// Invented UI-only choices. These IDs are not sent anywhere and enforce nothing.
public enum MockCapabilityCatalog {
    public static let models: [MockModel] = [
        MockModel(id: "mock-model-balanced", name: "MOCK balanced model"),
        MockModel(id: "mock-model-fast", name: "MOCK fast model")
    ]

    public static let tools: [MockCapability] = [
        MockCapability(id: "mock-notes", name: "MOCK notes tool"),
        MockCapability(id: "mock-search", name: "MOCK retrieval tool")
    ]

    public static let skills: [MockCapability] = [
        MockCapability(id: "mock-briefing", name: "MOCK briefing skill"),
        MockCapability(id: "mock-tone", name: "MOCK tone skill")
    ]

    public static let modelIDs = Set(models.map(\.id))
    public static let toolIDs = Set(tools.map(\.id))
    public static let skillIDs = Set(skills.map(\.id))
}

/// Per-conversation mock selections. The UI explicitly labels these as MOCK and does
/// not claim model routing or tool/skill enforcement.
public struct ConversationCapabilities: Equatable {
    public var selectedModelID: String?
    public var enabledToolIDs: Set<String>
    public var enabledSkillIDs: Set<String>

    public init(
        selectedModelID: String? = nil,
        enabledToolIDs: Set<String> = [],
        enabledSkillIDs: Set<String> = []
    ) {
        self.selectedModelID = selectedModelID
        self.enabledToolIDs = enabledToolIDs
        self.enabledSkillIDs = enabledSkillIDs
    }

    public static let prototypeDefault = ConversationCapabilities(
        selectedModelID: "mock-model-balanced",
        enabledToolIDs: ["mock-notes"],
        enabledSkillIDs: ["mock-briefing"]
    )

    public var selectedModelName: String {
        guard let selectedModelID,
              let model = MockCapabilityCatalog.models.first(where: { $0.id == selectedModelID })
        else {
            return "No MOCK model selected"
        }
        return model.name
    }

    @discardableResult
    public mutating func setSelectedModel(id: String?) -> Bool {
        guard let id else {
            selectedModelID = nil
            return true
        }
        guard MockCapabilityCatalog.modelIDs.contains(id) else { return false }
        selectedModelID = id
        return true
    }

    @discardableResult
    public mutating func toggleTool(id: String) -> Bool {
        guard MockCapabilityCatalog.toolIDs.contains(id) else { return false }
        if enabledToolIDs.contains(id) {
            enabledToolIDs.remove(id)
        } else {
            enabledToolIDs.insert(id)
        }
        return true
    }

    @discardableResult
    public mutating func toggleSkill(id: String) -> Bool {
        guard MockCapabilityCatalog.skillIDs.contains(id) else { return false }
        if enabledSkillIDs.contains(id) {
            enabledSkillIDs.remove(id)
        } else {
            enabledSkillIDs.insert(id)
        }
        return true
    }
}
