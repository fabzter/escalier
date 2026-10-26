import AppKit
import CapturePolicy

@MainActor
final class FixtureController: NSObject, NSWindowDelegate {
    private let controlWindow: NSWindow
    private let readbackTextView: NSTextView
    private let statusLabel: NSTextField
    private let auxiliaryModeLabel: NSTextField
    private let clickThroughModeLabel: NSTextField
    private let markerLegendLabel: NSTextField
    private let underlayField: NSTextField

    private var controlPolicy: FixtureWindowPolicy
    private var markerPair: MarkerPair?
    private var markerWindows: [FixtureWindowRole: NSPanel] = [:]
    private var auxiliaryPanel: NSPanel?
    private var clickThroughPanel: NSPanel?
    private var clickThroughView: ClickThroughPanelView?
    private var auxiliaryNonactivating = true
    private var clickThroughMode: ClickThroughMode = .intercept
    private var counters = ClickThroughCounters()
    private var activationPolicyRequested: NSApplication.ActivationPolicy = .regular
    private var titlePresetIndex = 0
    private var eventJournal: [String] = []
    private var lifecycleRecorder = LifecycleRecorder()

    override init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 780, height: 860),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = FixturePolicies.defaultControlTitle
        window.sharingType = NSWindow.SharingType.readOnly
        window.isReleasedWhenClosed = false

        let textView = NSTextView(frame: NSRect(x: 0, y: 0, width: 720, height: 280))
        textView.isEditable = false
        textView.isSelectable = true
        textView.drawsBackground = true
        textView.backgroundColor = .textBackgroundColor
        textView.textColor = .textColor
        textView.font = .monospacedSystemFont(ofSize: 11, weight: .regular)
        textView.isVerticallyResizable = true
        textView.isHorizontallyResizable = false
        textView.autoresizingMask = [.width]
        textView.textContainer?.widthTracksTextView = true

        self.controlWindow = window
        self.readbackTextView = textView
        self.statusLabel = NSTextField(wrappingLabelWithString: "Initializing…")
        self.auxiliaryModeLabel = NSTextField(labelWithString: "")
        self.clickThroughModeLabel = NSTextField(labelWithString: "")
        self.markerLegendLabel = NSTextField(
            wrappingLabelWithString: "Marker pair is visually identical by design. Use readback frame origins to identify sharing-none (treatment) and sharing-readOnly (control); never infer identity from the rendered marker content."
        )
        self.underlayField = NSTextField(string: "0")
        self.controlPolicy = FixturePolicies.controlWindow()

        super.init()
        controlWindow.delegate = self
        buildControlContent()
        updateModeLabels()
        finish(stage: nil, summary: "fixture initialized")
    }

    func showControlWindow() {
        controlWindow.center()
        controlWindow.makeKeyAndOrderFront(nil)
        NSApp.activate()
        finish(stage: nil, summary: "control window shown")
    }

    func windowWillClose(_ notification: Notification) {
        guard let window = notification.object as? NSWindow else { return }
        if window === controlWindow {
            NSApp.terminate(nil)
        }
    }

    private func buildControlContent() {
        guard let contentView = controlWindow.contentView else { return }

        let root = NSStackView()
        root.orientation = .vertical
        root.alignment = .leading
        root.spacing = 7
        root.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(root)

        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 16),
            root.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -16),
            root.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 14),
            root.bottomAnchor.constraint(lessThanOrEqualTo: contentView.bottomAnchor, constant: -14)
        ])

        let banner = NSTextField(
            wrappingLabelWithString: "SYNTHETIC LOCAL FIXTURE — NOT A STEALTH CLAIM — RUNTIME NOT RUN IN WORKER"
        )
        banner.font = .boldSystemFont(ofSize: 12)
        banner.textColor = .systemOrange
        banner.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        root.addArrangedSubview(banner)

        markerLegendLabel.textColor = .secondaryLabelColor
        markerLegendLabel.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        root.addArrangedSubview(markerLegendLabel)

        root.addArrangedSubview(
            makeRow([
                makeButton("Create marker pair", action: #selector(createMarkerPair)),
                makeButton("Show markers", action: #selector(showMarkers)),
                makeButton("Hide markers", action: #selector(hideMarkers)),
                makeButton("Reshow markers", action: #selector(reshowMarkers))
            ])
        )

        root.addArrangedSubview(
            makeRow([
                makeButton("Show/hide auxiliary panel", action: #selector(toggleAuxiliaryPanel)),
                makeButton(
                    "Toggle auxiliary nonactivating",
                    action: #selector(toggleAuxiliaryNonactivating)
                )
            ])
        )

        root.addArrangedSubview(
            makeRow([
                makeButton("Show/hide click-through panel", action: #selector(toggleClickThroughPanel)),
                makeButton("Toggle click-through mode", action: #selector(toggleClickThroughMode)),
                makeButton("Panel hit (inert)", action: #selector(recordPanelHit))
            ])
        )

        root.addArrangedSubview(
            makeRow([
                makeButton("Activate fixture", action: #selector(activateFixture)),
                makeButton("Deactivate fixture", action: #selector(deactivateFixture)),
                makeButton("Activation policy: accessory", action: #selector(switchToAccessory)),
                makeButton("Activation policy: regular", action: #selector(switchToRegular))
            ])
        )

        root.addArrangedSubview(
            makeRow([
                makeButton("Cycle neutral title", action: #selector(cycleTitle)),
                makeButton("Read back now", action: #selector(readBackNow)),
                makeButton("Quit", action: #selector(quitFixture))
            ])
        )

        underlayField.alignment = .right
        underlayField.widthAnchor.constraint(equalToConstant: 80).isActive = true
        root.addArrangedSubview(
            makeRow([
                NSTextField(labelWithString: "Browser underlay clicks (manual):"),
                underlayField,
                makeButton(
                    "Record manual underlay count",
                    action: #selector(recordUnderlayCount)
                )
            ])
        )

        auxiliaryModeLabel.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        root.addArrangedSubview(auxiliaryModeLabel)
        clickThroughModeLabel.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        root.addArrangedSubview(clickThroughModeLabel)

        statusLabel.textColor = .secondaryLabelColor
        statusLabel.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        root.addArrangedSubview(statusLabel)

        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.autohidesScrollers = true
        scroll.borderType = .bezelBorder
        scroll.documentView = readbackTextView
        scroll.translatesAutoresizingMaskIntoConstraints = false
        scroll.heightAnchor.constraint(equalToConstant: 280).isActive = true
        scroll.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        root.addArrangedSubview(scroll)

        let footer = NSTextField(
            wrappingLabelWithString: "Readback JSON is printed to stdout and displayed here only. Window flags are not receiver-pixel evidence. The app does not start capture, use global input hooks, request TCC permissions or write files."
        )
        footer.textColor = .secondaryLabelColor
        footer.widthAnchor.constraint(equalTo: root.widthAnchor).isActive = true
        root.addArrangedSubview(footer)
    }

    private func makeRow(_ views: [NSView]) -> NSStackView {
        let row = NSStackView(views: views)
        row.orientation = .horizontal
        row.alignment = .centerY
        row.spacing = 8
        return row
    }

    private func makeButton(_ title: String, action: Selector) -> NSButton {
        NSButton(title: title, target: self, action: action)
    }

    @objc private func createMarkerPair() {
        if markerPair != nil {
            finish(stage: .createMarkers, summary: "marker pair already created; no duplicate windows")
            return
        }
        let visibleFrame = NSScreen.main?.visibleFrame
            ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let pair = MarkerPair.layout(visibleFrame: visibleFrame)
        markerPair = pair
        for spec in [pair.treatment, pair.control] {
            let panel = makeMarkerPanel(spec: spec)
            markerWindows[spec.role] = panel
        }
        finish(
            stage: .createMarkers,
            summary: "created marker pair treatment=\(Int(pair.treatment.frame.x)),\(Int(pair.treatment.frame.y)) control=\(Int(pair.control.frame.x)),\(Int(pair.control.frame.y))"
        )
    }

    private func makeMarkerPanel(spec: MarkerSpec) -> NSPanel {
        let panel = NSPanel(
            contentRect: spec.frame.cgRect,
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.title = spec.visual.title
        panel.sharingType = spec.sharing == .sharingNone
            ? NSWindow.SharingType.none
            : NSWindow.SharingType.readOnly
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isFloatingPanel = true
        panel.becomesKeyOnlyIfNeeded = true
        panel.hidesOnDeactivate = false
        panel.ignoresMouseEvents = false
        panel.isMovableByWindowBackground = true
        panel.alphaValue = 1
        panel.isOpaque = true
        panel.hasShadow = false
        panel.isReleasedWhenClosed = false
        panel.contentView = MarkerPanelView(
            frame: NSRect(origin: .zero, size: spec.frame.cgRect.size),
            visual: spec.visual
        )
        return panel
    }

    @objc private func showMarkers() {
        if markerPair == nil {
            createMarkerPair()
        }
        for role in [FixtureWindowRole.sharingNoneMarker, .sharingReadOnlyMarker] {
            markerWindows[role]?.orderFrontRegardless()
        }
        finish(stage: .showMarkers, summary: "orderFrontRegardless on both marker panels")
    }

    @objc private func hideMarkers() {
        for panel in markerWindows.values {
            panel.orderOut(nil)
        }
        finish(stage: .hideMarkers, summary: "orderOut on both marker panels")
    }

    @objc private func reshowMarkers() {
        for panel in markerWindows.values {
            panel.orderFrontRegardless()
        }
        finish(stage: .reshowMarkers, summary: "reshow both marker panels without changing policy")
    }

    @objc private func toggleAuxiliaryPanel() {
        if auxiliaryPanel == nil {
            createAuxiliaryPanel()
            finish(stage: nil, summary: "auxiliary panel created and shown")
            return
        }
        guard let panel = auxiliaryPanel else {
            finish(stage: nil, summary: "auxiliary panel unavailable")
            return
        }
        if panel.isVisible {
            panel.orderOut(nil)
            finish(stage: nil, summary: "auxiliary panel hidden")
        } else {
            panel.orderFrontRegardless()
            finish(stage: nil, summary: "auxiliary panel shown")
        }
    }

    private func createAuxiliaryPanel() {
        let visibleFrame = NSScreen.main?.visibleFrame
            ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let size = NSSize(width: 320, height: 180)
        let frame = NSRect(
            x: visibleFrame.minX + 40,
            y: visibleFrame.minY + 80,
            width: size.width,
            height: size.height
        )
        var style: NSWindow.StyleMask = [.titled]
        if auxiliaryNonactivating {
            style.insert(.nonactivatingPanel)
        }
        let panel = NSPanel(
            contentRect: frame,
            styleMask: style,
            backing: .buffered,
            defer: false
        )
        panel.title = FixturePolicies.auxiliaryTitle
        panel.sharingType = NSWindow.SharingType.none
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isFloatingPanel = true
        panel.becomesKeyOnlyIfNeeded = true
        panel.hidesOnDeactivate = false
        panel.ignoresMouseEvents = false
        panel.isMovableByWindowBackground = true
        panel.alphaValue = 1
        panel.isOpaque = true
        panel.hasShadow = true
        panel.isReleasedWhenClosed = false
        panel.contentView = MarkerPanelView(
            frame: NSRect(origin: .zero, size: size),
            visual: auxiliaryVisual()
        )
        auxiliaryPanel = panel
        panel.orderFrontRegardless()
    }

    private func auxiliaryVisual() -> MarkerVisualFingerprint {
        MarkerVisualFingerprint(
            headline: "ESCALIER SYNTHETIC AUXILIARY",
            subheadline: "Separate surface row — not all-surface validation",
            backgroundColorHex: "#0F1C1A",
            roiColorHex: "#FF00AA",
            roiRelativeRect: RectCodable(x: 20, y: 20, width: 80, height: 56),
            windowWidth: 320,
            windowHeight: 180,
            styleMaskRaw: WindowOptionNames.titledStyleMaskRaw
                | (auxiliaryNonactivating
                    ? WindowOptionNames.nonactivatingPanelStyleMaskRaw
                    : 0),
            levelRaw: WindowOptionNames.floatingLevelRaw,
            alpha: 1,
            hasShadow: true,
            isOpaque: true,
            collectionBehaviorRaw: FixturePolicies.markerCollectionBehaviorRaw,
            title: FixturePolicies.auxiliaryTitle
        )
    }

    @objc private func toggleAuxiliaryNonactivating() {
        auxiliaryNonactivating.toggle()
        if let panel = auxiliaryPanel {
            if auxiliaryNonactivating {
                panel.styleMask.insert(.nonactivatingPanel)
            } else {
                panel.styleMask.remove(.nonactivatingPanel)
            }
            panel.orderFrontRegardless()
        }
        finish(
            stage: nil,
            summary: "auxiliary nonactivating=\(auxiliaryNonactivating)"
        )
    }

    @objc private func toggleClickThroughPanel() {
        if clickThroughPanel == nil {
            createClickThroughPanel()
            finish(stage: nil, summary: "click-through panel created and shown")
            return
        }
        guard let panel = clickThroughPanel else {
            finish(stage: nil, summary: "click-through panel unavailable")
            return
        }
        if panel.isVisible {
            panel.orderOut(nil)
            finish(stage: nil, summary: "click-through panel hidden")
        } else {
            panel.orderFrontRegardless()
            finish(stage: nil, summary: "click-through panel shown")
        }
    }

    private func createClickThroughPanel() {
        let visibleFrame = NSScreen.main?.visibleFrame
            ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let size = NSSize(width: 360, height: 170)
        let frame = NSRect(
            x: visibleFrame.midX - size.width / 2,
            y: visibleFrame.minY + 120,
            width: size.width,
            height: size.height
        )
        let panel = NSPanel(
            contentRect: frame,
            styleMask: [.borderless, .nonactivatingPanel],
            backing: .buffered,
            defer: false
        )
        panel.title = FixturePolicies.clickThroughTitle
        panel.sharingType = NSWindow.SharingType.readOnly
        panel.level = .floating
        panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        panel.isFloatingPanel = true
        panel.becomesKeyOnlyIfNeeded = true
        panel.hidesOnDeactivate = false
        panel.ignoresMouseEvents = clickThroughMode.ignoresMouseEvents
        panel.isMovableByWindowBackground = true
        panel.alphaValue = 1
        panel.isOpaque = true
        panel.hasShadow = false
        panel.isReleasedWhenClosed = false

        let view = ClickThroughPanelView(
            frame: NSRect(origin: .zero, size: size)
        )
        view.onHit = { [weak self] in
            self?.incrementPanelHit()
        }
        view.update(panelHits: counters.panelHits, mode: clickThroughMode)
        panel.contentView = view
        clickThroughView = view
        clickThroughPanel = panel
        panel.orderFrontRegardless()
    }

    @objc private func toggleClickThroughMode() {
        clickThroughMode = clickThroughMode == .intercept ? .passThrough : .intercept
        counters.setMode(clickThroughMode)
        clickThroughPanel?.ignoresMouseEvents = clickThroughMode.ignoresMouseEvents
        clickThroughView?.update(panelHits: counters.panelHits, mode: clickThroughMode)
        finish(
            stage: nil,
            summary: "click-through mode=\(clickThroughMode.rawValue) ignoresMouseEvents=\(clickThroughMode.ignoresMouseEvents)"
        )
    }

    @objc private func recordPanelHit() {
        incrementPanelHit()
    }

    private func incrementPanelHit() {
        counters.recordPanelHit()
        clickThroughView?.update(panelHits: counters.panelHits, mode: counters.mode)
        finish(stage: nil, summary: "inert panel hit count=\(counters.panelHits)")
    }

    @objc private func recordUnderlayCount() {
        let raw = underlayField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let value = Int(raw), value >= 0 else {
            logEvent("underlay-count-rejected", "value=\(raw)")
            render(makeReadbackReport())
            return
        }
        do {
            try counters.recordBrowserUnderlayHits(value)
        } catch {
            logEvent("underlay-count-rejected", "negative value=\(value)")
            render(makeReadbackReport())
            return
        }
        clickThroughView?.update(panelHits: counters.panelHits, mode: counters.mode)
        finish(stage: nil, summary: "manual browser underlay count=\(value)")
    }

    @objc private func activateFixture() {
        NSApp.activate()
        controlWindow.makeKeyAndOrderFront(nil)
        finish(stage: .activateFixture, summary: "NSApp.activate + control window key/front")
    }

    @objc private func deactivateFixture() {
        NSApp.deactivate()
        finish(stage: .deactivateFixture, summary: "NSApp.deactivate")
    }

    @objc private func switchToAccessory() {
        activationPolicyRequested = .accessory
        let changed = NSApp.setActivationPolicy(.accessory)
        logEvent("activation-policy-request", "accessory accepted=\(changed)")
        finish(stage: .switchToAccessory, summary: "request accessory activation policy")
    }

    @objc private func switchToRegular() {
        activationPolicyRequested = .regular
        let changed = NSApp.setActivationPolicy(.regular)
        logEvent("activation-policy-request", "regular accepted=\(changed)")
        finish(stage: .switchToRegular, summary: "request regular activation policy")
    }

    @objc private func cycleTitle() {
        titlePresetIndex = (titlePresetIndex + 1) % FixturePolicies.neutralTitlePresets.count
        let title = FixturePolicies.neutralTitlePresets[titlePresetIndex]
        controlWindow.title = title
        controlPolicy = FixturePolicies.controlWindow(title: title)
        finish(stage: nil, summary: "control title preset=\(titlePresetIndex) title=\(title)")
    }

    @objc private func readBackNow() {
        finish(stage: nil, summary: "manual readback")
    }

    @objc private func quitFixture() {
        NSApp.terminate(nil)
    }

    private func finish(stage: LifecycleStage?, summary: String) {
        logEvent(stage?.rawValue ?? "manual-action", summary)
        var report = makeReadbackReport()
        if let stage {
            do {
                try lifecycleRecorder.record(
                    stage: stage,
                    requestedSummary: summary,
                    report: report
                )
                // Rebuild so this action's lifecycle entry is visible in its own
                // printed/displayed readback, not only in the next action's report.
                report = makeReadbackReport()
            } catch {
                logEvent("lifecycle-readback-error", "\(error)")
            }
        }
        render(report)
    }

    private func makeReadbackReport() -> ReadbackReport {
        var requests: [FixtureWindowRole: FixtureWindowPolicy] = [
            .controlWindow: controlPolicy
        ]
        if let pair = markerPair {
            requests[.sharingNoneMarker] = pair.treatment.policy
            requests[.sharingReadOnlyMarker] = pair.control.policy
        }
        if auxiliaryPanel != nil {
            requests[.auxiliaryPanel] = FixturePolicies.auxiliaryPanel(
                nonactivating: auxiliaryNonactivating
            )
        }
        if clickThroughPanel != nil {
            requests[.clickThroughPanel] = FixturePolicies.clickThroughPanel(
                intercept: clickThroughMode == .intercept
            )
        }

        var readbacks: [WindowReadback] = []
        var mismatches: [PolicyMismatch] = []
        for role in FixtureWindowRole.readbackOrder {
            guard let window = window(for: role), let request = requests[role] else {
                continue
            }
            let readback = makeWindowReadback(role: role, window: window, request: request)
            readbacks.append(readback)
            mismatches.append(contentsOf: readback.mismatches(against: request))
        }

        let app = makeAppReadback()
        if let mismatch = app.activationPolicyMismatch() {
            mismatches.append(mismatch)
        }

        return ReadbackReport(
            identity: fixtureIdentity(),
            capturedAt: timestamp(),
            app: app,
            windows: readbacks,
            policyMismatches: mismatches,
            counters: counters,
            eventJournal: eventJournal,
            lifecycleJournal: lifecycleRecorder.entries
        )
    }

    private func makeWindowReadback(
        role: FixtureWindowRole,
        window: NSWindow,
        request: FixtureWindowPolicy
    ) -> WindowReadback {
        let panel = window as? NSPanel
        return WindowReadback(
            role: role,
            title: window.title,
            sharingRequested: request.sharing,
            sharingObservedRaw: window.sharingType.rawValue,
            styleMaskRaw: window.styleMask.rawValue,
            levelRaw: window.level.rawValue,
            alpha: Double(window.alphaValue),
            hasShadow: window.hasShadow,
            isOpaque: window.isOpaque,
            ignoresMouseEvents: window.ignoresMouseEvents,
            ignoresMouseEventsRequested: request.ignoresMouseEvents,
            isVisible: window.isVisible,
            isKeyWindow: window.isKeyWindow,
            isMainWindow: window.isMainWindow,
            canBecomeKey: window.canBecomeKey,
            canBecomeMain: window.canBecomeMain,
            becomesKeyOnlyIfNeeded: panel?.becomesKeyOnlyIfNeeded ?? false,
            isFloatingPanel: panel?.isFloatingPanel ?? false,
            hidesOnDeactivate: window.hidesOnDeactivate,
            isMovableByWindowBackground: window.isMovableByWindowBackground,
            occlusionVisible: window.occlusionState.contains(.visible),
            frame: RectCodable(window.frame),
            collectionBehaviorRaw: window.collectionBehavior.rawValue
        )
    }

    private func makeAppReadback() -> AppReadback {
        let frontmost: FrontmostAppReadback
        if let application = NSWorkspace.shared.frontmostApplication {
            frontmost = FrontmostAppReadback(
                available: true,
                localizedName: application.localizedName,
                bundleIdentifier: application.bundleIdentifier,
                activationPolicy: WindowOptionNames.activationPolicyName(
                    forRaw: Int(application.activationPolicy.rawValue)
                ),
                isFixtureProcess: application.processIdentifier
                    == ProcessInfo.processInfo.processIdentifier
            )
        } else {
            frontmost = .unavailable
        }

        return AppReadback(
            activationPolicyObservedRaw: Int(NSApp.activationPolicy().rawValue),
            activationPolicyRequestedRaw: Int(activationPolicyRequested.rawValue),
            isActive: NSApp.isActive,
            keyWindow: windowReference(NSApp.keyWindow),
            mainWindow: windowReference(NSApp.mainWindow),
            frontmostApplication: frontmost,
            screens: NSScreen.screens.map { screen in
                ScreenReadback(
                    frame: RectCodable(screen.frame),
                    visibleFrame: RectCodable(screen.visibleFrame),
                    backingScaleFactor: Double(screen.backingScaleFactor)
                )
            }
        )
    }

    private func windowReference(_ window: NSWindow?) -> WindowReference {
        guard let window else { return .absent }
        let role = FixtureWindowRole.readbackOrder.first { role in
            self.window(for: role) === window
        }
        return WindowReference(present: true, role: role, title: window.title)
    }

    private func window(for role: FixtureWindowRole) -> NSWindow? {
        switch role {
        case .controlWindow:
            return controlWindow
        case .sharingNoneMarker, .sharingReadOnlyMarker:
            return markerWindows[role]
        case .auxiliaryPanel:
            return auxiliaryPanel
        case .clickThroughPanel:
            return clickThroughPanel
        }
    }

    private func fixtureIdentity() -> FixtureIdentity {
        let bundle = Bundle.main
        let packageType = bundle.object(forInfoDictionaryKey: "CFBundlePackageType") as? String
        let buildKind: FixtureBuildKind = packageType == "APPL"
            ? .appBundle
            : .unbundledExecutable
        let appName = bundle.object(forInfoDictionaryKey: "CFBundleName") as? String
            ?? ProcessInfo.processInfo.processName
        return FixtureIdentity(
            appName: appName,
            buildKind: buildKind,
            bundleIdentifier: bundle.bundleIdentifier
        )
    }

    private func render(_ report: ReadbackReport) {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        if let data = try? encoder.encode(report),
           let text = String(data: data, encoding: .utf8) {
            readbackTextView.string = text
            print(text)
        }

        let missing = report.missingWindowRoles.map(\.rawValue).joined(separator: ",")
        let missingLifecycle = lifecycleRecorder
            .missingReadbacks(for: LifecycleStep.standard())
            .map(\.rawValue)
            .joined(separator: ",")
        statusLabel.stringValue = [
            "activation=\(report.app.activationPolicyObserved)",
            "active=\(report.app.isActive)",
            "windows=\(report.windows.count)/5",
            "missing=\(missing.isEmpty ? "none" : missing)",
            "mismatches=\(report.policyMismatches.count)",
            "lifecycle=\(lifecycleRecorder.entries.count)/8",
            "lifecycleMissing=\(missingLifecycle.isEmpty ? "none" : missingLifecycle)"
        ].joined(separator: "  ")
        updateModeLabels()
        clickThroughView?.update(panelHits: counters.panelHits, mode: counters.mode)
    }

    private func updateModeLabels() {
        auxiliaryModeLabel.stringValue = auxiliaryNonactivating
            ? "Auxiliary: nonactivating ON (separate surface row)"
            : "Auxiliary: nonactivating OFF (normal panel state)"
        clickThroughModeLabel.stringValue =
            "Click-through: \(clickThroughMode.rawValue), ignoresMouseEvents=\(clickThroughMode.ignoresMouseEvents)"
    }

    private func logEvent(_ name: String, _ detail: String) {
        eventJournal.append("\(timestamp()) \(name) — \(detail)")
        if eventJournal.count > 200 {
            eventJournal.removeFirst(eventJournal.count - 200)
        }
    }

    private func timestamp() -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: Date())
    }
}
