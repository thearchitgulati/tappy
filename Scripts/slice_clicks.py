#!/usr/bin/env python3
"""Detect individual keystroke onsets in a longer recording and slice each
one out as its own short WAV clip, so we can turn a single "typing on camera"
recording into a set of click_N.wav samples for a sound pack.
"""
import math
import os
import struct
import sys
import wave


def read_wav_mono16(path):
    with wave.open(path, "rb") as f:
        assert f.getsampwidth() == 2, "expected 16-bit PCM"
        assert f.getnchannels() == 1, "expected mono"
        rate = f.getframerate()
        n = f.getnframes()
        raw = f.readframes(n)
    samples = struct.unpack(f"<{n}h", raw)
    return list(samples), rate


def envelope(samples, rate, window_ms=3):
    window = max(1, int(rate * window_ms / 1000))
    env = []
    acc = 0.0
    buf = [0.0] * window
    idx = 0
    for s in samples:
        v = (s / 32768.0) ** 2
        acc += v - buf[idx]
        buf[idx] = v
        idx = (idx + 1) % window
        env.append(math.sqrt(max(0.0, acc / window)))
    return env


def find_onsets(env, rate, threshold_ratio=4.0, min_gap_ms=70, floor=0.01):
    sorted_env = sorted(env)
    median = sorted_env[len(sorted_env) // 2] if sorted_env else 0
    threshold = max(floor, median * threshold_ratio)

    min_gap = int(rate * min_gap_ms / 1000)
    onsets = []
    last_onset = -min_gap
    above = False
    for i, v in enumerate(env):
        if v > threshold and not above:
            if i - last_onset >= min_gap:
                onsets.append(i)
                last_onset = i
            above = True
        elif v <= threshold * 0.5:
            above = False
    return onsets, threshold


def write_wav(path, samples, rate):
    with wave.open(path, "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        clipped = [max(-32768, min(32767, int(s))) for s in samples]
        f.writeframes(struct.pack(f"<{len(clipped)}h", *clipped))


def slice_clip(samples, rate, onset, next_onset=None, pre_ms=2, post_ms=90, fade_ms=8, guard_ms=5):
    pre = int(rate * pre_ms / 1000)
    post = int(rate * post_ms / 1000)
    start = max(0, onset - pre)
    end = min(len(samples), onset + post)
    if next_onset is not None:
        guard = int(rate * guard_ms / 1000)
        end = min(end, max(onset + 1, next_onset - guard))
    clip = list(samples[start:end])

    fade_len = min(int(rate * fade_ms / 1000), len(clip) // 4)
    for i in range(fade_len):
        clip[-(i + 1)] *= i / fade_len
    return clip


def main():
    if len(sys.argv) < 3:
        print("usage: slice_clicks.py <input.wav> <out_dir> [prefix] [max_clips]")
        sys.exit(1)

    in_path = sys.argv[1]
    out_dir = sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else "click"
    max_clips = int(sys.argv[4]) if len(sys.argv) > 4 else 999

    samples, rate = read_wav_mono16(in_path)
    env = envelope(samples, rate)
    onsets, threshold = find_onsets(env, rate)

    print(f"{in_path}: {len(onsets)} onsets detected (threshold={threshold:.4f}, rate={rate})")
    os.makedirs(out_dir, exist_ok=True)

    for i, onset in enumerate(onsets[:max_clips]):
        next_onset = onsets[i + 1] if i + 1 < len(onsets) else None
        clip = slice_clip(samples, rate, onset, next_onset=next_onset)
        out_path = os.path.join(out_dir, f"{prefix}_{i}.wav")
        write_wav(out_path, clip, rate)
        t = onset / rate
        print(f"  onset {i}: t={t:.3f}s -> {out_path}")


if __name__ == "__main__":
    main()
