import AppKit
import SwiftUI
import EscalierCore

/// Minimal AppKit coordinator: one native window hosting SwiftUI content plus an
/// in-application menu. All shortcuts are menu equivalents local to this app.
/// No global monitor, event tap, permission request or capture API is used here.
final class AppDelegate: NSObject, NSApplicationDelegate {
    private let store = SampleContent.demoStore()
    private var window: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMainMenu()
        showMainWindow()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        true
    }

    func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
        true
    }

    private func showMainWindow() {
        let rootView = RootView(store: store)
        let hostingController = NSHostingController(rootView: rootView)
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1240, height: 840),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Escalier — synthetic native shell spike"
        window.contentViewController = hostingController
        window.minSize = NSSize(width: 1100, height: 700)
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        self.window = window
    }

    private func buildMainMenu() {
        let mainMenu = NSMenu()

        let applicationMenuItem = NSMenuItem()
        mainMenu.addItem(applicationMenuItem)
        let applicationMenu = NSMenu()
        applicationMenuItem.submenu = applicationMenu
        applicationMenu.addItem(
            withTitle: "About Escalier Shell Spike",
            action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)),
            keyEquivalent: ""
        )
        applicationMenu.addItem(.separator())
        applicationMenu.addItem(
            withTitle: "Quit Escalier Shell Spike",
            action: #selector(NSApplication.terminate(_:)),
            keyEquivalent: "q"
        )

        let conversationMenuItem = NSMenuItem()
        mainMenu.addItem(conversationMenuItem)
        let conversationMenu = NSMenu(title: "Conversation")
        conversationMenuItem.submenu = conversationMenu
        let startItem = NSMenuItem(
            title: "Start live conversation (synthetic)",
            action: #selector(startConversation(_:)),
            keyEquivalent: ""
        )
        startItem.target = self
        conversationMenu.addItem(startItem)

        let referenceMenuItem = NSMenuItem()
        mainMenu.addItem(referenceMenuItem)
        let referenceMenu = NSMenu(title: "Reference")
        referenceMenuItem.submenu = referenceMenu
        addMenuItem(
            to: referenceMenu,
            title: "Previous synthetic reference",
            action: #selector(selectPreviousReference(_:)),
            keyEquivalent: "["
        )
        addMenuItem(
            to: referenceMenu,
            title: "Next synthetic reference",
            action: #selector(selectNextReference(_:)),
            keyEquivalent: "]"
        )

        let assistanceMenuItem = NSMenuItem()
        mainMenu.addItem(assistanceMenuItem)
        let assistanceMenu = NSMenu(title: "Assistance (synthetic routes)")
        assistanceMenuItem.submenu = assistanceMenu
        for action in AssistanceAction.allCases {
            let item = NSMenuItem(
                title: action.label,
                action: #selector(performAssistanceAction(_:)),
                keyEquivalent: action.keyEquivalent
            )
            item.keyEquivalentModifierMask = [.command]
            item.target = self
            item.representedObject = action.rawValue
            assistanceMenu.addItem(item)
        }
        assistanceMenu.addItem(.separator())
        let noteItem = NSMenuItem(
            title: "Routes are MOCK; no assistance, OMP, capture or network is connected",
            action: nil,
            keyEquivalent: ""
        )
        noteItem.isEnabled = false
        assistanceMenu.addItem(noteItem)

        let editMenuItem = NSMenuItem()
        mainMenu.addItem(editMenuItem)
        let editMenu = NSMenu(title: "Edit")
        editMenuItem.submenu = editMenu
        editMenu.addItem(
            withTitle: "Cut",
            action: #selector(NSText.cut(_:)),
            keyEquivalent: "x"
        )
        editMenu.addItem(
            withTitle: "Copy",
            action: #selector(NSText.copy(_:)),
            keyEquivalent: "c"
        )
        editMenu.addItem(
            withTitle: "Paste",
            action: #selector(NSText.paste(_:)),
            keyEquivalent: "v"
        )
        editMenu.addItem(
            withTitle: "Select All",
            action: #selector(NSText.selectAll(_:)),
            keyEquivalent: "a"
        )

        NSApp.mainMenu = mainMenu
    }

    private func addMenuItem(
        to menu: NSMenu,
        title: String,
        action: Selector,
        keyEquivalent: String
    ) {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: keyEquivalent)
        item.keyEquivalentModifierMask = [.command]
        item.target = self
        menu.addItem(item)
    }

    @objc private func performAssistanceAction(_ sender: NSMenuItem) {
        guard let rawValue = sender.representedObject as? String,
              let action = AssistanceAction(rawValue: rawValue)
        else {
            return
        }
        _ = store.dispatchAssistanceAction(action)
    }

    @objc private func startConversation(_ sender: Any?) {
        _ = store.startConversation()
    }

    @objc private func selectPreviousReference(_ sender: Any?) {
        _ = store.selectPreviousReference()
    }

    @objc private func selectNextReference(_ sender: Any?) {
        _ = store.selectNextReference()
    }
}
