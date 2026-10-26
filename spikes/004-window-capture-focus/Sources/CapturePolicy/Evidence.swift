import Foundation

public enum RuntimeCellStatus: String, CaseIterable, Codable, Equatable, Sendable {
    case notRun = "NOT RUN"
    case transportObserved = "OBSERVED — RECEIVER TRANSPORT"
    case controlAbsent = "INVALID — CONTROL ABSENT"
    case noReceiverEvidence = "NO RECEIVER EVIDENCE"
    case senderPreviewOnly = "NO RECEIVER EVIDENCE — SENDER PREVIEW ONLY"
    case occluded = "OCCLUDED — NOT INTERPRETABLE"
    case outsideSource = "N/A — INSIDE SELECTED SOURCE REQUIRED"
}

public struct RoiSampleReadback: Codable, Equatable, Sendable {
    public let label: String
    public let nearMarkerFraction: Double
    public let sampledAt: String
    public let width: Int
    public let height: Int

    public init(
        label: String,
        nearMarkerFraction: Double,
        sampledAt: String,
        width: Int,
        height: Int
    ) {
        self.label = label
        self.nearMarkerFraction = nearMarkerFraction
        self.sampledAt = sampledAt
        self.width = width
        self.height = height
    }
}

public struct ReceiverTransportReadback: Codable, Equatable, Sendable {
    public let framesDecoded: Int?
    public let bytesReceived: Int?
    public let frameWidth: Int?
    public let frameHeight: Int?
    public let videoWidth: Int?
    public let videoHeight: Int?
    public let timestamp: Double?

    public init(
        framesDecoded: Int? = nil,
        bytesReceived: Int? = nil,
        frameWidth: Int? = nil,
        frameHeight: Int? = nil,
        videoWidth: Int? = nil,
        videoHeight: Int? = nil,
        timestamp: Double? = nil
    ) {
        self.framesDecoded = framesDecoded
        self.bytesReceived = bytesReceived
        self.frameWidth = frameWidth
        self.frameHeight = frameHeight
        self.videoWidth = videoWidth
        self.videoHeight = videoHeight
        self.timestamp = timestamp
    }
}

public struct RuntimeCellInput: Equatable, Sendable {
    public let cellID: String
    public let sourceKind: String
    public let overlap: String
    public let frontmost: String
    public let treatmentVisible: Bool?
    public let controlVisible: Bool?
    public let occlusionReason: String?
    public let outsideSelectedSource: Bool
    public let senderPreviewOnly: Bool
    public let transport: ReceiverTransportReadback?
    public let roiSamples: [RoiSampleReadback]

    public init(
        cellID: String,
        sourceKind: String,
        overlap: String,
        frontmost: String,
        treatmentVisible: Bool? = nil,
        controlVisible: Bool? = nil,
        occlusionReason: String? = nil,
        outsideSelectedSource: Bool = false,
        senderPreviewOnly: Bool = false,
        transport: ReceiverTransportReadback? = nil,
        roiSamples: [RoiSampleReadback] = []
    ) {
        self.cellID = cellID
        self.sourceKind = sourceKind
        self.overlap = overlap
        self.frontmost = frontmost
        self.treatmentVisible = treatmentVisible
        self.controlVisible = controlVisible
        self.occlusionReason = occlusionReason
        self.outsideSelectedSource = outsideSelectedSource
        self.senderPreviewOnly = senderPreviewOnly
        self.transport = transport
        self.roiSamples = roiSamples
    }
}

public struct RuntimeCellEvidence: Codable, Equatable, Sendable {
    public let cellID: String
    public let sourceKind: String
    public let overlap: String
    public let frontmost: String
    public let treatmentVisible: Bool?
    public let controlVisible: Bool?
    public let occlusionReason: String?
    public let outsideSelectedSource: Bool
    public let senderPreviewOnly: Bool
    public let transport: ReceiverTransportReadback?
    public let roiSamples: [RoiSampleReadback]
    public let status: RuntimeCellStatus
    public let reasons: [String]

    public static func evaluate(_ input: RuntimeCellInput) -> RuntimeCellEvidence {
        var reasons: [String] = []
        let status: RuntimeCellStatus

        if input.outsideSelectedSource {
            status = .outsideSource
            reasons.append(
                "Both markers are outside selected source; the control is absent in this cell, so sharing-flag exclusion cannot be interpreted."
            )
        } else if let occlusionReason = input.occlusionReason,
                  input.treatmentVisible != true || input.controlVisible != true {
            status = .occluded
            reasons.append(
                "Markers were occluded or not positively visible: \(occlusionReason). Both markers must be positively visible before treatment absence is interpreted; occlusion is not treatment-absence evidence."
            )
        } else if input.senderPreviewOnly {
            status = .senderPreviewOnly
            reasons.append(
                "Only the sender preview is available. A sender preview is not a receiver and is not receiver evidence."
            )
        } else if input.controlVisible == false {
            status = .controlAbsent
            reasons.append(
                "The sharing-readOnly control is not positively visible in this cell; control absent, so the cell is invalid for interpretation."
            )
        } else if input.treatmentVisible == nil || input.controlVisible == nil {
            status = .notRun
            reasons.append("Cell observations are incomplete and remain NOT RUN.")
        } else if let transport = input.transport {
            let hasFrames = (transport.framesDecoded ?? 0) > 0
            let hasBytes = (transport.bytesReceived ?? 0) > 0
            let hasTimestamp = transport.timestamp.map { $0.isFinite && $0 > 0 } ?? false
            let hasFrameDimensions =
                (transport.frameWidth ?? 0) > 0 && (transport.frameHeight ?? 0) > 0
            let hasVideoDimensions =
                (transport.videoWidth ?? 0) > 0 && (transport.videoHeight ?? 0) > 0

            if !hasBytes || !hasTimestamp {
                status = .noReceiverEvidence
                reasons.append(
                    "Receiver transport requires positive bytesReceived and a recorded positive timestamp; missing, zero, negative, or non-finite fields are not receiver evidence."
                )
            } else if hasFrames && hasFrameDimensions && hasVideoDimensions {
                status = .transportObserved
                if input.treatmentVisible == false {
                    reasons.append(
                        "Receiver transport and inbound frames are present; the sharing-readOnly control is visible in the same cell. The sharing-none marker absence is one local observation, not a privacy claim."
                    )
                } else {
                    reasons.append(
                        "Receiver transport and inbound frames are present with a positive sharing-readOnly control in the same cell. Marker presence/absence remains a local observation with no stealth claim."
                    )
                }
            } else {
                status = .noReceiverEvidence
                reasons.append(
                    "Receiver transport stats, decoded frames, or dimensions are missing or zero. Transport success without complete inbound video evidence is not receiver evidence."
                )
            }
        } else {
            status = .noReceiverEvidence
            reasons.append(
                "Receiver transport stats are missing. Transport success without inbound video statistics is not receiver evidence."
            )
        }

        return RuntimeCellEvidence(
            cellID: input.cellID,
            sourceKind: input.sourceKind,
            overlap: input.overlap,
            frontmost: input.frontmost,
            treatmentVisible: input.treatmentVisible,
            controlVisible: input.controlVisible,
            occlusionReason: input.occlusionReason,
            outsideSelectedSource: input.outsideSelectedSource,
            senderPreviewOnly: input.senderPreviewOnly,
            transport: input.transport,
            roiSamples: input.roiSamples,
            status: status,
            reasons: reasons
        )
    }
}
