import AppKit
import ApplicationServices
import Carbon.HIToolbox
import CoreGraphics
import RoutingCore

/// Prompt-free readback only. Nothing here requests, prompts for, grants or changes a
/// permission, and nothing here enables or disables secure event input.
enum NativeChecks {
    static func foregroundPID() -> Int32? {
        NSWorkspace.shared.frontmostApplication?.processIdentifier
    }

    static func secureInputEnabled() -> Bool {
        IsSecureEventInputEnabled()
    }

    static func accessibilityTrusted() -> Bool {
        AXIsProcessTrusted()
    }

    static func listenEventAccess() -> Bool {
        CGPreflightListenEventAccess()
    }

    static func currentGate() -> GateContext {
        GateContext(
            foregroundPID: foregroundPID(),
            permissionsAvailable: accessibilityTrusted() && listenEventAccess(),
            secureInputEnabled: secureInputEnabled()
        )
    }

    /// Checks the fixed non-modifier key universe through the current session state.
    /// This is a best-effort arming precondition, not continuous held-key tracking.
    static func heldNonModifierKey() -> Bool {
        var codes = KeyPolicy.printableKeyCodes
        codes.formUnion(KeyPolicy.navigationKeyCodes)
        codes.formUnion([
            KeyPolicy.escapeKeyCode,
            KeyPolicy.backspaceKeyCode,
            KeyPolicy.forwardDeleteKeyCode,
            KeyPolicy.returnKeyCode,
            KeyPolicy.tabKeyCode
        ])

        for code in codes {
            if CGEventSource.keyState(.combinedSessionState, key: CGKeyCode(code)) {
                return true
            }
        }
        return false
    }

    static func preflightSummary() -> String {
        let trusted = accessibilityTrusted() ? "yes" : "no"
        let listen = listenEventAccess() ? "yes" : "no"
        let secure = secureInputEnabled() ? "on" : "off"
        let pid = foregroundPID().map(String.init) ?? "unknown"
        return "Accessibility trusted: \(trusted) · listen access: \(listen) · secure input: \(secure) · frontmost PID: \(pid)"
    }
}
