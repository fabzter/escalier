import XCTest
import CapturePolicy

final class LifecycleTests: XCTestCase {
    func testStandardLifecycleSequenceMatchesBindingOrder() {
        let steps = LifecycleStep.standard()
        XCTAssertEqual(
            steps.map(\.stage),
            [
                .createMarkers,
                .showMarkers,
                .hideMarkers,
                .reshowMarkers,
                .activateFixture,
                .deactivateFixture,
                .switchToAccessory,
                .switchToRegular
            ]
        )
        XCTAssertTrue(steps.allSatisfy(\.expectsReadback))
    }

    func testLifecycleRecorderRequiresReadbackAfterEveryStage() throws {
        var recorder = LifecycleRecorder()
        let report = TestFixtures.report()
        for step in LifecycleStep.standard().dropLast(2) {
            try recorder.record(stage: step.stage, requestedSummary: "requested-\(step.stage.rawValue)", report: report)
        }
        XCTAssertEqual(
            recorder.missingReadbacks(for: LifecycleStep.standard()),
            [.switchToAccessory, .switchToRegular]
        )
        try recorder.record(stage: .switchToAccessory, requestedSummary: "requested-accessory", report: report)
        try recorder.record(stage: .switchToRegular, requestedSummary: "requested-regular", report: report)
        XCTAssertEqual(recorder.missingReadbacks(for: LifecycleStep.standard()), [])
        XCTAssertEqual(recorder.entries.count, 8)
        XCTAssertTrue(recorder.entries.allSatisfy(\.hasReadback))
    }

    func testEmptyReadbackIsRejected() {
        var recorder = LifecycleRecorder()
        let empty = TestFixtures.report(windows: [])
        XCTAssertThrowsError(
            try recorder.record(stage: .createMarkers, requestedSummary: "create", report: empty)
        ) { error in
            XCTAssertEqual(error as? LifecycleError, .emptyReadback)
        }
        XCTAssertTrue(recorder.entries.isEmpty)
    }

    func testLifecycleEntryCarriesPolicyMismatchesAndMissingRoles() throws {
        var recorder = LifecycleRecorder()
        let mismatch = PolicyMismatch(
            scope: "marker-sharing-none",
            field: "sharing",
            requested: "sharing-none",
            observed: "sharing-readOnly"
        )
        let report = TestFixtures.report(
            windows: [TestFixtures.readback()],
            policyMismatches: [mismatch]
        )
        try recorder.record(stage: .createMarkers, requestedSummary: "create", report: report)
        let entry = try XCTUnwrap(recorder.entries.first)
        XCTAssertEqual(entry.policyMismatches, [mismatch])
        XCTAssertTrue(entry.missingWindowRoles.contains(.controlWindow))
        XCTAssertTrue(entry.hasReadback)
    }

    func testLifecycleBackedReportIncludesRequestedAndObservedActivationState() {
        let report = TestFixtures.report(
            app: TestFixtures.appReadback(
                observedRaw: WindowOptionNames.accessoryActivationRaw,
                requestedRaw: WindowOptionNames.accessoryActivationRaw,
                isActive: false
            )
        )
        XCTAssertEqual(report.app.activationPolicyRequested, "accessory")
        XCTAssertEqual(report.app.activationPolicyObserved, "accessory")
        XCTAssertFalse(report.app.isActive)
        XCTAssertNil(report.app.activationPolicyMismatch())
    }
}
