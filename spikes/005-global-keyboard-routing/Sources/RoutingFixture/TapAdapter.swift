import AppKit
import CoreFoundation
import CoreGraphics
import Foundation
import RoutingAdapter
import RoutingCore

/// Minimal native adapter around one active session-level event tap.
///
/// All callback decisions, timers and teardown run on one owned run loop. The tap is
/// created only after an explicit arm call. The shared `AdapterCoordinator` owns the
/// decision/delivery/teardown wiring and is exercised headlessly through its fake seam.
final class TapAdapter: AdapterDependencies, AdapterLifecycleTarget {
    var onStatus: ((StatusSnapshot) -> Void)?
    var onTeardownComplete: (() -> Void)?

    private let controlLock = NSLock()
    private var thread: Thread?
    private var runLoop: CFRunLoop?
    private var stopRequested = false
    private var started = false

    private var mode: ArmMode = .shortcut
    private var coordinator: AdapterCoordinator!

    private var tap: CFMachPort?
    private var source: CFRunLoopSource?
    private var callbackContext: UnsafeMutableRawPointer?
    private var uiTimer: CFRunLoopTimer?
    private var settleTimer: CFRunLoopTimer?
    private var sessionObservers: [NSObjectProtocol] = []

    var teardownIsComplete: Bool {
        coordinator?.teardownIsComplete ?? false
    }

    func start(allowedPID: Int32, mode: ArmMode, bindings: [ShortcutBinding]) {
        controlLock.lock()
        if started {
            controlLock.unlock()
            return
        }
        started = true
        self.mode = mode
        let configuration = RoutingConfiguration(allowedPID: allowedPID, bindings: bindings)
        coordinator = AdapterCoordinator(
            configuration: configuration,
            dependencies: self,
            target: self
        )
        let worker = Thread { [weak self] in
            self?.threadMain()
        }
        worker.name = "EscalierRoutingTap"
        worker.stackSize = 512 * 1024
        thread = worker
        controlLock.unlock()
        worker.start()
    }

    func stop() {
        controlLock.lock()
        let activeRunLoop = runLoop
        if activeRunLoop == nil {
            stopRequested = true
            controlLock.unlock()
            return
        }
        controlLock.unlock()

        CFRunLoopPerformBlock(activeRunLoop, CFRunLoopMode.commonModes.rawValue) { [weak self] in
            self?.requestUserStop()
        }
        CFRunLoopWakeUp(activeRunLoop)
    }

    // MARK: - Owned thread

    private func threadMain() {
        autoreleasepool {
            guard let currentRunLoop = CFRunLoopGetCurrent() else {
                finishThread()
                return
            }

            controlLock.lock()
            runLoop = currentRunLoop
            let earlyStop = stopRequested
            stopRequested = false
            controlLock.unlock()

            if earlyStop {
                completeTeardown()
                finishThread()
                return
            }

            guard installTap(on: currentRunLoop) else {
                completeTeardown()
                finishThread()
                return
            }

            startTimers(on: currentRunLoop)
            coordinator.publishStatus()
            scheduleSettleTick(on: currentRunLoop)
            CFRunLoopRun()

            completeTeardown()
            finishThread()
        }
    }

    private func installTap(on currentRunLoop: CFRunLoop) -> Bool {
        let request = coordinator.beginArm(
            mode: mode,
            gate: NativeChecks.currentGate(),
            heldNonModifierKeys: NativeChecks.heldNonModifierKey()
        )
        guard request == .installTap else {
            return false
        }

        let eventMask: CGEventMask =
            (1 << CGEventType.keyDown.rawValue) |
            (1 << CGEventType.keyUp.rawValue) |
            (1 << CGEventType.flagsChanged.rawValue)

        let context = Unmanaged.passRetained(self).toOpaque()
        guard let createdTap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .defaultTap,
            eventsOfInterest: eventMask,
            callback: escalierTapCallback,
            userInfo: context
        ) else {
            Unmanaged<TapAdapter>.fromOpaque(context).release()
            coordinator.tapInstallationFailed(.tapReturnedNil)
            return false
        }

        guard let createdSource = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, createdTap, 0) else {
            CGEvent.tapEnable(tap: createdTap, enable: false)
            CFMachPortInvalidate(createdTap)
            Unmanaged<TapAdapter>.fromOpaque(context).release()
            coordinator.tapInstallationFailed(.tapInstallationFailed)
            return false
        }

        callbackContext = context
        tap = createdTap
        source = createdSource
        CFRunLoopAddSource(currentRunLoop, createdSource, .commonModes)
        enableTap()

        guard CGEvent.tapIsEnabled(tap: createdTap) else {
            coordinator.tapInstallationFailed(.tapInstallationFailed)
            return false
        }

        coordinator.tapInstalled(at: uptime)
        observeSessionEvents()
        return true
    }

    private func observeSessionEvents() {
        let center = NSWorkspace.shared.notificationCenter
        let events: [(Notification.Name, StopReason)] = [
            (NSWorkspace.willSleepNotification, .systemSleep),
            (NSWorkspace.screensDidSleepNotification, .systemSleep),
            (NSWorkspace.sessionDidResignActiveNotification, .sessionResigned)
        ]
        for (name, reason) in events {
            let token = center.addObserver(forName: name, object: nil, queue: nil) { [weak self] _ in
                self?.enqueueSessionStop(reason: reason)
            }
            sessionObservers.append(token)
        }
    }

    private func enqueueSessionStop(reason: StopReason) {
        controlLock.lock()
        let activeRunLoop = runLoop
        controlLock.unlock()
        guard let activeRunLoop else { return }
        CFRunLoopPerformBlock(activeRunLoop, CFRunLoopMode.commonModes.rawValue) { [weak self] in
            guard let self else { return }
            _ = self.coordinator.requestStop(reason: reason)
            self.coordinator.publishStatus()
        }
        CFRunLoopWakeUp(activeRunLoop)
    }

    private func startTimers(on currentRunLoop: CFRunLoop) {
        let interval = max(coordinator.configuration.uiReadInterval, 0.05)
        let timer = CFRunLoopTimerCreateWithHandler(
            kCFAllocatorDefault,
            CFAbsoluteTimeGetCurrent() + interval,
            interval,
            0,
            0
        ) { [weak self] _ in
            self?.pump()
        }
        if let timer {
            uiTimer = timer
            CFRunLoopAddTimer(currentRunLoop, timer, .commonModes)
        }
    }

    private func scheduleSettleTick(on currentRunLoop: CFRunLoop) {
        let timer = CFRunLoopTimerCreateWithHandler(
            kCFAllocatorDefault,
            CFAbsoluteTimeGetCurrent() + coordinator.configuration.settleInterval,
            0,
            0,
            0
        ) { [weak self] _ in
            self?.pump()
        }
        if let timer {
            settleTimer = timer
            CFRunLoopAddTimer(currentRunLoop, timer, .commonModes)
        }
    }

    private func pump() {
        _ = coordinator.tick()
        coordinator.publishStatus()
    }

    private func requestUserStop() {
        _ = coordinator.requestStop()
        coordinator.publishStatus()
    }

    // MARK: - Adapter seam dependencies

    var uptime: TimeInterval {
        ProcessInfo.processInfo.systemUptime
    }

    func monotonicNanos() -> UInt64 {
        DispatchTime.now().uptimeNanoseconds
    }

    func currentGate() -> GateContext {
        NativeChecks.currentGate()
    }

    func scheduleTeardown(_ action: @escaping () -> Void) {
        controlLock.lock()
        let activeRunLoop = runLoop
        controlLock.unlock()
        guard let activeRunLoop else { return }
        CFRunLoopPerformBlock(activeRunLoop, CFRunLoopMode.commonModes.rawValue) {
            action()
        }
        CFRunLoopWakeUp(activeRunLoop)
    }

    func publish(_ snapshot: StatusSnapshot) {
        DispatchQueue.main.async { [weak self] in
            self?.onStatus?(snapshot)
        }
    }

    // MARK: - Callback hot path

    // CALLBACK-BEGIN
    fileprivate func process(type: CGEventType, event: CGEvent) -> Unmanaged<CGEvent>? {
        let kind: AdapterEvent.Kind
        switch type {
        case .keyDown:
            kind = .keyDown
        case .keyUp:
            kind = .keyUp
        case .flagsChanged:
            kind = .flagsChanged
        case CGEventType.tapDisabledByTimeout:
            kind = .tapDisabledByTimeout
        case CGEventType.tapDisabledByUserInput:
            kind = .tapDisabledByUserInput
        default:
            return Unmanaged.passUnretained(event)
        }

        let adapterEvent = AdapterEvent(
            kind: kind,
            keyCode: UInt16(truncatingIfNeeded: event.getIntegerValueField(.keyboardEventKeycode)),
            rawModifiers: event.flags.rawValue,
            isRepeat: event.getIntegerValueField(.keyboardEventAutorepeat) != 0
        )
        let result = coordinator.process(
            adapterEvent,
            original: event,
            unicode: { self.extractUnicode(from: event) }
        )
        if result.event != nil {
            return Unmanaged.passUnretained(event)
        }
        return nil
    }

    private func extractUnicode(from event: CGEvent) -> String? {
        let maxLength = coordinator.configuration.perEventUTF16Limit
        var buffer = [UniChar](repeating: 0, count: maxLength)
        var length = 0
        buffer.withUnsafeMutableBufferPointer { pointer in
            event.keyboardGetUnicodeString(
                maxStringLength: maxLength,
                actualStringLength: &length,
                unicodeString: pointer.baseAddress
            )
        }
        var usableLength = min(length, maxLength)
        if usableLength > 0 {
            let lastUnit = buffer[usableLength - 1]
            if lastUnit >= 0xD800 && lastUnit <= 0xDBFF {
                // The native extraction cap fell between a surrogate pair; never
                // hand a split scalar to the text buffer.
                usableLength -= 1
            }
        }
        guard usableLength > 0 else { return nil }
        return String(utf16CodeUnits: buffer, count: usableLength)
    }
    // CALLBACK-END

    // MARK: - Adapter lifecycle target

    func enableTap() {
        guard let tap else { return }
        CGEvent.tapEnable(tap: tap, enable: true)
    }

    func disableTap() {
        guard let tap else { return }
        CGEvent.tapEnable(tap: tap, enable: false)
    }

    func invalidateTapAndSource() {
        if let tap {
            CFMachPortInvalidate(tap)
        }
        if let source {
            if let runLoop {
                CFRunLoopRemoveSource(runLoop, source, .commonModes)
            }
            CFRunLoopSourceInvalidate(source)
        }
        tap = nil
        source = nil
    }

    func invalidateTimers() {
        if let uiTimer {
            CFRunLoopTimerInvalidate(uiTimer)
        }
        if let settleTimer {
            CFRunLoopTimerInvalidate(settleTimer)
        }
        uiTimer = nil
        settleTimer = nil
    }

    func removeObservers() {
        let center = NSWorkspace.shared.notificationCenter
        for observer in sessionObservers {
            center.removeObserver(observer)
        }
        sessionObservers.removeAll()
    }

    func releaseCallbackContext() {
        guard let callbackContext else { return }
        self.callbackContext = nil
        Unmanaged<TapAdapter>.fromOpaque(callbackContext).release()
    }

    func stopRunLoop() {
        if let runLoop {
            CFRunLoopStop(runLoop)
        }
    }

    func teardownDidComplete() {
        DispatchQueue.main.async { [weak self] in
            self?.onTeardownComplete?()
        }
    }

    private func completeTeardown() {
        coordinator?.completeTeardown()
    }

    private func finishThread() {
        controlLock.lock()
        runLoop = nil
        thread = nil
        controlLock.unlock()
    }
}

// CALLBACK-BEGIN
private func escalierTapCallback(
    proxy: CGEventTapProxy,
    type: CGEventType,
    event: CGEvent,
    userInfo: UnsafeMutableRawPointer?
) -> Unmanaged<CGEvent>? {
    guard let userInfo else {
        return Unmanaged.passUnretained(event)
    }
    let adapter = Unmanaged<TapAdapter>.fromOpaque(userInfo).takeUnretainedValue()
    return adapter.process(type: type, event: event)
}
// CALLBACK-END
