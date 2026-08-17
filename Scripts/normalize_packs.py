#!/usr/bin/env python3
"""Normalize peak volume across all click/space/enter/delete samples in every
real-recording pack. Onset-sliced real recordings inherit whatever loudness
that particular keystroke happened to have -- unlike the synthesized packs,
nothing was normalizing them, so peaks varied by up to ~14x within a single
pack (some barely audible, some too loud). This brings every sample to a
consistent target peak while leaving confirm chimes (already normalized by
make_pop) untouched.
"""
import os
import struct
import wave

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "Sources", "Tappy", "Resources", "sounds")
TARGET_PEAK = 0.6
PREFIXES = ("click_down", "click_up", "space_down", "space_up", "enter_down", "enter_up", "delete_down", "delete_up")


def normalize_wav(path, target_peak):
    with wave.open(path, "rb") as f:
        params = f.getparams()
        raw = f.readframes(params.nframes)
    samples = list(struct.unpack(f"<{params.nframes}h", raw))
    peak = max((abs(s) for s in samples), default=1) or 1
    scale = min(20.0, (target_peak * 32767) / peak)
    scaled = [max(-32768, min(32767, int(s * scale))) for s in samples]
    with wave.open(path, "wb") as f:
        f.setparams(params)
        f.writeframes(struct.pack(f"<{len(scaled)}h", *scaled))
    return peak / 32767, target_peak


def main():
    for pack_name in sorted(os.listdir(SOUNDS_DIR)):
        pack_dir = os.path.join(SOUNDS_DIR, pack_name)
        if not os.path.isdir(pack_dir):
            continue
        changed = 0
        for fname in sorted(os.listdir(pack_dir)):
            if not fname.endswith(".wav") or not fname.startswith(PREFIXES):
                continue
            old_peak, new_peak = normalize_wav(os.path.join(pack_dir, fname), TARGET_PEAK)
            changed += 1
        if changed:
            print(f"{pack_name}: normalized {changed} files to peak={TARGET_PEAK}")


if __name__ == "__main__":
    main()
