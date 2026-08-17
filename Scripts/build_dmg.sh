#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="Tappy"
APP_BUNDLE="$ROOT_DIR/.build/$APP_NAME.app"
DMG_STAGING="$ROOT_DIR/.build/dmg_staging"
DMG_PATH="$ROOT_DIR/.build/$APP_NAME.dmg"

# Read version from Info.plist so the DMG filename stays in sync.
VERSION=$(/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$ROOT_DIR/Sources/$APP_NAME/Resources/Info.plist")
DMG_VERSIONED_PATH="$ROOT_DIR/.build/${APP_NAME}-${VERSION}.dmg"

echo "Building and signing the app first..."
"$ROOT_DIR/Scripts/build_app.sh"

# A stale mount from an earlier/interrupted run can shadow the volume this
# run creates (macOS silently mounts the new one as "Tappy 1", so our
# AppleScript/SetFile calls end up targeting the wrong, already-finalized
# disk). Clear out any leftovers first.
for vol in /Volumes/"$APP_NAME"*; do
  [ -e "$vol" ] && hdiutil detach "$vol" -force >/dev/null 2>&1 || true
done

echo "Staging DMG contents..."
rm -rf "$DMG_STAGING" "$DMG_PATH" "$DMG_VERSIONED_PATH"
mkdir -p "$DMG_STAGING"

cp -R "$APP_BUNDLE" "$DMG_STAGING/"
ln -s /Applications "$DMG_STAGING/Applications"

echo "Adding installer background..."
mkdir -p "$DMG_STAGING/.background"
cp "$ROOT_DIR/AppIcon/dmg_background.png" "$DMG_STAGING/.background/background.png"
sync

# Build a writable DMG first so a real mounted Finder window can lay out
# icon positions and a background picture (persisted into a .DS_Store on
# the volume) -- a plain `hdiutil create` from a folder has no Finder
# session to generate that layout, so it always looks like a bare window.
#
# Deliberately blank + explicitly sized rather than `-srcfolder`: with
# -srcfolder, hdiutil auto-sizes the image from the source content and
# silently ignores any -size override, and that auto-sizing has repeatedly
# come in too tight once HFS+ formatting overhead is subtracted -- large
# files (like the volume icon) then silently fail to copy with no error
# from hdiutil itself. Creating blank at a generous fixed size and copying
# the staged content in afterwards sidesteps that entirely.
RW_DMG_PATH="$ROOT_DIR/.build/${APP_NAME}-rw.dmg"
rm -f "$RW_DMG_PATH"
echo "Creating writable staging DMG..."
hdiutil create -volname "$APP_NAME" -ov -fs HFS+ -size 60m "$RW_DMG_PATH" >/dev/null

ATTACH_PLIST="$ROOT_DIR/.build/attach.plist"
hdiutil attach "$RW_DMG_PATH" -readwrite -noverify -noautoopen -plist > "$ATTACH_PLIST"
DEVICE=$(python3 -c "
import plistlib
with open('$ATTACH_PLIST', 'rb') as f:
    data = plistlib.load(f)
for e in data['system-entities']:
    if e.get('mount-point'):
        print(e['dev-entry'])
        break
")
VOLUME=$(python3 -c "
import plistlib
with open('$ATTACH_PLIST', 'rb') as f:
    data = plistlib.load(f)
for e in data['system-entities']:
    if e.get('mount-point'):
        print(e['mount-point'])
        break
")
rm -f "$ATTACH_PLIST"

# Use the disk's actual mounted name (not the hardcoded $APP_NAME) for every
# subsequent Finder/SetFile step -- if a stale volume from an earlier/failed
# run is still mounted as "Tappy", macOS silently mounts this run's volume as
# "Tappy 1" instead, and any hardcoded "tell disk \"Tappy\"" would style the
# wrong, already-stale disk while this run's real volume goes unstyled.
VOLUME_NAME=$(basename "$VOLUME")

echo "Copying staged contents onto $VOLUME..."
cp -R "$DMG_STAGING"/. "$VOLUME"/
sync

echo "Styling Finder window ($VOLUME)..."
osascript <<OSA
tell application "Finder"
  tell disk "$VOLUME_NAME"
    open
    set current view of container window to icon view
    set toolbar visible of container window to false
    set statusbar visible of container window to false
    set the bounds of container window to {400, 120, 1060, 560}
    set theViewOptions to the icon view options of container window
    set arrangement of theViewOptions to not arranged
    set icon size of theViewOptions to 128
    set background picture of theViewOptions to file ".background:background.png"
    set position of item "$APP_NAME.app" of container window to {161, 205}
    set position of item "Applications" of container window to {499, 205}
    close
    open
    update without registering applications
    delay 2
  end tell
end tell
OSA

sync
chmod -Rf go-w "$VOLUME" 2>/dev/null || true
hdiutil detach "$DEVICE" >/dev/null

echo "Creating $DMG_PATH..."
hdiutil convert "$RW_DMG_PATH" -format UDZO -ov -o "$DMG_PATH" >/dev/null
mv "$DMG_PATH" "$DMG_VERSIONED_PATH"

rm -f "$RW_DMG_PATH"
rm -rf "$DMG_STAGING"

echo ""
echo "Done: $DMG_VERSIONED_PATH"
ls -lh "$DMG_VERSIONED_PATH"
