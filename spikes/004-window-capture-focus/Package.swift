// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "EscalierCaptureFixture",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "CapturePolicy", targets: ["CapturePolicy"]),
        .executable(name: "EscalierCaptureFixture", targets: ["EscalierCaptureFixture"])
    ],
    targets: [
        .target(name: "CapturePolicy"),
        .executableTarget(
            name: "EscalierCaptureFixture",
            dependencies: ["CapturePolicy"]
        ),
        .testTarget(
            name: "CapturePolicyTests",
            dependencies: ["CapturePolicy"]
        )
    ]
)
