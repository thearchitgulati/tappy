#!/usr/bin/env python3
"""Heuristically rank click samples by likely key size: bigger keys (space,
enter) tend to hit a stabilizer bar and produce a louder, lower-pitched
"thock" than regular alpha keys. Uses peak amplitude + zero-crossing rate
(a cheap proxy for dominant pitch, no FFT needed) as signals.
"""
import os
import struct
import sys
import wave


def read_wav_mono16(path):
    with wave.open(path, "rb") as f:
        rate = f.getframerate()
        n = f.getnframes()
        raw = f.readframes(n)
    samples = struct.unpack(f"<{n}h", raw)
    return list(samples), rate


def analyze(path):
    samples, rate = read_wav_mono16(path)
    n = len(samples)
    peak = max(abs(s) for s in samples) / 32768.0
    zero_crossings = sum(
        1 for i in range(1, n) if (samples[i - 1] >= 0) != (samples[i] >= 0)
    )
    zcr = zero_crossings / (n / rate)  # crossings per second, proxy for pitch
    return peak, zcr


def main():
    root = os.path.join(os.path.dirname(__file__), "..", "Sources", "Tappy", "Resources", "sounds")
    for pack_name in sorted(os.listdir(root)):
        pack_dir = os.path.join(root, pack_name)
        if not os.path.isdir(pack_dir):
            continue
        clicks = sorted(f for f in os.listdir(pack_dir) if f.startswith("click_"))
        if not clicks:
            continue
        print(f"\n{pack_name}:")
        results = []
        for click in clicks:
            peak, zcr = analyze(os.path.join(pack_dir, click))
            results.append((click, peak, zcr))
        for click, peak, zcr in sorted(results, key=lambda r: r[2]):
            print(f"  {click}: peak={peak:.3f} zcr={zcr:.0f}Hz")


if __name__ == "__main__":
    main()
