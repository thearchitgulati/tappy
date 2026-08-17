import AVFoundation

struct SoundPack {
    let name: String
    let regular: [AVAudioPCMBuffer]
    let space: [AVAudioPCMBuffer]
    let enter: [AVAudioPCMBuffer]
    let delete: [AVAudioPCMBuffer]
    /// Optional selection weights for `regular`, parallel by index (from
    /// click_weights.json). Falls back to uniform random when nil/mismatched.
    let regularWeights: [Double]?
    let confirmCopy: AVAudioPCMBuffer?
    let confirmPaste: AVAudioPCMBuffer?
}

enum ConfirmSound {
    case copy
    case paste
}

enum KeyCategory {
    case regular
    case space
    case enter
    case delete
}

/// Plays click + confirm samples with low latency via a pool of player nodes.
final class AudioEngine {
    private let engine = AVAudioEngine()
    private var clickPlayers: [AVAudioPlayerNode] = []
    private var confirmPlayers: [AVAudioPlayerNode] = []
    private var nextClickPlayerIndex = 0
    private var nextConfirmPlayerIndex = 0

    private(set) var packs: [SoundPack] = []
    private(set) var currentPack: SoundPack?

    var volume: Float = 0.8 {
        didSet {
            clickPlayers.forEach { $0.volume = volume }
            confirmPlayers.forEach { $0.volume = volume }
        }
    }

    init(playerPoolSize: Int = 8, confirmPoolSize: Int = 2) {
        loadPacks()
        guard let firstPack = packs.first, let format = firstPack.regular.first?.format else {
            print("Tappy: no sound packs found, audio disabled")
            return
        }
        currentPack = firstPack

        for _ in 0..<playerPoolSize {
            let player = AVAudioPlayerNode()
            player.volume = volume
            engine.attach(player)
            engine.connect(player, to: engine.mainMixerNode, format: format)
            clickPlayers.append(player)
        }

        for _ in 0..<confirmPoolSize {
            let player = AVAudioPlayerNode()
            player.volume = volume
            engine.attach(player)
            engine.connect(player, to: engine.mainMixerNode, format: format)
            confirmPlayers.append(player)
        }

        do {
            try engine.start()
        } catch {
            print("Tappy: failed to start audio engine: \(error)")
        }
    }

    func selectPack(named name: String) {
        guard let pack = packs.first(where: { $0.name == name }) else { return }
        currentPack = pack
    }

    private func loadPacks() {
        // Bundle.main.resourceURL (Contents/Resources) rather than SwiftPM's
        // generated Bundle.module: that accessor assumes a bare-executable
        // layout (resource bundle next to the binary) and silently falls
        // back to an absolute build-machine path once packaged as a real
        // signed .app, where Bundle.main.bundleURL is the outer .app and
        // code signing requires everything to live under Contents/ anyway.
        guard let resourceURL = Bundle.main.resourceURL else { return }
        let soundsDir = resourceURL.appendingPathComponent("sounds")
        let fm = FileManager.default
        guard let packDirs = try? fm.contentsOfDirectory(at: soundsDir, includingPropertiesForKeys: nil, options: [.skipsHiddenFiles]) else {
            print("Tappy: no sounds directory found at \(soundsDir.path)")
            return
        }

        for packDir in packDirs.sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) {
            var isDirectory: ObjCBool = false
            guard fm.fileExists(atPath: packDir.path, isDirectory: &isDirectory), isDirectory.boolValue else { continue }

            guard let files = try? fm.contentsOfDirectory(at: packDir, includingPropertiesForKeys: nil) else { continue }

            var regular: [AVAudioPCMBuffer] = []
            var space: [AVAudioPCMBuffer] = []
            var enter: [AVAudioPCMBuffer] = []
            var delete: [AVAudioPCMBuffer] = []
            var confirmCopy: AVAudioPCMBuffer?
            var confirmPaste: AVAudioPCMBuffer?

            for file in files.sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) where file.pathExtension == "wav" {
                guard let buffer = Self.loadBuffer(file) else { continue }
                let name = file.lastPathComponent
                if name == "confirm_copy.wav" {
                    confirmCopy = buffer
                } else if name == "confirm_paste.wav" {
                    confirmPaste = buffer
                } else if name.hasPrefix("space_down") {
                    space.append(buffer)
                } else if name.hasPrefix("enter_down") {
                    enter.append(buffer)
                } else if name.hasPrefix("delete_down") {
                    delete.append(buffer)
                } else if name.hasPrefix("click_down") {
                    regular.append(buffer)
                }
            }

            guard !regular.isEmpty else { continue }

            var regularWeights: [Double]?
            let weightsURL = packDir.appendingPathComponent("click_weights.json")
            if let data = try? Data(contentsOf: weightsURL),
               let weights = try? JSONDecoder().decode([Double].self, from: data),
               weights.count == regular.count {
                regularWeights = weights
            }

            packs.append(SoundPack(
                name: packDir.lastPathComponent,
                regular: regular,
                space: space,
                enter: enter,
                delete: delete,
                regularWeights: regularWeights,
                confirmCopy: confirmCopy,
                confirmPaste: confirmPaste
            ))
        }
    }

    private static func loadBuffer(_ file: URL) -> AVAudioPCMBuffer? {
        guard let audioFile = try? AVAudioFile(forReading: file) else { return nil }
        let format = audioFile.processingFormat
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(audioFile.length)) else { return nil }
        do {
            try audioFile.read(into: buffer)
            return buffer
        } catch {
            print("Tappy: failed to read \(file.lastPathComponent): \(error)")
            return nil
        }
    }

    /// Picks a random buffer index, honoring per-index weights when given
    /// (e.g. the real iPhone keyboard click alternates between two sounds
    /// at roughly a 27%/73% split, not a uniform 50/50 or fixed rotation).
    private static func pickIndex(count: Int, weights: [Double]?) -> Int {
        guard count > 1 else { return 0 }
        guard let weights, weights.count == count else {
            return Int.random(in: 0..<count)
        }
        let total = weights.reduce(0, +)
        guard total > 0 else { return Int.random(in: 0..<count) }
        var roll = Double.random(in: 0..<total)
        for (index, weight) in weights.enumerated() {
            if roll < weight { return index }
            roll -= weight
        }
        return count - 1
    }

    /// Fire-and-forget click playback for a key press. `category` picks a
    /// distinct sample set for larger keys (space/enter/delete) when the
    /// pack provides one, falling back to the regular click set. Safe to
    /// call from any thread.
    func playClick(category: KeyCategory = .regular) {
        guard let pack = currentPack, !clickPlayers.isEmpty else { return }

        let buffers: [AVAudioPCMBuffer]
        let weights: [Double]?
        switch category {
        case .space: buffers = pack.space.isEmpty ? pack.regular : pack.space
        case .enter: buffers = pack.enter.isEmpty ? pack.regular : pack.enter
        case .delete: buffers = pack.delete.isEmpty ? pack.regular : pack.delete
        case .regular: buffers = pack.regular
        }
        weights = (category == .regular) ? pack.regularWeights : nil
        guard !buffers.isEmpty else { return }

        let player = clickPlayers[nextClickPlayerIndex]
        nextClickPlayerIndex = (nextClickPlayerIndex + 1) % clickPlayers.count

        let buffer = buffers[Self.pickIndex(count: buffers.count, weights: weights)]

        player.stop()
        player.scheduleBuffer(buffer, at: nil, options: .interrupts)
        player.play()
    }

    /// Plays a distinct confirmation chime for recognized shortcuts (e.g. Cmd+C / Cmd+V).
    func playConfirm(_ kind: ConfirmSound) {
        guard let pack = currentPack else { return }
        let buffer: AVAudioPCMBuffer?
        switch kind {
        case .copy: buffer = pack.confirmCopy
        case .paste: buffer = pack.confirmPaste
        }
        guard let buffer, !confirmPlayers.isEmpty else { return }

        let player = confirmPlayers[nextConfirmPlayerIndex]
        nextConfirmPlayerIndex = (nextConfirmPlayerIndex + 1) % confirmPlayers.count

        player.stop()
        player.scheduleBuffer(buffer, at: nil, options: .interrupts)
        player.play()
    }
}
