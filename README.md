# Tappy

Real mechanical-keyboard click sounds for any keyboard on your Mac. Tappy sits in your menu bar and plays a click as you type — no new hardware required.

**[Download for Mac](https://get-tappy.vercel.app)**

## Install

1. Download the DMG from [get-tappy.vercel.app](https://get-tappy.vercel.app) and drag Tappy into Applications.
2. Since Tappy isn't notarized by Apple (no paid developer account behind this), macOS will flag it as from an unidentified developer. Right-click Tappy → **Open** → **Open** to launch it the first time — you only need to do this once.
3. On first launch, Tappy explains why it needs Accessibility access (it's how it hears your keystrokes system-wide to play the click) and walks you through granting it in System Settings.
4. That's it — Tappy lives in your menu bar. Click the icon to switch sound packs, adjust volume, or quit.

## Why it needs Accessibility access

Tappy listens for key-down events system-wide via a `CGEventTap` so it can play a click no matter what app you're typing in. It only reads which key was pressed — it never logs, stores, or transmits anything you type.

## Building from source

Requires Xcode command line tools and macOS 13+.

```
git clone https://github.com/thearchitgulati/tappy.git
cd tappy
./Scripts/build_app.sh   # builds .build/Tappy.app
./Scripts/build_dmg.sh   # builds a distributable DMG in .build/
```

The app is ad-hoc signed (`codesign --force --sign -`), not notarized — building from source gives you the same unidentified-developer warning on first launch as the downloaded build.

## Project layout

- `Sources/Tappy/` — the app itself (Swift, AppKit + AVAudioEngine)
- `Scripts/` — build scripts for the app bundle, DMG installer, and landing page
- `Landing/` — the [get-tappy.vercel.app](https://get-tappy.vercel.app) landing/download page
- `CHANGELOG.json` — version history, also rendered on the download page

## Changelog

See [CHANGELOG.json](CHANGELOG.json) for version history, or check the "What's new" section on the [download page](https://get-tappy.vercel.app).

## Sound credits

See [SOUND_CREDITS.md](SOUND_CREDITS.md).

## License

MIT
