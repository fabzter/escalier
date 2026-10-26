import Foundation

public struct WindowReference: Codable, Equatable, Sendable {
    public let present: Bool
    public let role: FixtureWindowRole?
    public let title: String?

    public static let absent = WindowReference(present: false, role: nil, title: nil)

    public init(present: Bool, role: FixtureWindowRole? = nil, title: String? = nil) {
        self.present = present
        self.role = role
        self.title = title
    }
}

public struct FrontmostAppReadback: Codable, Equatable, Sendable {
    public let available: Bool
    public let localizedName: String?
    public let bundleIdentifier: String?
    public let activationPolicy: String?
    public let isFixtureProcess: Bool

    public static let unavailable = FrontmostAppReadback(
        available: false,
        localizedName: nil,
        bundleIdentifier: nil,
        activationPolicy: nil,
        isFixtureProcess: false
    )

    public init(
        available: Bool,
        localizedName: String? = nil,
        bundleIdentifier: String? = nil,
        activationPolicy: String? = nil,
        isFixtureProcess: Bool = false
    ) {
        self.available = available
        self.localizedName = localizedName
        self.bundleIdentifier = bundleIdentifier
        self.activationPolicy = activationPolicy
        self.isFixtureProcess = isFixtureProcess
    }
}

public struct ScreenReadback: Codable, Equatable, Sendable {
    public let frame: RectCodable
    public let visibleFrame: RectCodable
    public let backingScaleFactor: Double

    public init(frame: RectCodable, visibleFrame: RectCodable, backingScaleFactor: Double) {
        self.frame = frame
        self.visibleFrame = visibleFrame
        self.backingScaleFactor = backingScaleFactor
    }
}

public struct PolicyMismatch: Codable, Equatable, Sendable {
    public let scope: String
    public let field: String
    public let requested: String
    public let observed: String

    public init(scope: String, field: String, requested: String, observed: String) {
        self.scope = scope
        self.field = field
        self.requested = requested
        self.observed = observed
    }
}

public struct AppReadback: Codable, Equatable, Sendable {
    public let activationPolicyObservedRaw: Int
    public let activationPolicyObserved: String
    public let activationPolicyRequestedRaw: Int
    public let activationPolicyRequested: String
    public let isActive: Bool
    public let keyWindow: WindowReference
    public let mainWindow: WindowReference
    public let frontmostApplication: FrontmostAppReadback
    public let screens: [ScreenReadback]

    public init(
        activationPolicyObservedRaw: Int = WindowOptionNames.regularActivationRaw,
        activationPolicyRequestedRaw: Int = WindowOptionNames.regularActivationRaw,
        isActive: Bool = true,
        keyWindow: WindowReference = .absent,
        mainWindow: WindowReference = .absent,
        frontmostApplication: FrontmostAppReadback = .unavailable,
        screens: [ScreenReadback] = []
    ) {
        self.activationPolicyObservedRaw = activationPolicyObservedRaw
        self.activationPolicyObserved = WindowOptionNames.activationPolicyName(
            forRaw: activationPolicyObservedRaw
        )
        self.activationPolicyRequestedRaw = activationPolicyRequestedRaw
        self.activationPolicyRequested = WindowOptionNames.activationPolicyName(
            forRaw: activationPolicyRequestedRaw
        )
        self.isActive = isActive
        self.keyWindow = keyWindow
        self.mainWindow = mainWindow
        self.frontmostApplication = frontmostApplication
        self.screens = screens
    }

    public func activationPolicyMismatch() -> PolicyMismatch? {
        guard activationPolicyObservedRaw != activationPolicyRequestedRaw else {
            return nil
        }
        return PolicyMismatch(
            scope: "app",
            field: "activationPolicy",
            requested: activationPolicyRequested,
            observed: activationPolicyObserved
        )
    }
}

public struct WindowReadback: Codable, Equatable, Sendable {
    public let role: FixtureWindowRole
    public let title: String
    public let sharingRequested: SharingPolicy
    public let sharingObservedRaw: UInt
    public let sharingObservedName: String
    public let styleMaskRaw: UInt
    public let styleMaskNames: [String]
    public let levelRaw: Int
    public let levelName: String
    public let alpha: Double
    public let hasShadow: Bool
    public let isOpaque: Bool
    public let ignoresMouseEvents: Bool
    public let ignoresMouseEventsRequested: Bool
    public let isVisible: Bool
    public let isKeyWindow: Bool
    public let isMainWindow: Bool
    public let canBecomeKey: Bool
    public let canBecomeMain: Bool
    public let becomesKeyOnlyIfNeeded: Bool
    public let isFloatingPanel: Bool
    public let hidesOnDeactivate: Bool
    public let isMovableByWindowBackground: Bool
    public let occlusionVisible: Bool
    public let frame: RectCodable
    public let collectionBehaviorRaw: UInt
    public let collectionBehaviorNames: [String]

    public init(
        role: FixtureWindowRole,
        title: String = FixturePolicies.markerTitle,
        sharingRequested: SharingPolicy = .sharingReadOnly,
        sharingObservedRaw: UInt? = nil,
        styleMaskRaw: UInt = WindowOptionNames.nonactivatingPanelStyleMaskRaw,
        levelRaw: Int = WindowOptionNames.floatingLevelRaw,
        alpha: Double = 1,
        hasShadow: Bool = false,
        isOpaque: Bool = true,
        ignoresMouseEvents: Bool = false,
        ignoresMouseEventsRequested: Bool = false,
        isVisible: Bool = true,
        isKeyWindow: Bool = false,
        isMainWindow: Bool = false,
        canBecomeKey: Bool = false,
        canBecomeMain: Bool = false,
        becomesKeyOnlyIfNeeded: Bool = true,
        isFloatingPanel: Bool = true,
        hidesOnDeactivate: Bool = false,
        isMovableByWindowBackground: Bool = true,
        occlusionVisible: Bool = true,
        frame: RectCodable = RectCodable(x: 0, y: 0, width: 360, height: 220),
        collectionBehaviorRaw: UInt = FixturePolicies.markerCollectionBehaviorRaw
    ) {
        let observedRaw = sharingObservedRaw ?? sharingRequested.appKitRawValue
        self.role = role
        self.title = title
        self.sharingRequested = sharingRequested
        self.sharingObservedRaw = observedRaw
        self.sharingObservedName = SharingPolicy.observedName(forRaw: observedRaw)
        self.styleMaskRaw = styleMaskRaw
        self.styleMaskNames = WindowOptionNames.styleMaskNames(forRaw: styleMaskRaw)
        self.levelRaw = levelRaw
        self.levelName = WindowOptionNames.levelName(forRaw: levelRaw)
        self.alpha = alpha
        self.hasShadow = hasShadow
        self.isOpaque = isOpaque
        self.ignoresMouseEvents = ignoresMouseEvents
        self.ignoresMouseEventsRequested = ignoresMouseEventsRequested
        self.isVisible = isVisible
        self.isKeyWindow = isKeyWindow
        self.isMainWindow = isMainWindow
        self.canBecomeKey = canBecomeKey
        self.canBecomeMain = canBecomeMain
        self.becomesKeyOnlyIfNeeded = becomesKeyOnlyIfNeeded
        self.isFloatingPanel = isFloatingPanel
        self.hidesOnDeactivate = hidesOnDeactivate
        self.isMovableByWindowBackground = isMovableByWindowBackground
        self.occlusionVisible = occlusionVisible
        self.frame = frame
        self.collectionBehaviorRaw = collectionBehaviorRaw
        self.collectionBehaviorNames = WindowOptionNames.collectionBehaviorNames(
            forRaw: collectionBehaviorRaw
        )
    }

    public func mismatches(against request: FixtureWindowPolicy) -> [PolicyMismatch] {
        var mismatches: [PolicyMismatch] = []

        func add(_ field: String, _ requested: String, _ observed: String) {
            mismatches.append(
                PolicyMismatch(
                    scope: role.rawValue,
                    field: field,
                    requested: requested,
                    observed: observed
                )
            )
        }

        if sharingObservedRaw != request.sharing.appKitRawValue {
            add("sharing", request.sharing.rawValue, sharingObservedName)
        }
        if styleMaskRaw != request.styleMaskRaw {
            add("styleMaskRaw", "\(request.styleMaskRaw)", "\(styleMaskRaw)")
        }
        if levelRaw != request.levelRaw {
            add("levelRaw", "\(request.levelRaw)", "\(levelRaw)")
        }
        if abs(alpha - request.alpha) > 0.0001 {
            add("alpha", "\(request.alpha)", "\(alpha)")
        }
        if hasShadow != request.hasShadow {
            add("hasShadow", "\(request.hasShadow)", "\(hasShadow)")
        }
        if isOpaque != request.isOpaque {
            add("isOpaque", "\(request.isOpaque)", "\(isOpaque)")
        }
        if ignoresMouseEvents != request.ignoresMouseEvents {
            add("ignoresMouseEvents", "\(request.ignoresMouseEvents)", "\(ignoresMouseEvents)")
        }
        if hidesOnDeactivate != request.hidesOnDeactivate {
            add("hidesOnDeactivate", "\(request.hidesOnDeactivate)", "\(hidesOnDeactivate)")
        }
        if becomesKeyOnlyIfNeeded != request.becomesKeyOnlyIfNeeded {
            add(
                "becomesKeyOnlyIfNeeded",
                "\(request.becomesKeyOnlyIfNeeded)",
                "\(becomesKeyOnlyIfNeeded)"
            )
        }
        if isFloatingPanel != request.isFloatingPanel {
            add("isFloatingPanel", "\(request.isFloatingPanel)", "\(isFloatingPanel)")
        }
        if collectionBehaviorRaw != request.collectionBehaviorRaw {
            add(
                "collectionBehaviorRaw",
                "\(request.collectionBehaviorRaw)",
                "\(collectionBehaviorRaw)"
            )
        }
        if title != request.title {
            add("title", request.title, title)
        }
        return mismatches
    }
}

public enum FixtureBuildKind: String, Codable, Equatable, Sendable {
    case appBundle = "app-bundle"
    case unbundledExecutable = "unbundled-executable"
}

public struct FixtureIdentity: Codable, Equatable, Sendable {
    public static let spikeID = "004-window-capture-focus"
    public static let claimBoundary =
        "Synthetic local fixture. Window policy flags and native readback are not receiver-pixel evidence; no stealth, invisibility, or HackerRank-result claim."
    public static let synthetic = true

    public let spikeID: String
    public let appName: String
    public let synthetic: Bool
    public let buildKind: FixtureBuildKind
    public let bundleIdentifier: String?
    public let claimBoundary: String

    public init(
        appName: String,
        buildKind: FixtureBuildKind,
        bundleIdentifier: String?
    ) {
        self.spikeID = FixtureIdentity.spikeID
        self.appName = appName
        self.synthetic = FixtureIdentity.synthetic
        self.buildKind = buildKind
        self.bundleIdentifier = bundleIdentifier
        self.claimBoundary = FixtureIdentity.claimBoundary
    }
}

public struct ReadbackReport: Codable, Equatable, Sendable {
    public static let schemaVersion = 1
    public static let defaultWorkerRuntimeStatus = "NOT RUN IN WORKER"
    public static let defaultEvidenceStatus = "NO RECEIVER EVIDENCE — NATIVE READBACK ONLY"
    public static let defaultLimitations = [
        "Window flags and readback are not receiver-pixel evidence.",
        "No capture, focus, click-through, or stealth result is established by this build.",
        "Frontmost-app identity may be unavailable; no permission escalation is attempted.",
        "Display arrangement and scale must be recorded from the actual runtime session.",
        "A synthetic local result does not establish HackerRank or any third-party server behavior."
    ]

    public let schemaVersion: Int
    public let spikeID: String
    public let identity: FixtureIdentity
    public let capturedAt: String
    public let app: AppReadback
    public let expectedWindowRoles: [FixtureWindowRole]
    public let windows: [WindowReadback]
    public let missingWindowRoles: [FixtureWindowRole]
    public let policyMismatches: [PolicyMismatch]
    public let counters: ClickThroughCounters
    public let eventJournal: [String]
    public let lifecycleJournal: [LifecycleEntry]
    public let workerRuntimeStatus: String
    public let evidenceStatus: String
    public let limitations: [String]

    public init(
        identity: FixtureIdentity = FixtureIdentity(
            appName: "Escalier Synthetic Capture Fixture",
            buildKind: .unbundledExecutable,
            bundleIdentifier: nil
        ),
        capturedAt: String = "1970-01-01T00:00:00.000Z",
        app: AppReadback = AppReadback(),
        expectedWindowRoles: [FixtureWindowRole] = FixtureWindowRole.readbackOrder,
        windows: [WindowReadback],
        policyMismatches: [PolicyMismatch] = [],
        counters: ClickThroughCounters = ClickThroughCounters(),
        eventJournal: [String] = [],
        lifecycleJournal: [LifecycleEntry] = [],
        workerRuntimeStatus: String = ReadbackReport.defaultWorkerRuntimeStatus,
        evidenceStatus: String = ReadbackReport.defaultEvidenceStatus,
        limitations: [String] = ReadbackReport.defaultLimitations
    ) {
        let presentRoles = Set(windows.map(\.role))
        self.schemaVersion = ReadbackReport.schemaVersion
        self.spikeID = FixtureIdentity.spikeID
        self.identity = identity
        self.capturedAt = capturedAt
        self.app = app
        self.expectedWindowRoles = expectedWindowRoles
        self.windows = windows
        self.missingWindowRoles = expectedWindowRoles.filter { !presentRoles.contains($0) }
        self.policyMismatches = policyMismatches
        self.counters = counters
        self.eventJournal = eventJournal
        self.lifecycleJournal = lifecycleJournal
        self.workerRuntimeStatus = workerRuntimeStatus
        self.evidenceStatus = evidenceStatus
        self.limitations = limitations
    }
}

public enum EvidenceSchema {
    public static let requiredManualFields: [String] = [
        "os_version",
        "app_build",
        "browser_name_version",
        "source_kind",
        "source_dimensions",
        "display_arrangement_scale",
        "permission_state",
        "audio_track_count",
        "receiver_transport_stats",
        "receiver_frames_decoded",
        "receiver_bytes_received",
        "receiver_video_dimensions",
        "marker_roi_samples",
        "positive_control",
        "focus_event_log",
        "window_policy_readback",
        "clean_display_protocol",
        "permission_protocol",
        "limitations"
    ]

    public static let requiredWindowFields: [String] = [
        "role",
        "title",
        "sharingRequested",
        "sharingObservedRaw",
        "sharingObservedName",
        "styleMaskRaw",
        "styleMaskNames",
        "levelRaw",
        "levelName",
        "alpha",
        "hasShadow",
        "isOpaque",
        "ignoresMouseEvents",
        "ignoresMouseEventsRequested",
        "isVisible",
        "isKeyWindow",
        "isMainWindow",
        "canBecomeKey",
        "canBecomeMain",
        "becomesKeyOnlyIfNeeded",
        "isFloatingPanel",
        "hidesOnDeactivate",
        "isMovableByWindowBackground",
        "occlusionVisible",
        "frame",
        "collectionBehaviorRaw",
        "collectionBehaviorNames"
    ]

    public static let requiredAppFields: [String] = [
        "activationPolicyObservedRaw",
        "activationPolicyObserved",
        "activationPolicyRequestedRaw",
        "activationPolicyRequested",
        "isActive",
        "keyWindow",
        "mainWindow",
        "frontmostApplication",
        "screens"
    ]

    public static let requiredReportFields: [String] = [
        "schemaVersion",
        "spikeID",
        "identity",
        "capturedAt",
        "app",
        "expectedWindowRoles",
        "windows",
        "missingWindowRoles",
        "policyMismatches",
        "counters",
        "eventJournal",
        "lifecycleJournal",
        "workerRuntimeStatus",
        "evidenceStatus",
        "limitations"
    ]
}
