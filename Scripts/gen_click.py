#!/usr/bin/env python3
"""Generate synthesized click packs, informed by real spectral/timing
analysis of 7 distinct switch families (see analyze_spectrum.py output run
against downloaded reference previews -- analyzed for data only, no audio
copied or shipped). Measured character per family:

  Cherry Black   : 35-50ms,  decay 108-267/s, centroid 4500-8400Hz, high/low ~0.9+  (crisp, snappy)
  Crystal Clicky : 57-65ms,  decay 55-165/s,  centroid 3600-6300Hz, high/low ~0.6-0.8 (clicky, rounder)
  Oreo           : 58-65ms;  DOWN thocky (centroid ~3000-3600Hz, high/low ~0.05-0.17),
                              UP bright/clicky (centroid ~5600-6300Hz, high/low ~0.7-0.98)
  Cardboard      : 73-140ms, decay 61-200/s,  centroid 2900-3800Hz, high/low ~0.7-0.94 (long, resonant)
  Milky Soft     : 75-104ms, decay 47-63/s,   centroid 2600-3600Hz, high/low ~0.7-0.96 (gentle, muffled)
  Deep Red       : 62-82ms,  decay 53-133/s,  centroid 1150-2150Hz, high/low ~0.00-0.02 (deep bassy thock)
  Creamy         : DOWN 89-115ms slow decay ~30-36/s, rich mid (2900-4200Hz);
                              UP much quieter/shorter/faster (peak ~0.04-0.24, as short as 23ms)

Each click layers three components:
  1. impulse  -- a very brief (~2ms) broadband snap at the moment of contact
  2. tick     -- a tonal, fairly narrow-band resonance (the housing's ring)
  3. body     -- a lower resonance (the "thock")
"""
import json
import math
import os
import random
import struct
import wave

SAMPLE_RATE = 44100


def _write_wav(path, samples, target_peak=0.85):
    peak = max((abs(s) for s in samples), default=1.0) or 1.0
    scale = min(10.0, target_peak / peak)
    frames = bytearray()
    for s in samples:
        value = int(max(-1.0, min(1.0, s * scale)) * 32767)
        frames += struct.pack("<h", value)
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(bytes(frames))


def _svf_bandpass(input_samples, freq, q):
    f = 2 * math.sin(math.pi * min(freq, SAMPLE_RATE / 3) / SAMPLE_RATE)
    q_inv = 1 / q
    low = 0.0
    band = 0.0
    out = []
    for x in input_samples:
        high = x - low - q_inv * band
        band = band + f * high
        low = low + f * band
        out.append(band)
    return out


def _white_noise(n, seed):
    random.seed(seed)
    return [random.uniform(-1, 1) for _ in range(n)]


def _resonance(n, freq, decay, inharmonic_ratio=None, inharmonic_mix=0.3):
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        v = math.sin(2 * math.pi * freq * t)
        if inharmonic_ratio:
            v = (1 - inharmonic_mix) * v + inharmonic_mix * math.sin(2 * math.pi * freq * inharmonic_ratio * t)
        out.append(v * math.exp(-decay * t))
    return out


def _one_pole_lowpass(samples, cutoff_freq):
    rc = 1 / (2 * math.pi * cutoff_freq)
    dt = 1 / SAMPLE_RATE
    alpha = dt / (rc + dt)
    out = []
    y = 0.0
    for x in samples:
        y = y + alpha * (x - y)
        out.append(y)
    return out


def make_click(path, seed, duration,
                impulse_amount, impulse_decay,
                tick_freq, tick_q, tick_decay, tick_amount,
                body_freq, body_decay, body_amount,
                body_freq2=None, body2_amount=0.0, target_peak=0.85,
                impulse_lowpass=None):
    n = int(SAMPLE_RATE * duration)

    impulse_noise = _white_noise(n, seed)
    if impulse_lowpass:
        impulse_noise = _one_pole_lowpass(impulse_noise, impulse_lowpass)
    impulse_env = [math.exp(-impulse_decay * (i / SAMPLE_RATE)) for i in range(n)]
    impulse = [impulse_noise[i] * impulse_env[i] for i in range(n)]

    tick_noise = _white_noise(n, seed + 1000)
    tick = _svf_bandpass(tick_noise, tick_freq, tick_q)
    tick_env = [math.exp(-tick_decay * (i / SAMPLE_RATE)) for i in range(n)]
    tick = [tick[i] * tick_env[i] for i in range(n)]

    body = _resonance(n, body_freq, body_decay, inharmonic_ratio=2.76, inharmonic_mix=0.22)

    samples = [
        impulse_amount * impulse[i] + tick_amount * tick[i] + body_amount * body[i]
        for i in range(n)
    ]

    if body_freq2:
        body2 = _resonance(n, body_freq2, body_decay * 1.4, inharmonic_ratio=1.9, inharmonic_mix=0.18)
        samples = [s + body2_amount * b for s, b in zip(samples, body2)]

    _write_wav(path, samples, target_peak=target_peak)


def make_pop(path, freq_start, freq_end, duration, decay, transient_amount, thud=False):
    n = int(SAMPLE_RATE * duration)

    noise = _white_noise(n, seed=hash(path) % 10_000)
    transient = _svf_bandpass(noise, 3200, 6)
    transient_env = [math.exp(-90 * (i / SAMPLE_RATE)) for i in range(n)]
    transient = [t * e for t, e in zip(transient, transient_env)]

    body = []
    for i in range(n):
        t = i / SAMPLE_RATE
        progress = t / duration
        freq = freq_start + (freq_end - freq_start) * progress
        v = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(2 * math.pi * freq * 2 * t)
        body.append(v * math.exp(-decay * t))

    samples = [transient_amount * tr + 0.55 * b for tr, b in zip(transient, body)]

    if thud:
        thud_noise = _white_noise(n, seed=(hash(path) + 1) % 10_000)
        thud_band = _svf_bandpass(thud_noise, 220, 3)
        thud_start = int(duration * 0.55 * SAMPLE_RATE)
        for i in range(thud_start, n):
            t = (i - thud_start) / SAMPLE_RATE
            samples[i] += 0.4 * thud_band[i] * math.exp(-70 * t)

    fade_len = int(0.002 * SAMPLE_RATE)
    for i in range(min(fade_len, n)):
        samples[i] *= i / fade_len

    _write_wav(path, samples, target_peak=0.6)


def _default_up_variant(down_spec):
    """Symmetric families: release is quieter, a touch brighter, decays
    a bit faster than the press -- used unless a pack defines explicit
    up_clicks (for families measured as genuinely asymmetric)."""
    up = dict(down_spec)
    up["tick_freq"] = down_spec["tick_freq"] * 1.12
    up["tick_decay"] = down_spec["tick_decay"] * 1.3
    up["impulse_amount"] = down_spec["impulse_amount"] * 0.7
    up["body_amount"] = down_spec["body_amount"] * 0.6
    up["duration"] = down_spec["duration"] * 0.85
    up["target_peak"] = 0.55
    return up


# All synthesized click packs (Cherry Black, iPhone Click, and the 6 before
# them) were tried and dropped after repeated "still sounds bad" feedback --
# the noise+resonance synthesis approach hit a real ceiling. Current packs
# ("Gaming Click", "Logitech Typing") are built from real CC0-licensed
# recordings instead; see Scripts/assemble_freesound_packs.py. make_click/
# make_pop below are kept for confirm-chime generation and are available if
# synthesis is ever worth revisiting, but PACKS is intentionally empty.
PACKS = {}


def main():
    out_root = os.path.join(
        os.path.dirname(__file__), "..", "Sources", "Tappy", "Resources", "sounds"
    )

    for pack_name, spec in PACKS.items():
        pack_dir = os.path.join(out_root, pack_name)
        os.makedirs(pack_dir, exist_ok=True)
        default_duration = spec["duration"]

        for idx, down_spec in enumerate(spec["clicks"]):
            full_down = dict(down_spec)
            full_down.setdefault("duration", default_duration)
            full_down.setdefault("target_peak", 0.55)
            make_click(os.path.join(pack_dir, f"click_down_{idx}.wav"), seed=idx * 7, **full_down)

            if "up_clicks" in spec:
                up_spec = dict(spec["up_clicks"][idx % len(spec["up_clicks"])])
            else:
                up_spec = _default_up_variant(dict(down_spec, duration=default_duration))
            up_spec.setdefault("target_peak", 0.55)
            make_click(os.path.join(pack_dir, f"click_up_{idx}.wav"), seed=idx * 7 + 500, **up_spec)

        make_pop(
            os.path.join(pack_dir, "confirm_copy.wav"),
            freq_start=600, freq_end=950, duration=0.26, decay=9, transient_amount=0.28,
        )
        make_pop(
            os.path.join(pack_dir, "confirm_paste.wav"),
            freq_start=950, freq_end=560, duration=0.3, decay=8, transient_amount=0.25, thud=True,
        )

        if "click_weights" in spec:
            with open(os.path.join(pack_dir, "click_weights.json"), "w") as f:
                json.dump(spec["click_weights"], f)

        print(f"Wrote pack '{pack_name}' to {pack_dir}")


if __name__ == "__main__":
    main()
