import Foundation

public enum TerminationRequest: Equatable, Sendable {
    case terminateNow
    case waitForTeardown
}

/// Pure close-path gate: keeps AppKit termination pending until the adapter reports
/// teardown complete, with one explicitly bounded forced fallback.
public final class TerminationGate {
    public private(set) var isWaiting = false
    public private(set) var didForceTermination = false
    private var stopRequested = false

    public init() {}

    public func request(
        needsTeardownWait: Bool,
        requestStop: () -> Void
    ) -> TerminationRequest {
        guard needsTeardownWait else {
            isWaiting = false
            return .terminateNow
        }
        if !stopRequested {
            stopRequested = true
            requestStop()
        }
        isWaiting = true
        return .waitForTeardown
    }

    public func teardownCompleted() -> Bool {
        guard isWaiting else { return false }
        isWaiting = false
        return true
    }

    public func forceAfterDeadline() -> Bool {
        guard isWaiting else { return false }
        isWaiting = false
        didForceTermination = true
        return true
    }
}
