import Foundation
import XCTest
import CapturePolicy

final class ReadbackTests: XCTestCase {
    func testWindowReadbackEncodesEveryRequiredField() throws {
        let readback = TestFixtures.readback()
        let data = try JSONEncoder().encode(readback)
        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any]
        )
        for key in EvidenceSchema.requiredWindowFields {
            XCTAssertNotNil(object[key], "missing window readback field: \(key)")
            XCTAssertFalse(object[key] is NSNull, "null window readback field: \(key)")
        }
        XCTAssertEqual(object["sharingObservedName"] as? String, "sharing-none")
        XCTAssertEqual(object["levelName"] as? String, "floating")
        XCTAssertTrue(
            (object["styleMaskNames"] as? [String])?.contains("nonactivatingPanel") == true
        )
        XCTAssertTrue(
            (object["collectionBehaviorNames"] as? [String])?.contains("canJoinAllSpaces") == true
        )
    }

    func testWindowReadbackRoundTripsWithStableOrdering() throws {
        let original = TestFixtures.readback(ignoresMouseEvents: true, ignoresMouseEventsRequested: true)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(original)
        let decoded = try JSONDecoder().decode(WindowReadback.self, from: data)
        XCTAssertEqual(decoded, original)
        let text = try XCTUnwrap(String(data: data, encoding: .utf8))
        XCTAssertTrue(text.hasPrefix("{\"alpha\":"), "expected sorted-key JSON: \(text)")
    }

    func testSharingRequestedVersusObservedMismatchIsExplicit() {
        let request = TestFixtures.markerPolicy // sharing-none
        let observedReadOnly = TestFixtures.readback(
            role: .sharingNoneMarker,
            sharingRequested: .sharingNone,
            sharingObservedRaw: SharingPolicy.sharingReadOnly.appKitRawValue
        )
        let mismatches = observedReadOnly.mismatches(against: request)
        XCTAssertTrue(mismatches.contains { $0.field == "sharing" && $0.scope == "marker-sharing-none" })
    }

    func testMatchingWindowPolicyHasNoMismatches() {
        let request = TestFixtures.markerPolicy
        let observed = TestFixtures.readback(
            role: .sharingNoneMarker,
            sharingRequested: .sharingNone,
            sharingObservedRaw: SharingPolicy.sharingNone.appKitRawValue
        )
        XCTAssertEqual(observed.mismatches(against: request), [])
    }

    func testClickThroughAndCollectionMismatchesAreExplicit() {
        let request = FixturePolicies.clickThroughPanel(intercept: true)
        let observed = TestFixtures.readback(
            role: .clickThroughPanel,
            sharingRequested: .sharingReadOnly,
            sharingObservedRaw: SharingPolicy.sharingReadOnly.appKitRawValue,
            ignoresMouseEvents: true,
            ignoresMouseEventsRequested: true,
            collectionBehaviorRaw: 0,
            title: request.title
        )
        let fields = Set(observed.mismatches(against: request).map(\.field))
        XCTAssertTrue(fields.contains("ignoresMouseEvents"))
        XCTAssertTrue(fields.contains("collectionBehaviorRaw"))
    }

    func testAppActivationMismatchIsExplicit() {
        let app = TestFixtures.appReadback(
            observedRaw: WindowOptionNames.regularActivationRaw,
            requestedRaw: WindowOptionNames.accessoryActivationRaw
        )
        let mismatch = app.activationPolicyMismatch()
        XCTAssertEqual(mismatch?.scope, "app")
        XCTAssertEqual(mismatch?.field, "activationPolicy")
        XCTAssertEqual(mismatch?.requested, "accessory")
        XCTAssertEqual(mismatch?.observed, "regular")
    }

    func testReportEncodesAllRequiredTopLevelAndNestedFields() throws {
        let report = TestFixtures.report()
        let data = try JSONEncoder().encode(report)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        for key in EvidenceSchema.requiredReportFields {
            XCTAssertNotNil(object[key], "missing report field: \(key)")
        }
        let app = try XCTUnwrap(object["app"] as? [String: Any])
        for key in EvidenceSchema.requiredAppFields {
            XCTAssertNotNil(app[key], "missing app field: \(key)")
        }
        let windows = try XCTUnwrap(object["windows"] as? [[String: Any]])
        XCTAssertEqual(windows.count, 2)
        XCTAssertEqual(report.workerRuntimeStatus, "NOT RUN IN WORKER")
        XCTAssertTrue(report.evidenceStatus.contains("NO RECEIVER EVIDENCE"))
        XCTAssertTrue(report.identity.synthetic)
        XCTAssertEqual(report.identity.spikeID, "004-window-capture-focus")
        XCTAssertFalse(report.limitations.isEmpty)
    }

    func testReportEncodesLifecycleJournalAfterEachStage() throws {
        let entry = LifecycleEntry(
            stage: .createMarkers,
            requestedSummary: "create marker pair",
            capturedAt: "1970-01-01T00:00:00.000Z",
            activationPolicyObserved: "regular",
            isActive: true,
            windowRoles: [.controlWindow, .sharingNoneMarker, .sharingReadOnlyMarker],
            policyMismatches: [],
            missingWindowRoles: [.auxiliaryPanel, .clickThroughPanel]
        )
        let report = TestFixtures.report(lifecycleJournal: [entry])
        XCTAssertEqual(report.lifecycleJournal, [entry])
        let data = try JSONEncoder().encode(report)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let journal = try XCTUnwrap(object["lifecycleJournal"] as? [[String: Any]])
        XCTAssertEqual(journal.count, 1)
        XCTAssertEqual(journal[0]["stage"] as? String, "create-markers")
        XCTAssertEqual(
            (journal[0]["windowRoles"] as? [String]),
            ["control-window", "marker-sharing-none", "marker-sharing-read-only"]
        )
    }

    func testMissingWindowRolesAreNeverSilentlyTreatedAsPresent() {
        let report = TestFixtures.report(windows: [TestFixtures.readback()])
        XCTAssertTrue(report.missingWindowRoles.contains(.controlWindow))
        XCTAssertTrue(report.missingWindowRoles.contains(.sharingReadOnlyMarker))
        XCTAssertTrue(report.missingWindowRoles.contains(.auxiliaryPanel))
        XCTAssertTrue(report.missingWindowRoles.contains(.clickThroughPanel))
        XCTAssertFalse(report.missingWindowRoles.contains(.sharingNoneMarker))
    }

    func testFullWindowSetHasNoMissingRoles() {
        let windows = FixtureWindowRole.readbackOrder.map { role in
            TestFixtures.readback(
                role: role,
                sharingRequested: role.expectedSharing,
                sharingObservedRaw: role.expectedSharing.appKitRawValue,
                styleMaskRaw: FixturePolicies.controlWindow(title: "Fixture").styleMaskRaw,
                levelRaw: WindowOptionNames.normalLevelRaw,
                becomesKeyOnlyIfNeeded: false,
                isFloatingPanel: false,
                collectionBehaviorRaw: 0
            )
        }
        let report = TestFixtures.report(windows: windows)
        XCTAssertEqual(report.missingWindowRoles, [])
    }

    func testWindowReferenceModelsAbsenceInsteadOfNullWindowRole() {
        let absent = WindowReference.absent
        XCTAssertFalse(absent.present)
        XCTAssertNil(absent.role)
        let present = WindowReference(present: true, role: .controlWindow, title: "Fixture")
        XCTAssertTrue(present.present)
        XCTAssertEqual(present.role, .controlWindow)
    }

    func testSchemaListsIncludeManualEvidenceAndNoPassClaim() {
        XCTAssertTrue(EvidenceSchema.requiredManualFields.contains("browser_name_version"))
        XCTAssertTrue(EvidenceSchema.requiredManualFields.contains("receiver_frames_decoded"))
        XCTAssertTrue(EvidenceSchema.requiredManualFields.contains("positive_control"))
        XCTAssertTrue(EvidenceSchema.requiredManualFields.contains("focus_event_log"))
        XCTAssertFalse(RuntimeCellStatus.allCases.contains { $0.rawValue.contains("PASS") })
    }
}
