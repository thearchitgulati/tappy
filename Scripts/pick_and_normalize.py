#!/usr/bin/env python3
"""Re-select click variants from a sliced onset set, filtering out weak/
false-positive onsets by peak amplitude before picking, then normalize the
selected set to a consistent peak. This is the proper fix for "some sounds
too loud, some inaudible" -- picking already-solid onsets needs only a
modest normalization pass, unlike blindly amplifying a weak, noisy onset
by 40x to hit a target peak.
"""
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(__file__))
from slice_clicks import read_wav_mono16, envelope, find_onsets, slice_clip, write_wav  # noqa: E402


def slice_all(wav_path):
    samples, rate = read_wav_mono16(wav_path)
    env = envelope(samples, rate)
    onsets, _ = find_onsets(env, rate)
    clips = []
    for i, onset in enumerate(onsets):
        next_onset = onsets[i + 1] if i + 1 < len(onsets) else None
        clip = slice_clip(samples, rate, onset, next_onset=next_onset)
        peak = max((abs(s) for s in clip), default=0) / 32768.0
        clips.append((onset / rate, clip, peak))
    return clips, rate


def pick_well_spaced(clips, count, low_pct=60, high_pct=95):
    """Keep only onsets whose peak falls within [low_pct, high_pct] of the
    peak distribution -- drops weak/false-positive onsets (below low_pct)
    AND outlier spikes unrelated to normal keystrokes (above high_pct),
    since relative-to-max is unreliable when one freak spike dwarfs the
    rest. Picks `count` spread evenly across time from what remains."""
    if not clips:
        return []
    peaks = sorted(c[2] for c in clips)
    lo = peaks[int(low_pct / 100 * (len(peaks) - 1))]
    hi = peaks[int(high_pct / 100 * (len(peaks) - 1))]
    strong = [c for c in clips if lo <= c[2] <= hi]
    if not strong:
        strong = clips
    if len(strong) <= count:
        return strong
    step = len(strong) / count
    return [strong[int(i * step)] for i in range(count)]


def normalize_clip(clip, target_peak=0.6, max_gain=6.0):
    peak = max((abs(s) for s in clip), default=0) / 32768.0
    if peak == 0:
        return clip
    scale = min(max_gain, target_peak / peak)
    return [max(-32768, min(32767, int(s * scale))) for s in clip]


def build_pack_clicks(wav_path, out_dir, prefix, count, low_pct=60, high_pct=95, target_peak=0.6):
    clips, rate = slice_all(wav_path)
    picked = pick_well_spaced(clips, count, low_pct=low_pct, high_pct=high_pct)
    os.makedirs(out_dir, exist_ok=True)
    for i, (t, clip, peak) in enumerate(picked):
        normalized = normalize_clip(clip, target_peak=target_peak)
        write_wav(os.path.join(out_dir, f"{prefix}_{i}.wav"), normalized, rate)
    return len(picked)
