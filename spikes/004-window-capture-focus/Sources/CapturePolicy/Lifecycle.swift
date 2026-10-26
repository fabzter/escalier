import Foundation

public enum LifecycleStage: String, CaseIterable, Codable, Equatable, Sendable {
    case createMarkers = "create-markers"
    case showMarkers = "show-markers"
    case hideMarkers = "hide-markers"
    case reshowMarkers = "reshow-markers"
    case activateFixture = "activate-fixture"
    case deactivateFixture = "deactivate-fixture"
    case switchToAccessory = "switch-to-accessory"
    case switchToRegular = "switch-to-regular"
}

public struct LifecycleStep: Codable, Equatable, Sendable {
    public let stage: LifecycleStage
    public let expectsReadback: Bool

    public init(stage: LifecycleStage, expectsReadback: Bool = true) {
        self.stage = stage
        self.expectsReadback = expectsReadback
    }

    public static func standard() -> [LifecycleStep] {
        LifecycleStage.allCases.map { LifecycleStep(stage: $0, expectsReadback: true) }
    }
}

public enum LifecycleError: Error, Equatable {
    case emptyReadback
}

public struct LifecycleEntry: Codable, Equatable, Sendable {
    public let stage: LifecycleStage
    public let requestedSummary: String
    public let capturedAt: String
    public let activationPolicyObserved: String
    public let isActive: Bool
    public let windowRoles: [FixtureWindowRole]
    public let policyMismatches: [PolicyMismatch]
    public let missingWindowRoles: [FixtureWindowRole]

    public init(
        stage: LifecycleStage,
        requestedSummary: String,
        capturedAt: String,
        activationPolicyObserved: String,
        isActive: Bool,
        windowRoles: [FixtureWindowRole],
        policyMismatches: [PolicyMismatch],
        missingWindowRoles: [FixtureWindowRole]
    ) {
        self.stage = stage
        self.requestedSummary = requestedSummary
        self.capturedAt = capturedAt
        self.activationPolicyObserved = activationPolicyObserved
        self.isActive = isActive
        self.windowRoles = windowRoles
        self.policyMismatches = policyMismatches
        self.missingWindowRoles = missingWindowRoles
    }

    public var hasReadback: Bool {
        !windowRoles.isEmpty && !capturedAt.isEmpty
    }
}

public struct LifecycleRecorder: Sendable {
    public private(set) var entries: [LifecycleEntry]

    public init(entries: [LifecycleEntry] = []) {
        self.entries = entries
    }

    public mutating func record(
        stage: LifecycleStage,
        requestedSummary: String,
        report: ReadbackReport
    ) throws {
        guard !report.windows.isEmpty, !report.capturedAt.isEmpty else {
            throw LifecycleError.emptyReadback
        }
        let entry = LifecycleEntry(
            stage: stage,
            requestedSummary: requestedSummary,
            capturedAt: report.capturedAt,
            activationPolicyObserved: report.app.activationPolicyObserved,
            isActive: report.app.isActive,
            windowRoles: report.windows.map(\.role),
            policyMismatches: report.policyMismatches,
            missingWindowRoles: report.missingWindowRoles
        )
        entries.append(entry)
    }

    public func missingReadbacks(for steps: [LifecycleStep]) -> [LifecycleStage] {
        let recorded = Set(entries.map(\.stage))
        return steps
            .filter(\.expectsReadback)
            .map(\.stage)
            .filter { !recorded.contains($0) }
    }
}
