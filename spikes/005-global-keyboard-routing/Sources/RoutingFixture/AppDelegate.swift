import AppKit
import RoutingAdapter
import RoutingCore

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private var panel: NSPanel!
    private var pidField: NSTextField!
    private var modePopup: NSPopUpButton!
    private var preflightLabel: NSTextField!
    private var statusLabel: NSTextField!
    private var textReadout: NSTextField!
    private var countersLabel: NSTextField!
    private var armButton: NSButton!
    private var stopButton: NSButton!
    private var adapter: TapAdapter?
    private let terminationGate = TerminationGate()
    private var terminationFallbackScheduled = false
    private var lastPhase: Phase = .off

    func applicationDidFinishLaunching(_ notification: Notification) {
        // STARTUP-BEGIN
        buildPanel()
        preflightLabel.stringValue = NativeChecks.preflightSummary()
        applyPhase(Phase.off, reason: "Capture is OFF. Runtime has not been authorized.")
        panel.orderFrontRegardless()
        // STARTUP-END
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        let needsTeardownWait = adapter.map { !$0.teardownIsComplete } ?? false
        let request = terminationGate.request(needsTeardownWait: needsTeardownWait) { [weak self] in
            self?.adapter?.stop()
        }
        guard request == .waitForTeardown else {
            return .terminateNow
        }
        scheduleTerminationFallback()
        return .terminateLater
    }

    private func scheduleTerminationFallback() {
        guard !terminationFallbackScheduled else { return }
        terminationFallbackScheduled = true
        // The engine's drain is bounded at 1.5 s and the adapter ticks at 10 Hz.
        // This fallback prevents an indefinite termination wait if teardown itself
        // is stuck; process exit still removes the OS tap.
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) { [weak self] in
            guard let self else { return }
            if self.terminationGate.forceAfterDeadline() {
                NSApp.reply(toApplicationShouldTerminate: true)
            }
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        adapter?.stop()
    }

    func windowWillClose(_ notification: Notification) {
        adapter?.stop()
    }

    private func adapterTeardownDidComplete() {
        adapter = nil
        if lastPhase == .off || lastPhase == .closed {
            armButton.isEnabled = true
        }
        if terminationGate.teardownCompleted() {
            NSApp.reply(toApplicationShouldTerminate: true)
        }
    }

    private func buildPanel() {
        let panel = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: 540, height: 460),
            styleMask: [.titled, .closable, .nonactivatingPanel, .utilityWindow],
            backing: .buffered,
            defer: false
        )
        panel.title = "Escalier Spike 005 — Synthetic Routing"
        panel.isFloatingPanel = true
        panel.becomesKeyOnlyIfNeeded = true
        panel.hidesOnDeactivate = false
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isReleasedWhenClosed = false
        panel.delegate = self

        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 10
        stack.translatesAutoresizingMaskIntoConstraints = false

        let title = NSTextField(labelWithString: "Synthetic global-routing fixture")
        title.font = NSFont.boldSystemFont(ofSize: 15)
        stack.addArrangedSubview(title)

        let instructions = NSTextField(
            wrappingLabelWithString: "Capture is OFF at launch. Configure while OFF. Arming creates an event tap only after the explicit button action and prompt-free checks. This panel is non-activating; the allowed foreground PID must stay the browser fixture."
        )
        instructions.maximumNumberOfLines = 0
        stack.addArrangedSubview(instructions)

        preflightLabel = NSTextField(wrappingLabelWithString: "")
        preflightLabel.maximumNumberOfLines = 0
        preflightLabel.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        stack.addArrangedSubview(preflightLabel)

        let controls = NSStackView()
        controls.orientation = .horizontal
        controls.spacing = 8

        let refresh = NSButton(title: "Refresh checks", target: self, action: #selector(refreshPressed))
        controls.addArrangedSubview(refresh)

        pidField = NSTextField(string: "")
        pidField.placeholderString = "allowed PID"
        pidField.alignment = .right
        pidField.widthAnchor.constraint(equalToConstant: 90).isActive = true
        controls.addArrangedSubview(pidField)

        modePopup = NSPopUpButton(frame: .zero, pullsDown: false)
        modePopup.addItems(withTitles: ["Shortcut action", "Text capture"])
        modePopup.selectItem(at: 0)
        controls.addArrangedSubview(modePopup)

        armButton = NSButton(title: "Arm", target: self, action: #selector(armPressed))
        controls.addArrangedSubview(armButton)

        stopButton = NSButton(title: "Stop", target: self, action: #selector(stopPressed))
        controls.addArrangedSubview(stopButton)
        stack.addArrangedSubview(controls)

        let mapping = NSTextField(
            wrappingLabelWithString: "Registered: cmd+shift+K → fixture-action · Escape while armed = emergency stop · absolute session limit 30 s · drain after stop ≤ 1.5 s"
        )
        mapping.maximumNumberOfLines = 0
        stack.addArrangedSubview(mapping)

        statusLabel = NSTextField(wrappingLabelWithString: "")
        statusLabel.maximumNumberOfLines = 0
        statusLabel.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        stack.addArrangedSubview(statusLabel)

        let readoutTitle = NSTextField(labelWithString: "Escalier-owned in-memory text (cleared on stop):")
        stack.addArrangedSubview(readoutTitle)

        textReadout = NSTextField(labelWithString: "")
        textReadout.isEditable = false
        textReadout.isSelectable = true
        textReadout.isBezeled = true
        textReadout.drawsBackground = true
        textReadout.lineBreakMode = .byTruncatingTail
        textReadout.widthAnchor.constraint(equalTo: stack.widthAnchor).isActive = true
        stack.addArrangedSubview(textReadout)

        countersLabel = NSTextField(wrappingLabelWithString: "")
        countersLabel.maximumNumberOfLines = 0
        countersLabel.font = NSFont.monospacedSystemFont(ofSize: 10, weight: .regular)
        stack.addArrangedSubview(countersLabel)

        let note = NSTextField(
            wrappingLabelWithString: "Stop paths: Stop button (may change foreground and disarm), Escape while armed, and the 30 s absolute limit. No permission prompt, no auto-re-enable, no event injection, no persistence. Runtime no-bubble behavior is NOT RUN until separate live human approval."
        )
        note.maximumNumberOfLines = 0
        note.font = NSFont.systemFont(ofSize: 10)
        stack.addArrangedSubview(note)

        let content = NSView()
        panel.contentView = content
        content.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: content.leadingAnchor, constant: 16),
            stack.trailingAnchor.constraint(equalTo: content.trailingAnchor, constant: -16),
            stack.topAnchor.constraint(equalTo: content.topAnchor, constant: 16),
            stack.bottomAnchor.constraint(lessThanOrEqualTo: content.bottomAnchor, constant: -16)
        ])

        panel.center()
        self.panel = panel
    }

    @objc private func refreshPressed() {
        preflightLabel.stringValue = NativeChecks.preflightSummary()
    }

    @objc private func armPressed() {
        let trimmed = pidField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let pid = Int32(trimmed), pid > 0 else {
            statusLabel.stringValue = "Enter a positive allowed foreground PID while capture is OFF."
            return
        }
        guard adapter == nil else { return }

        let mode: ArmMode = modePopup.indexOfSelectedItem == 1 ? .text : .shortcut
        let adapter = TapAdapter()
        adapter.onStatus = { [weak self] snapshot in
            self?.apply(snapshot)
        }
        adapter.onTeardownComplete = { [weak self] in
            self?.adapterTeardownDidComplete()
        }
        self.adapter = adapter
        statusLabel.stringValue = "Installing tap after prompt-free checks; settling 250 ms…"
        adapter.start(allowedPID: pid, mode: mode, bindings: [.fixtureDefault])
    }

    @objc private func stopPressed() {
        adapter?.stop()
        statusLabel.stringValue = "Stop requested. Existing owned key-ups drain for at most 1.5 s."
    }

    private func apply(_ snapshot: StatusSnapshot) {
        let modeText = snapshot.mode?.rawValue ?? "—"
        var details: [String] = [
            "phase=\(snapshot.phase.rawValue)",
            "mode=\(modeText)",
            "remaining=\(String(format: "%.2f", snapshot.remainingSessionSeconds))s",
            "actions=\(snapshot.actionCount)"
        ]
        if let unavailable = snapshot.unavailableReason {
            details.append("unavailable=\(unavailable.rawValue)")
        }
        if let stop = snapshot.stopReason {
            details.append("stop=\(stop.rawValue)")
        }
        if let invalid = snapshot.invalidReason {
            details.append("INVALID=\(invalid.rawValue)")
        }
        statusLabel.stringValue = details.joined(separator: " · ")

        textReadout.stringValue = snapshot.text.isEmpty ? "(empty)" : snapshot.text

        let counters = snapshot.counters
        countersLabel.stringValue = [
            "passed=\(counters.passed)",
            "consumed=\(counters.consumed)",
            "selectedDown=\(counters.selectedKeyDowns)",
            "selectedUp=\(counters.selectedKeyUps)",
            "modifier=\(counters.modifierEvents)",
            "text=\(counters.textEvents)",
            "extract=\(counters.unicodeExtractions)",
            "repeat=\(counters.repeatsConsumed)",
            "drainUp=\(counters.drainOwnedKeyUps)",
            "callbackMaxNs=\(counters.maxCallbackNanoseconds)",
            "budgetViolations=\(counters.callbackBudgetViolations)"
        ].joined(separator: " · ")

        applyPhase(snapshot.phase, reason: nil)
    }

    private func applyPhase(_ phase: Phase, reason: String?) {
        let active = phase == .installing || phase == .settling || phase == .armed || phase == .draining
        lastPhase = phase
        armButton.isEnabled = !active && adapter == nil
        stopButton.isEnabled = active
        if let reason {
            statusLabel.stringValue = "phase=\(phase.rawValue) · \(reason)"
            textReadout.stringValue = "(empty)"
        }
    }
}
