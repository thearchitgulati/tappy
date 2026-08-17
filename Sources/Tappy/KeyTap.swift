import AppKit

/// Wraps a global CGEventTap that observes key-down events system-wide.
/// Requires the user to grant Accessibility permission to this app.
final class KeyTap {
    private var eventTap: CFMachPort?
    private var runLoopSource: CFRunLoopSource?
    private let onKeyDown: (Int64, CGEventFlags) -> Void

    init(onKeyDown: @escaping (Int64, CGEventFlags) -> Void) {
        self.onKeyDown = onKeyDown
    }

    static func hasAccessibilityPermission(promptIfNeeded: Bool) -> Bool {
        let options: NSDictionary = [kAXTrustedCheckOptionPrompt.takeRetainedValue() as String: promptIfNeeded]
        return AXIsProcessTrustedWithOptions(options)
    }

    func start() -> Bool {
        let eventMask = (1 << CGEventType.keyDown.rawValue)

        let callback: CGEventTapCallBack = { _, type, event, refcon in
            guard type == .keyDown, let refcon else {
                return Unmanaged.passRetained(event)
            }
            let tap = Unmanaged<KeyTap>.fromOpaque(refcon).takeUnretainedValue()
            let keyCode = event.getIntegerValueField(.keyboardEventKeycode)
            tap.onKeyDown(keyCode, event.flags)
            return Unmanaged.passRetained(event)
        }

        let selfPtr = Unmanaged.passUnretained(self).toOpaque()

        guard let tap = CGEvent.tapCreate(
            tap: .cgSessionEventTap,
            place: .headInsertEventTap,
            options: .listenOnly,
            eventsOfInterest: CGEventMask(eventMask),
            callback: callback,
            userInfo: selfPtr
        ) else {
            return false
        }

        eventTap = tap
        let source = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, tap, 0)
        runLoopSource = source
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, .commonModes)
        CGEvent.tapEnable(tap: tap, enable: true)
        return true
    }

    func stop() {
        if let tap = eventTap {
            CGEvent.tapEnable(tap: tap, enable: false)
        }
        if let source = runLoopSource {
            CFRunLoopRemoveSource(CFRunLoopGetCurrent(), source, .commonModes)
        }
        eventTap = nil
        runLoopSource = nil
    }
}
