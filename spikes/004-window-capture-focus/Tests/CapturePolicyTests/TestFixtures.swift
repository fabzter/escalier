import Foundation
import CapturePolicy

enum TestFixtures {
    static let markerVisual = MarkerVisualFingerprint(
        headline: "ESCALIER SYNTHETIC MARKER",
        subheadline: "Local capture/focus fixture — not a stealth claim",
        backgroundColorHex: "#10151C",
        roiColorHex: "#FF00AA",
        roiRelativeRect: RectCodable(x: 24, y: 24, width: 96, height: 72),
        windowWidth: 360,
        windowHeight: 220,
        styleMaskRaw: WindowOptionNames.nonactivatingPanelStyleMaskRaw,
        levelRaw: WindowOptionNames.floatingLevelRaw,
        alpha: 1,
        hasShadow: false,
        isOpaque: true,
        collectionBehaviorRaw: WindowOptionNames.canJoinAllSpacesRaw | WindowOptionNames.fullScreenAuxiliaryRaw,
        title: "Escalier synthetic marker"
    )

    static let markerPolicy = FixturePolicies.marker(
        role: .sharingNoneMarker,
        frame: RectCodable(x: 40, y: 300, width: 360, height: 220)
    )

    static func readback(
        role: FixtureWindowRole = .sharingNoneMarker,
        sharingRequested: SharingPolicy = .sharingNone,
        sharingObservedRaw: UInt? = nil,
        ignoresMouseEvents: Bool = false,
        ignoresMouseEventsRequested: Bool = false,
        styleMaskRaw: UInt = WindowOptionNames.nonactivatingPanelStyleMaskRaw,
        levelRaw: Int = WindowOptionNames.floatingLevelRaw,
        alpha: Double = 1,
        hasShadow: Bool = false,
        isOpaque: Bool = true,
        isVisible: Bool = true,
        isKeyWindow: Bool = false,
        isMainWindow: Bool = false,
        becomesKeyOnlyIfNeeded: Bool = true,
        isFloatingPanel: Bool = true,
        collectionBehaviorRaw: UInt = WindowOptionNames.canJoinAllSpacesRaw | WindowOptionNames.fullScreenAuxiliaryRaw,
        title: String = "Escalier synthetic marker"
    ) -> WindowReadback {
        WindowReadback(
            role: role,
            title: title,
            sharingRequested: sharingRequested,
            sharingObservedRaw: sharingObservedRaw,
            styleMaskRaw: styleMaskRaw,
            levelRaw: levelRaw,
            alpha: alpha,
            hasShadow: hasShadow,
            isOpaque: isOpaque,
            ignoresMouseEvents: ignoresMouseEvents,
            ignoresMouseEventsRequested: ignoresMouseEventsRequested,
            isVisible: isVisible,
            isKeyWindow: isKeyWindow,
            isMainWindow: isMainWindow,
            canBecomeKey: !isFloatingPanel,
            canBecomeMain: !isFloatingPanel,
            becomesKeyOnlyIfNeeded: becomesKeyOnlyIfNeeded,
            isFloatingPanel: isFloatingPanel,
            hidesOnDeactivate: false,
            isMovableByWindowBackground: true,
            occlusionVisible: isVisible,
            frame: RectCodable(x: 40, y: 300, width: 360, height: 220),
            collectionBehaviorRaw: collectionBehaviorRaw
        )
    }

    static func appReadback(
        observedRaw: Int = WindowOptionNames.regularActivationRaw,
        requestedRaw: Int = WindowOptionNames.regularActivationRaw,
        isActive: Bool = true
    ) -> AppReadback {
        AppReadback(
            activationPolicyObservedRaw: observedRaw,
            activationPolicyRequestedRaw: requestedRaw,
            isActive: isActive
        )
    }

    static func report(
        windows: [WindowReadback]? = nil,
        app: AppReadback = appReadback(),
        policyMismatches: [PolicyMismatch] = [],
        counters: ClickThroughCounters = ClickThroughCounters(),
        eventJournal: [String] = ["fixture-readback"],
        lifecycleJournal: [LifecycleEntry] = []
    ) -> ReadbackReport {
        ReadbackReport(
            app: app,
            windows: windows ?? [
                readback(
                    role: .sharingNoneMarker,
                    sharingRequested: .sharingNone,
                    sharingObservedRaw: SharingPolicy.sharingNone.appKitRawValue
                ),
                readback(
                    role: .sharingReadOnlyMarker,
                    sharingRequested: .sharingReadOnly,
                    sharingObservedRaw: SharingPolicy.sharingReadOnly.appKitRawValue
                )
            ],
            policyMismatches: policyMismatches,
            counters: counters,
            eventJournal: eventJournal,
            lifecycleJournal: lifecycleJournal
        )
    }

    static func receiverTransport(
        framesDecoded: Int? = 90,
        bytesReceived: Int? = 400_000,
        frameWidth: Int? = 1920,
        frameHeight: Int? = 1080,
        videoWidth: Int? = 1920,
        videoHeight: Int? = 1080,
        timestamp: Double? = 1_234
    ) -> ReceiverTransportReadback {
        ReceiverTransportReadback(
            framesDecoded: framesDecoded,
            bytesReceived: bytesReceived,
            frameWidth: frameWidth,
            frameHeight: frameHeight,
            videoWidth: videoWidth,
            videoHeight: videoHeight,
            timestamp: timestamp
        )
    }

    static let roiSample = RoiSampleReadback(
        label: "control-readOnly",
        nearMarkerFraction: 0.97,
        sampledAt: "1970-01-01T00:00:01.000Z",
        width: 32,
        height: 32
    )

    static func cell(
        status: RuntimeCellStatus? = nil,
        memberwise: (inout CellInputs) -> Void = { _ in }
    ) -> RuntimeCellEvidence {
        var inputs = CellInputs()
        memberwise(&inputs)
        return RuntimeCellEvidence.evaluate(inputs.makeInput())
    }
}

struct CellInputs {
    var cellID = "display-both-markers"
    var sourceKind = "entire-display"
    var overlap = "nonoverlap"
    var frontmost = "browser"
    var treatmentVisible: Bool? = true
    var controlVisible: Bool? = true
    var occlusionReason: String? = nil
    var outsideSelectedSource = false
    var senderPreviewOnly = false
    var transport: ReceiverTransportReadback? = TestFixtures.receiverTransport()
    var roiSamples: [RoiSampleReadback] = [TestFixtures.roiSample]

    func makeInput() -> RuntimeCellInput {
        RuntimeCellInput(
            cellID: cellID,
            sourceKind: sourceKind,
            overlap: overlap,
            frontmost: frontmost,
            treatmentVisible: treatmentVisible,
            controlVisible: controlVisible,
            occlusionReason: occlusionReason,
            outsideSelectedSource: outsideSelectedSource,
            senderPreviewOnly: senderPreviewOnly,
            transport: transport,
            roiSamples: roiSamples
        )
    }
}
