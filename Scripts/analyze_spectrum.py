#!/usr/bin/env python3
"""Spectral analysis of reference click recordings, to inform synthesis
parameters (dominant frequencies, decay rates, tick/body energy balance)
instead of guessing them.
"""
import os
import sys

import numpy as np


def load_wav(path):
    import wave
    with wave.open(path, "rb") as f:
        rate = f.getframerate()
        n = f.getnframes()
        raw = f.readframes(n)
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    return samples, rate


def decay_rate(samples, rate):
    """Fit amplitude envelope to A*exp(-k*t) via log-linear regression."""
    envelope = np.abs(samples)
    # smooth with a small moving average to avoid fitting to zero-crossings
    win = max(1, int(rate * 0.001))
    kernel = np.ones(win) / win
    smoothed = np.convolve(envelope, kernel, mode="same")
    smoothed = np.maximum(smoothed, 1e-6)

    t = np.arange(len(samples)) / rate
    # only fit the decay after the peak
    peak_idx = np.argmax(smoothed)
    t_fit = t[peak_idx:]
    y_fit = np.log(smoothed[peak_idx:])
    if len(t_fit) < 5:
        return 0.0
    slope, _ = np.polyfit(t_fit, y_fit, 1)
    return max(0.0, -slope)


def spectral_peaks(samples, rate, n_peaks=3, fmin=80, fmax=8000):
    n = len(samples)
    windowed = samples * np.hanning(n)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(n, d=1 / rate)

    mask = (freqs >= fmin) & (freqs <= fmax)
    freqs = freqs[mask]
    spectrum = spectrum[mask]

    if len(spectrum) == 0:
        return []

    # find local maxima
    peaks = []
    for i in range(1, len(spectrum) - 1):
        if spectrum[i] > spectrum[i - 1] and spectrum[i] > spectrum[i + 1]:
            peaks.append((freqs[i], spectrum[i]))
    peaks.sort(key=lambda p: -p[1])
    return peaks[:n_peaks]


def spectral_centroid(samples, rate):
    n = len(samples)
    windowed = samples * np.hanning(n)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(n, d=1 / rate)
    total = spectrum.sum()
    if total == 0:
        return 0.0
    return float((freqs * spectrum).sum() / total)


def high_low_energy_ratio(samples, rate, split=1500):
    n = len(samples)
    windowed = samples * np.hanning(n)
    spectrum = np.abs(np.fft.rfft(windowed)) ** 2
    freqs = np.fft.rfftfreq(n, d=1 / rate)
    low = spectrum[freqs < split].sum()
    high = spectrum[freqs >= split].sum()
    total = low + high
    if total == 0:
        return 0.0
    return float(high / total)


def analyze_file(path):
    samples, rate = load_wav(path)
    peak_amp = float(np.max(np.abs(samples)))
    decay = decay_rate(samples, rate)
    centroid = spectral_centroid(samples, rate)
    peaks = spectral_peaks(samples, rate)
    high_ratio = high_low_energy_ratio(samples, rate)
    duration_ms = len(samples) / rate * 1000
    return dict(
        peak_amp=peak_amp,
        decay=decay,
        centroid=centroid,
        peaks=peaks,
        high_ratio=high_ratio,
        duration_ms=duration_ms,
    )


def main():
    root = os.path.join(os.path.dirname(__file__), "..", "Sources", "Tappy", "Resources", "sounds")
    for pack_name in sorted(os.listdir(root)):
        pack_dir = os.path.join(root, pack_name)
        if not os.path.isdir(pack_dir):
            continue
        clicks = sorted(f for f in os.listdir(pack_dir) if f.startswith("click_"))
        if not clicks:
            continue
        print(f"\n=== {pack_name} ===")
        for click in clicks[:3]:
            result = analyze_file(os.path.join(pack_dir, click))
            peaks_str = ", ".join(f"{f:.0f}Hz" for f, _ in result["peaks"])
            print(
                f"  {click}: dur={result['duration_ms']:.0f}ms peak={result['peak_amp']:.2f} "
                f"decay={result['decay']:.0f}/s centroid={result['centroid']:.0f}Hz "
                f"high/low={result['high_ratio']:.2f} top_freqs=[{peaks_str}]"
            )


if __name__ == "__main__":
    main()
