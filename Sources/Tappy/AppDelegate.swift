import AppKit

private let kVKANSI_C: Int64 = 0x08
private let kVKANSI_V: Int64 = 0x09
private let kVKSpace: Int64 = 0x31
private let kVKReturn: Int64 = 0x24
private let kVKKeypadEnter: Int64 = 0x4C
private let kVKDelete: Int64 = 0x33
private let kVKForwardDelete: Int64 = 0x75
private let selectedPackDefaultsKey = "selectedPack"
private let accessibilityExplainerShownKey = "accessibilityExplainerShown"
private let volumeDefaultsKey = "volume"

final class AppDelegate: NSObject, NSApplicationDelegate, NSMenuDelegate {
    private var statusItem: NSStatusItem?
    private var enableMenuItem: NSMenuItem?
    private var accessibilityMenuItem: NSMenuItem?
    private var packMenuItems: [NSMenuItem] = []
    private let audioEngine = AudioEngine()
    private var keyTap: KeyTap?
    private var isEnabled = true
    private var hasAccessibilityPermission = false
    private var menuBarIconOn: NSImage?
    private var menuBarIconOff: NSImage?
    private var toastWindow: NSWindow?

    func applicationDidFinishLaunching(_ notification: Notification) {
        startApp()
    }

    private func startApp() {
        NSApp.setActivationPolicy(.accessory)
        restoreSelectedPack()
        restoreVolume()
        setupStatusItem()
        keyTap = KeyTap { [weak self] keyCode, flags in
            self?.handleKeyDown(keyCode: keyCode, flags: flags)
        }
        beginAccessibilityFlow()
    }

    private func handleKeyDown(keyCode: Int64, flags: CGEventFlags) {
        guard isEnabled else { return }

        let isCommandDown = flags.contains(.maskCommand)
        if isCommandDown && keyCode == kVKANSI_C {
            audioEngine.playConfirm(.copy)
            return
        }
        if isCommandDown && keyCode == kVKANSI_V {
            audioEngine.playConfirm(.paste)
            return
        }

        let category: KeyCategory
        switch keyCode {
        case kVKSpace: category = .space
        case kVKReturn, kVKKeypadEnter: category = .enter
        case kVKDelete, kVKForwardDelete: category = .delete
        default: category = .regular
        }
        audioEngine.playClick(category: category)
    }

    private func setupStatusItem() {
        menuBarIconOn = Self.loadMenuBarIcon(named: "menubar_on")
        menuBarIconOff = Self.loadMenuBarIcon(named: "menubar_off")

        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        item.button?.image = menuBarIconOff ?? NSImage(systemSymbolName: "keyboard.fill", accessibilityDescription: "Tappy")

        let menu = NSMenu()
        menu.delegate = self
        let enableItem = NSMenuItem(title: "Enabled", action: #selector(toggleEnabled), keyEquivalent: "")
        enableItem.target = self
        enableItem.state = .on
        menu.addItem(enableItem)
        enableMenuItem = enableItem

        let accessItem = NSMenuItem(title: "Grant Accessibility Access…", action: #selector(openAccessibilitySettings), keyEquivalent: "")
        accessItem.target = self
        accessItem.isHidden = true
        menu.addItem(accessItem)
        accessibilityMenuItem = accessItem

        menu.addItem(NSMenuItem.separator())
        menu.addItem(makeVolumeMenuItem())

        menu.addItem(NSMenuItem.separator())

        let packMenu = NSMenu()
        packMenuItems = []
        for pack in audioEngine.packs {
            let item = NSMenuItem(title: pack.name, action: #selector(selectPack(_:)), keyEquivalent: "")
            item.target = self
            item.state = (pack.name == audioEngine.currentPack?.name) ? .on : .off
            packMenu.addItem(item)
            packMenuItems.append(item)
        }
        let packParentItem = NSMenuItem(title: "Sound Pack", action: nil, keyEquivalent: "")
        packParentItem.submenu = packMenu
        menu.addItem(packParentItem)

        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit Tappy", action: #selector(quit), keyEquivalent: "q"))

        item.menu = menu
        statusItem = item
    }

    private func restoreSelectedPack() {
        guard let savedName = UserDefaults.standard.string(forKey: selectedPackDefaultsKey) else { return }
        audioEngine.selectPack(named: savedName)
    }

    private func restoreVolume() {
        guard UserDefaults.standard.object(forKey: volumeDefaultsKey) != nil else { return }
        audioEngine.volume = UserDefaults.standard.float(forKey: volumeDefaultsKey)
    }

    /// Builds a custom menu item hosting a live volume slider -- NSMenuItem
    /// has no built-in slider, so this embeds a plain NSSlider in a small
    /// container view via `view`, matching how System Settings/Control
    /// Center-style menus expose sliders inside a menu.
    private func makeVolumeMenuItem() -> NSMenuItem {
        let container = NSView(frame: NSRect(x: 0, y: 0, width: 200, height: 36))

        let label = NSTextField(labelWithString: "Volume")
        label.font = NSFont.menuFont(ofSize: 0)
        label.frame = NSRect(x: 14, y: 8, width: 55, height: 18)
        container.addSubview(label)

        let slider = NSSlider(value: Double(audioEngine.volume), minValue: 0, maxValue: 1, target: self, action: #selector(volumeSliderChanged(_:)))
        slider.frame = NSRect(x: 72, y: 6, width: 114, height: 20)
        slider.isContinuous = true
        container.addSubview(slider)

        let item = NSMenuItem()
        item.view = container
        return item
    }

    @objc private func volumeSliderChanged(_ sender: NSSlider) {
        let volume = Float(sender.doubleValue)
        audioEngine.volume = volume
        UserDefaults.standard.set(volume, forKey: volumeDefaultsKey)
    }

    /// Entry point for the permission flow, called once at launch. Shows a
    /// plain-language explainer before the system's generic Accessibility
    /// dialog -- without it, a first-time user has no context for why a
    /// menu-bar keyboard app is asking for this (there's no README bundled
    /// anymore to explain it).
    private func beginAccessibilityFlow() {
        if KeyTap.hasAccessibilityPermission(promptIfNeeded: false) {
            accessibilityPermissionGranted(showToast: false)
            return
        }

        let alreadyExplained = UserDefaults.standard.bool(forKey: accessibilityExplainerShownKey)
        guard !alreadyExplained else {
            pollForAccessibilityPermission(promptIfNeeded: true)
            return
        }
        UserDefaults.standard.set(true, forKey: accessibilityExplainerShownKey)

        let alert = NSAlert()
        alert.messageText = "Tappy needs Accessibility access"
        alert.informativeText = "This lets Tappy hear your keystrokes system-wide so it can play a click sound as you type. Tappy never stores or sends anything you type.\n\nClick Continue, then switch Tappy on in System Settings."
        alert.addButton(withTitle: "Continue")
        alert.addButton(withTitle: "Not Now")
        NSApp.activate(ignoringOtherApps: true)
        let response = alert.runModal()
        pollForAccessibilityPermission(promptIfNeeded: response == .alertFirstButtonReturn)
    }

    /// Polls for the user granting permission in System Settings, since
    /// there's no callback for the trust change. Only shows the system
    /// prompt on the first call -- subsequent checks are silent so we don't
    /// spam the user with the same dialog every couple seconds.
    private func pollForAccessibilityPermission(promptIfNeeded: Bool) {
        if KeyTap.hasAccessibilityPermission(promptIfNeeded: promptIfNeeded) {
            accessibilityPermissionGranted(showToast: true)
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            self?.pollForAccessibilityPermission(promptIfNeeded: false)
        }
    }

    private func accessibilityPermissionGranted(showToast: Bool) {
        hasAccessibilityPermission = true
        updateStatusIcon()
        _ = keyTap?.start()
        if showToast {
            showReadyToast()
        }
    }

    private func updateStatusIcon() {
        let isActive = isEnabled && hasAccessibilityPermission
        statusItem?.button?.image = isActive ? menuBarIconOn : menuBarIconOff
    }

    func menuWillOpen(_ menu: NSMenu) {
        accessibilityMenuItem?.isHidden = hasAccessibilityPermission
    }

    @objc private func openAccessibilitySettings() {
        guard let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility") else { return }
        NSWorkspace.shared.open(url)
    }

    /// A brief native toast confirming the app is actually working, since
    /// there's otherwise zero feedback after granting permission -- the menu
    /// bar icon alone doesn't tell a first-time user anything changed.
    private func showReadyToast() {
        guard let button = statusItem?.button, let buttonWindow = button.window else { return }
        let buttonFrameInScreen = buttonWindow.convertToScreen(button.convert(button.bounds, to: nil))

        let message = "  ✓ You're all set — try typing anywhere  "
        let font = NSFont.systemFont(ofSize: 13, weight: .medium)
        let textWidth = (message as NSString).size(withAttributes: [.font: font]).width
        let width = textWidth + 24
        let height: CGFloat = 34

        let panel = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: width, height: height),
            styleMask: [.borderless],
            backing: .buffered,
            defer: false
        )
        panel.isOpaque = false
        panel.backgroundColor = .clear
        panel.hasShadow = true
        panel.level = .statusBar
        panel.ignoresMouseEvents = true

        let visualEffect = NSVisualEffectView(frame: NSRect(x: 0, y: 0, width: width, height: height))
        visualEffect.material = .hudWindow
        visualEffect.state = .active
        visualEffect.wantsLayer = true
        visualEffect.layer?.cornerRadius = height / 2
        visualEffect.layer?.masksToBounds = true
        visualEffect.autoresizingMask = [.width, .height]

        let label = NSTextField(labelWithString: message)
        label.font = font
        label.alignment = .center
        label.frame = visualEffect.bounds
        label.autoresizingMask = [.width, .height]
        visualEffect.addSubview(label)
        panel.contentView = visualEffect

        let x = buttonFrameInScreen.midX - width / 2
        let y = buttonFrameInScreen.minY - height - 8
        panel.setFrameOrigin(NSPoint(x: x, y: y))

        panel.alphaValue = 0
        panel.orderFrontRegardless()
        toastWindow = panel

        NSAnimationContext.runAnimationGroup { context in
            context.duration = 0.2
            panel.animator().alphaValue = 1
        }

        DispatchQueue.main.asyncAfter(deadline: .now() + 3.5) { [weak self] in
            guard let panel = self?.toastWindow else { return }
            NSAnimationContext.runAnimationGroup { context in
                context.duration = 0.3
                panel.animator().alphaValue = 0
            } completionHandler: {
                panel.orderOut(nil)
            }
        }
    }

    @objc private func toggleEnabled() {
        isEnabled.toggle()
        enableMenuItem?.state = isEnabled ? .on : .off
        updateStatusIcon()
    }

    /// Loads a menu bar template icon from the app bundle, combining its
    /// @1x/@2x/@3x variants into one NSImage so AppKit can pick the right
    /// resolution per screen -- there's no asset catalog to do this for us
    /// since resources are hand-copied by Scripts/build_app.sh.
    private static func loadMenuBarIcon(named name: String) -> NSImage? {
        guard let dir = Bundle.main.resourceURL?.appendingPathComponent("MenuBarIcons") else { return nil }
        let image = NSImage(size: NSSize(width: 18, height: 18))
        var addedAny = false
        for suffix in ["", "@2x", "@3x"] {
            let url = dir.appendingPathComponent("\(name)\(suffix).png")
            guard let rep = NSImageRep(contentsOf: url) else { continue }
            rep.size = NSSize(width: 18, height: 18)
            image.addRepresentation(rep)
            addedAny = true
        }
        guard addedAny else { return nil }
        image.isTemplate = true
        return image
    }

    @objc private func selectPack(_ sender: NSMenuItem) {
        audioEngine.selectPack(named: sender.title)
        UserDefaults.standard.set(sender.title, forKey: selectedPackDefaultsKey)
        for item in packMenuItems {
            item.state = (item === sender) ? .on : .off
        }
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }
}
