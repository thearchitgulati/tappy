#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="Tappy"
BUILD_DIR="$ROOT_DIR/.build/release"
APP_BUNDLE="$ROOT_DIR/.build/$APP_NAME.app"

echo "Building release binary..."
swift build -c release

echo "Assembling $APP_NAME.app..."
rm -rf "$APP_BUNDLE"
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

cp "$BUILD_DIR/$APP_NAME" "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
strip -x "$APP_BUNDLE/Contents/MacOS/$APP_NAME"
cp "$ROOT_DIR/Sources/$APP_NAME/Resources/Info.plist" "$APP_BUNDLE/Contents/Info.plist"

if [ -f "$ROOT_DIR/AppIcon/AppIcon.icns" ]; then
    cp "$ROOT_DIR/AppIcon/AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
fi

# Copy sounds straight into Contents/Resources (the standard macOS location,
# read at runtime via Bundle.main.resourceURL) rather than relying on
# SwiftPM's generated Bundle.module resource bundle -- that accessor assumes
# a bare-executable layout and isn't compatible with a properly codesigned
# .app, where everything must live under Contents/.
cp -R "$ROOT_DIR/Sources/$APP_NAME/Resources/sounds" "$APP_BUNDLE/Contents/Resources/sounds"
cp -R "$ROOT_DIR/Sources/$APP_NAME/Resources/MenuBarIcons" "$APP_BUNDLE/Contents/Resources/MenuBarIcons"

echo "Ad-hoc signing (no Developer ID -- Gatekeeper will still warn on other Macs)..."
# No --deep: the bundled sounds/ resource directory isn't a signable bundle
# (no executable, no Info.plist) -- only the app itself needs a signature.
codesign --force --sign - "$APP_BUNDLE"
codesign --verify --verbose "$APP_BUNDLE" 2>&1

echo "Done: $APP_BUNDLE"
echo ""
echo "Launch with: open '$APP_BUNDLE'"
