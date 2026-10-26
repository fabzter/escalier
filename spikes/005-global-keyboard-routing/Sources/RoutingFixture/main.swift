import AppKit

@main
enum FixtureMain {
    // NSApplication keeps only a weak delegate reference; hold it for the process lifetime.
    static var delegate: AppDelegate?

    static func main() {
        let application = NSApplication.shared
        let appDelegate = AppDelegate()
        FixtureMain.delegate = appDelegate
        application.delegate = appDelegate
        application.setActivationPolicy(.accessory)
        application.run()
    }
}
