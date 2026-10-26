// swift-tools-version: 5.9
// Dependency-free prototype package. Build products stay in this directory's .build/.
import PackageDescription

let package = Package(
    name: "EscalierShellSpike",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "EscalierCore", targets: ["EscalierCore"]),
        .executable(name: "EscalierShell", targets: ["EscalierShell"])
    ],
    dependencies: [],
    targets: [
        .target(
            name: "EscalierCore",
            path: "Sources/EscalierCore"
        ),
        .executableTarget(
            name: "EscalierShell",
            dependencies: ["EscalierCore"],
            path: "Sources/EscalierShell"
        ),
        .testTarget(
            name: "EscalierCoreTests",
            dependencies: ["EscalierCore"],
            path: "Tests/EscalierCoreTests"
        )
    ]
)
