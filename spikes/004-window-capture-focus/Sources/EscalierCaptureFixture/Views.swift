import AppKit
import CapturePolicy

@MainActor
final class MarkerPanelView: NSView {
    private let visual: MarkerVisualFingerprint

    init(frame: NSRect, visual: MarkerVisualFingerprint) {
        self.visual = visual
        super.init(frame: frame)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) is not used by this programmatic fixture")
    }

    override var isOpaque: Bool {
        true
    }

    override func draw(_ dirtyRect: NSRect) {
        HexColor.color(visual.backgroundColorHex).setFill()
        bounds.fill()

        let roi = visual.roiRelativeRect.cgRect
        HexColor.color(visual.roiColorHex).setFill()
        roi.fill()

        NSColor.white.setStroke()
        let outline = NSBezierPath(rect: roi.insetBy(dx: 1, dy: 1))
        outline.lineWidth = 2
        outline.stroke()

        let headlineAttributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.boldSystemFont(ofSize: 18),
            .foregroundColor: NSColor.white
        ]
        let subheadlineAttributes: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 12),
            .foregroundColor: NSColor(calibratedWhite: 0.82, alpha: 1)
        ]

        NSString(string: visual.headline).draw(
            at: NSPoint(x: 24, y: bounds.height - 46),
            withAttributes: headlineAttributes
        )
        NSString(string: visual.subheadline).draw(
            in: NSRect(
                x: 24,
                y: bounds.height - 82,
                width: bounds.width - 48,
                height: 30
            ),
            withAttributes: subheadlineAttributes
        )
    }
}

@MainActor
final class ClickThroughPanelView: NSView {
    var onHit: (() -> Void)?

    private let titleLabel = NSTextField(labelWithString: "CLICK-THROUGH TEST PANEL — INERT")
    private let modeLabel = NSTextField(labelWithString: "")
    private let countLabel = NSTextField(labelWithString: "Panel hits: 0")
    private let button = NSButton(title: "Panel hit (inert)", target: nil, action: nil)

    override init(frame: NSRect) {
        super.init(frame: frame)
        titleLabel.font = NSFont.boldSystemFont(ofSize: 13)
        titleLabel.textColor = .white
        modeLabel.font = NSFont.systemFont(ofSize: 11)
        modeLabel.textColor = NSColor(calibratedWhite: 0.82, alpha: 1)
        countLabel.font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        countLabel.textColor = .white
        button.bezelStyle = .rounded
        button.target = self
        button.action = #selector(hitButton)
        addSubview(titleLabel)
        addSubview(modeLabel)
        addSubview(countLabel)
        addSubview(button)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) is not used by this programmatic fixture")
    }

    override var isOpaque: Bool {
        true
    }

    override func draw(_ dirtyRect: NSRect) {
        HexColor.color("#161C24").setFill()
        bounds.fill()
        NSColor(calibratedWhite: 0.35, alpha: 1).setStroke()
        let border = NSBezierPath(rect: bounds.insetBy(dx: 1, dy: 1))
        border.lineWidth = 2
        border.stroke()
    }

    override func layout() {
        super.layout()
        titleLabel.frame = NSRect(x: 14, y: bounds.height - 30, width: bounds.width - 28, height: 18)
        modeLabel.frame = NSRect(x: 14, y: bounds.height - 52, width: bounds.width - 28, height: 16)
        countLabel.frame = NSRect(x: 14, y: 46, width: bounds.width - 28, height: 18)
        button.frame = NSRect(x: 14, y: 12, width: 170, height: 28)
    }

    func update(panelHits: Int, mode: ClickThroughMode) {
        modeLabel.stringValue =
            mode == .passThrough
            ? "pass-through: clicks reach the inert browser underlay"
            : "intercept: clicks stay on this inert panel"
        countLabel.stringValue = "Panel hits: \(panelHits)"
    }

    @objc private func hitButton() {
        onHit?()
    }
}
