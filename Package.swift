// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "Tappy",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "Tappy",
            path: "Sources/Tappy",
            // Resources/ (sounds + Info.plist) is packaged manually by
            // Scripts/build_app.sh into Contents/Resources, read at runtime
            // via Bundle.main.resourceURL -- SwiftPM's own resource-bundle
            // mechanism (Bundle.module) isn't compatible with a properly
            // codesigned .app. Excluded here so `swift build` doesn't warn
            // about "unhandled files" for the whole sounds/ tree.
            exclude: ["Resources"]
        )
    ]
)
