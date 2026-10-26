import Foundation
import XCTest
import CapturePolicy

final class EvidenceTests: XCTestCase {
    func testUnrecordedCellRemainsNotRun() {
        let evidence = RuntimeCellEvidence.evaluate(
            RuntimeCellInput(
                cellID: "unrecorded",
                sourceKind: "entire-display",
                overlap: "unknown",
                frontmost: "unknown",
                treatmentVisible: nil,
                controlVisible: nil
            )
        )
        XCTAssertEqual(evidence.status, .notRun)
        XCTAssertFalse(evidence.status.rawValue.contains("PASS"))
    }

    func testTransportWithPositiveControlIsObservedButNeverCalledPass() {
        let evidence = TestFixtures.cell()
        XCTAssertEqual(evidence.status, .transportObserved)
        XCTAssertTrue(evidence.reasons.joined(separator: " ").lowercased().contains("no stealth claim"))
        XCTAssertFalse(evidence.status.rawValue.contains("PASS"))
    }

    func testControlAbsentInvalidatesTreatmentInterpretation() {
        let evidence = TestFixtures.cell { inputs in
            inputs.controlVisible = false
            inputs.treatmentVisible = true
        }
        XCTAssertEqual(evidence.status, .controlAbsent)
        XCTAssertTrue(evidence.reasons.joined(separator: " ").lowercased().contains("control absent"))
    }

    func testBothMarkersOutsideSelectedSourceIsNotApplicableNotProtectionEvidence() {
        let evidence = TestFixtures.cell { inputs in
            inputs.sourceKind = "selected-browser-window"
            inputs.outsideSelectedSource = true
            inputs.treatmentVisible = false
            inputs.controlVisible = false
            inputs.transport = nil
        }
        XCTAssertEqual(evidence.status, .outsideSource)
        XCTAssertTrue(evidence.reasons.joined(separator: " ").lowercased().contains("outside selected source"))
        XCTAssertFalse(evidence.status.rawValue.lowercased().contains("protect"))
    }

    func testOcclusionIsNotTreatedAsTreatmentAbsenceEvidence() {
        let evidence = TestFixtures.cell { inputs in
            inputs.occlusionReason = "both markers behind browser window"
            inputs.treatmentVisible = false
            inputs.controlVisible = false
            inputs.transport = nil
        }
        XCTAssertEqual(evidence.status, .occluded)
        XCTAssertTrue(evidence.reasons.joined(separator: " ").lowercased().contains("occluded"))
    }

    func testMissingReceiverStatsMeansNoReceiverEvidenceEvenIfMarkersVisible() {
        let evidence = TestFixtures.cell { inputs in
            inputs.transport = nil
        }
        XCTAssertEqual(evidence.status, .noReceiverEvidence)
        XCTAssertTrue(evidence.reasons.joined(separator: " ").lowercased().contains("transport"))
    }

    func testMissingZeroOrNegativeBytesReceivedMeansNoReceiverEvidence() {
        for value in [nil, 0, -1] {
            let evidence = TestFixtures.cell { inputs in
                inputs.transport = TestFixtures.receiverTransport(bytesReceived: value)
            }
            XCTAssertEqual(evidence.status, .noReceiverEvidence, "bytesReceived=\(String(describing: value))")
            XCTAssertTrue(
                evidence.reasons.joined(separator: " ").contains("bytesReceived"),
                "bytesReceived=\(String(describing: value))"
            )
        }
    }

    func testMissingZeroNegativeOrNonFiniteTimestampMeansNoReceiverEvidence() {
        for value in [nil, 0.0, -1.0, Double.nan, Double.infinity] {
            let evidence = TestFixtures.cell { inputs in
                inputs.transport = TestFixtures.receiverTransport(timestamp: value)
            }
            XCTAssertEqual(evidence.status, .noReceiverEvidence, "timestamp=\(String(describing: value))")
            XCTAssertTrue(
                evidence.reasons.joined(separator: " ").contains("timestamp"),
                "timestamp=\(String(describing: value))"
            )
        }
    }

    func testTreatmentOccludedButControlVisibleRemainsOccluded() {
        let evidence = TestFixtures.cell { inputs in
            inputs.occlusionReason = "treatment marker behind browser window"
            inputs.treatmentVisible = false
            inputs.controlVisible = true
        }
        XCTAssertEqual(evidence.status, .occluded)
        XCTAssertTrue(evidence.reasons.joined(separator: " ").lowercased().contains("occluded"))
        XCTAssertFalse(evidence.reasons.joined(separator: " ").lowercased().contains("absence is one local observation"))
    }

    func testZeroFramesMeansNoReceiverEvidence() {
        let evidence = TestFixtures.cell { inputs in
            inputs.transport = TestFixtures.receiverTransport(framesDecoded: 0)
        }
        XCTAssertEqual(evidence.status, .noReceiverEvidence)
    }

    func testMissingReceiverVideoDimensionsMeansNoReceiverEvidence() {
        let evidence = TestFixtures.cell { inputs in
            inputs.transport = TestFixtures.receiverTransport(videoWidth: 0)
        }
        XCTAssertEqual(evidence.status, .noReceiverEvidence)
    }

    func testSenderPreviewOnlyIsExplicitlyRejected() {
        let evidence = TestFixtures.cell { inputs in
            inputs.senderPreviewOnly = true
        }
        XCTAssertEqual(evidence.status, .senderPreviewOnly)
        XCTAssertTrue(evidence.reasons.joined(separator: " ").lowercased().contains("sender preview"))
    }

    func testRoiSamplesCarryMetadataOnlyNoPixels() throws {
        let evidence = TestFixtures.cell()
        XCTAssertEqual(evidence.roiSamples.count, 1)
        let data = try JSONEncoder().encode(evidence)
        let text = try XCTUnwrap(String(data: data, encoding: .utf8)).lowercased()
        XCTAssertFalse(text.contains("\"pixels\""))
        XCTAssertFalse(text.contains("\"rgba\""))
        XCTAssertFalse(text.contains("data:image"))
        XCTAssertTrue(text.contains("nearmarkerfraction"))
    }

    func testRequiredManualEvidenceFieldsCoverPreflightSchema() {
        let fields = Set(EvidenceSchema.requiredManualFields)
        for expected in [
            "os_version", "app_build", "browser_name_version", "source_kind",
            "source_dimensions", "display_arrangement_scale", "permission_state",
            "audio_track_count", "receiver_transport_stats", "receiver_frames_decoded",
            "receiver_bytes_received", "receiver_video_dimensions", "marker_roi_samples",
            "positive_control", "focus_event_log", "window_policy_readback",
            "clean_display_protocol", "permission_protocol", "limitations"
        ] {
            XCTAssertTrue(fields.contains(expected), "missing manual evidence field: \(expected)")
        }
    }
}
