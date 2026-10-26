// swift-tools-version: 5.9
// Dependency-free synthetic spike package. Build products stay in this directory's .build/.
import PackageDescription

let package = Package(
    name: "EscalierKeyboardRoutingSpike",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .library(name: "RoutingCore", targets: ["RoutingCore"]),
        .library(name: "RoutingAdapter", targets: ["RoutingAdapter"]),
        .executable(name: "RoutingFixture", targets: ["RoutingFixture"])
    ],
    dependencies: [],
    targets: [
        .target(
            name: "RoutingCore",
            path: "Sources/RoutingCore"
        ),
        .target(
            name: "RoutingAdapter",
            dependencies: ["RoutingCore"],
            path: "Sources/RoutingAdapter"
        ),
        .executableTarget(
            name: "RoutingFixture",
            dependencies: ["RoutingCore", "RoutingAdapter"],
            path: "Sources/RoutingFixture"
        ),
        .testTarget(
            name: "RoutingCoreTests",
            dependencies: ["RoutingCore"],
            path: "Tests/RoutingCoreTests"
        ),
        .testTarget(
            name: "RoutingAdapterTests",
            dependencies: ["RoutingAdapter", "RoutingCore"],
            path: "Tests/RoutingAdapterTests"
        )
    ]
)
