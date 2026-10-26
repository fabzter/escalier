import AppKit

// AppKit process/window bootstrapping. The content is SwiftUI hosted by the coordinator.
// This executable is built but not launched by the implementation worker.
let application = NSApplication.shared
let coordinator = AppDelegate()
application.delegate = coordinator
application.setActivationPolicy(.regular)
application.run()
