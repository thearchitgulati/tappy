#!/usr/bin/env python3
"""Build all 6 sound packs from real, freesound.org-licensed recordings.
Reproduces the full pipeline used to get from "bad synthesized clicks" to
the shipped packs: download -> slice onsets -> filter weak/outlier onsets
by peak percentile -> normalize volume -> assemble per pack. See
SOUND_CREDITS.md for the license of every source used here.

Run: python3 Scripts/assemble_freesound_packs.py
Requires network access (freesound.org's CDN) and `afconvert` (macOS).
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from gen_click import make_pop  # noqa: E402
from pick_and_normalize import (  # noqa: E402
    build_pack_clicks, slice_all, pick_well_spaced, normalize_clip, write_wav,
)
from slice_clicks import read_wav_mono16  # noqa: E402

SOUNDS_DIR = os.path.join(os.path.dirname(__file__), "..", "Sources", "Tappy", "Resources", "sounds")

# name -> (freesound CDN preview URL, license)
SOURCES = {
    "feedbackdesignz":  "https://cdn.freesound.org/previews/245/245716_3601976-hq.mp3",     # CC0
    "getwecked":        "https://cdn.freesound.org/previews/764/764661_16538157-hq.mp3",    # CC0
    "kfrance100":       "https://cdn.freesound.org/previews/381/381229_7080438-hq.mp3",     # CC0
    "khenshom_macbook": "https://cdn.freesound.org/previews/565/565645_6652872-hq.mp3",     # CC0
    "cherry_mx_blue":   "https://cdn.freesound.org/previews/400/400699_6081465-hq.mp3",     # CC0
    "computer_key1":    "https://cdn.freesound.org/previews/380/380142_3249786-hq.mp3",     # CC0
    "computer_key2":    "https://cdn.freesound.org/previews/380/380141_3249786-hq.mp3",     # CC0
    "computer_key3":    "https://cdn.freesound.org/previews/380/380140_3249786-hq.mp3",     # CC0
    "computer_key4":    "https://cdn.freesound.org/previews/380/380139_3249786-hq.mp3",     # CC0
    "computer_space6":  "https://cdn.freesound.org/previews/380/380144_3249786-hq.mp3",     # CC0
    "computer_space7":  "https://cdn.freesound.org/previews/380/380143_3249786-hq.mp3",     # CC0
    "typewriter_key1":  "https://cdn.freesound.org/previews/380/380138_3249786-hq.mp3",     # CC0
    "typewriter_key2":  "https://cdn.freesound.org/previews/380/380137_3249786-hq.mp3",     # CC0
    "typewriter_key3":  "https://cdn.freesound.org/previews/380/380136_3249786-hq.mp3",     # CC0
    "typewriter_old":   "https://cdn.freesound.org/previews/380/380133_3249786-hq.mp3",     # CC0
    "alpinemesh_enter": "https://cdn.freesound.org/previews/627/627647_13684433-hq.mp3",    # CC0
    "keychron_space":   "https://cdn.freesound.org/previews/789/789630_5287430-hq.mp3",     # CC0
    "sadiquecat_delete":"https://cdn.freesound.org/previews/799/799115_5287430-hq.mp3",     # CC0
    "sadiquecat_enter": "https://cdn.freesound.org/previews/799/799116_5287430-hq.mp3",     # CC0
    "ramsamba_carriage":"https://cdn.freesound.org/previews/318/318686_1147663-hq.mp3",     # CC0
    "magedu_typewriter_space": "https://cdn.freesound.org/previews/277/277299_4877562-hq.mp3",  # CC-BY 4.0 -- attribution required, see SOUND_CREDITS.md
}


def download_and_convert(url, out_wav):
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_mp3 = tmp.name
    subprocess.run(["curl", "-sL", url, "-o", tmp_mp3], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@44100", "-c", "1", tmp_mp3, out_wav], check=True)
    os.remove(tmp_mp3)


def loudest_onset_clip(wav_path):
    clips, rate = slice_all(wav_path)
    return max(clips, key=lambda c: c[2]), rate


def pick_big_keys(wav_path, n=2):
    """Best-effort pick of the physically larger keys (space/enter) from a
    continuous typing recording: the loudest onsets tend to be the bigger
    keycaps, skipping the single loudest as it's often a one-off spike
    unrelated to normal keystrokes. Not verified per-key ground truth --
    guarantees same-keyboard material, not which literal key was hit."""
    clips, rate = slice_all(wav_path)
    ranked = sorted(clips, key=lambda c: -c[2])
    return ranked[1:1 + n], rate


def add_confirm_chimes(pack_dir):
    make_pop(os.path.join(pack_dir, "confirm_copy.wav"),
             freq_start=600, freq_end=950, duration=0.26, decay=9, transient_amount=0.28)
    make_pop(os.path.join(pack_dir, "confirm_paste.wav"),
             freq_start=950, freq_end=560, duration=0.3, decay=8, transient_amount=0.25, thud=True)


def main():
    work_dir = tempfile.mkdtemp(prefix="freesound_")
    wavs = {}
    for name, url in SOURCES.items():
        out_wav = os.path.join(work_dir, f"{name}.wav")
        print(f"Downloading + converting {name}...")
        download_and_convert(url, out_wav)
        wavs[name] = out_wav

    # Shared Delete sample (used by Gaming Click, Logitech Typing, Cherry MX
    # Blue): the brighter of the two onsets in Sadiquecat's FUJITSU Delete
    # recording -- the first onset is almost entirely bass and reads as a
    # boomy thud rather than a click.
    fujitsu_clips, fujitsu_rate = slice_all(wavs["sadiquecat_delete"])
    shared_delete_clip = normalize_clip(fujitsu_clips[1][1], target_peak=0.6, max_gain=8.0)

    def write_shared_delete(pack_dir):
        write_wav(os.path.join(pack_dir, "delete_down_0.wav"), shared_delete_clip, fujitsu_rate)

    # --- Gaming Click ---
    pack_dir = os.path.join(SOUNDS_DIR, "Gaming Click")
    os.makedirs(pack_dir, exist_ok=True)
    n = build_pack_clicks(wavs["feedbackdesignz"], pack_dir, "click_down", 6, low_pct=40, high_pct=95, target_peak=0.65)
    clip, rate = loudest_onset_clip(wavs["getwecked"])
    write_wav(os.path.join(pack_dir, f"click_down_{n}.wav"), normalize_clip(clip[1], target_peak=0.65), rate)
    clip, rate = loudest_onset_clip(wavs["keychron_space"])
    write_wav(os.path.join(pack_dir, "space_down_0.wav"), normalize_clip(clip[1], target_peak=0.6, max_gain=8.0), rate)
    clip, rate = loudest_onset_clip(wavs["alpinemesh_enter"])
    write_wav(os.path.join(pack_dir, "enter_down_0.wav"), normalize_clip(clip[1], target_peak=0.6, max_gain=8.0), rate)
    write_shared_delete(pack_dir)
    add_confirm_chimes(pack_dir)
    print("Gaming Click: done")

    # --- Logitech Typing ---
    pack_dir = os.path.join(SOUNDS_DIR, "Logitech Typing")
    os.makedirs(pack_dir, exist_ok=True)
    build_pack_clicks(wavs["kfrance100"], pack_dir, "click_down", 8, low_pct=55, high_pct=93, target_peak=0.65)
    big_keys, rate = pick_big_keys(wavs["kfrance100"], n=2)
    for label, (t, clip, peak) in zip(["space", "enter"], big_keys):
        write_wav(os.path.join(pack_dir, f"{label}_down_0.wav"), normalize_clip(clip, target_peak=0.6, max_gain=6.0), rate)
    write_shared_delete(pack_dir)
    add_confirm_chimes(pack_dir)
    print("Logitech Typing: done")

    # --- Computer Keyboard ---
    pack_dir = os.path.join(SOUNDS_DIR, "Computer Keyboard")
    os.makedirs(pack_dir, exist_ok=True)
    for i, key in enumerate(["computer_key1", "computer_key2", "computer_key3", "computer_key4"]):
        clip, rate = loudest_onset_clip(wavs[key])
        write_wav(os.path.join(pack_dir, f"click_down_{i}.wav"), normalize_clip(clip[1], target_peak=0.65), rate)
    for i, key in enumerate(["computer_space6", "computer_space7"]):
        clip, rate = loudest_onset_clip(wavs[key])
        write_wav(os.path.join(pack_dir, f"space_down_{i}.wav"), normalize_clip(clip[1], target_peak=0.6, max_gain=8.0), rate)
    clip, rate = loudest_onset_clip(wavs["sadiquecat_enter"])
    write_wav(os.path.join(pack_dir, "enter_down_0.wav"), normalize_clip(clip[1], target_peak=0.6, max_gain=8.0), rate)
    write_shared_delete(pack_dir)  # same FUJITSU keyboard as its own Enter sample
    add_confirm_chimes(pack_dir)
    print("Computer Keyboard: done")

    # --- Typewriter ---
    pack_dir = os.path.join(SOUNDS_DIR, "Typewriter")
    os.makedirs(pack_dir, exist_ok=True)
    for i, key in enumerate(["typewriter_key1", "typewriter_key2", "typewriter_key3"]):
        clip, rate = loudest_onset_clip(wavs[key])
        write_wav(os.path.join(pack_dir, f"click_down_{i}.wav"), normalize_clip(clip[1], target_peak=0.6), rate)
    build_pack_clicks(wavs["typewriter_old"], pack_dir, "click_down_extra", 5, low_pct=40, high_pct=95, target_peak=0.6)
    extras = sorted(glob.glob(os.path.join(pack_dir, "click_down_extra_*.wav")))
    for i, f in enumerate(extras):
        os.rename(f, os.path.join(pack_dir, f"click_down_{3 + i}.wav"))
    clip, rate = loudest_onset_clip(wavs["magedu_typewriter_space"])
    write_wav(os.path.join(pack_dir, "space_down_0.wav"), normalize_clip(clip[1], target_peak=0.6, max_gain=8.0), rate)
    # Carriage return used at full length, not windowed to ~90ms -- it's a
    # longer mechanical action than a single key click.
    samples, rate = read_wav_mono16(wavs["ramsamba_carriage"])
    write_wav(os.path.join(pack_dir, "enter_down_0.wav"), normalize_clip(list(samples), target_peak=0.55, max_gain=6.0), rate)
    # No Delete: most manual typewriters had no backspace key -- falls back
    # to the regular click sound rather than a mismatched modern sample.
    add_confirm_chimes(pack_dir)
    print("Typewriter: done")

    # --- Apple MacBook ---
    pack_dir = os.path.join(SOUNDS_DIR, "Apple MacBook")
    os.makedirs(pack_dir, exist_ok=True)
    build_pack_clicks(wavs["khenshom_macbook"], pack_dir, "click_down", 8, low_pct=60, high_pct=92, target_peak=0.65)
    big_keys, rate = pick_big_keys(wavs["khenshom_macbook"], n=2)
    for label, (t, clip, peak) in zip(["space", "enter"], big_keys):
        write_wav(os.path.join(pack_dir, f"{label}_down_0.wav"), normalize_clip(clip, target_peak=0.6, max_gain=6.0), rate)
    # Delete: another same-recording onset (not a big-key spike) -- the
    # shared FUJITSU Delete clashed badly with this pack's softer,
    # scissor-switch character, so it's sourced from its own keyboard too.
    all_clips, rate = slice_all(wavs["khenshom_macbook"])
    picked = pick_well_spaced(all_clips, 9, low_pct=60, high_pct=92)
    write_wav(os.path.join(pack_dir, "delete_down_0.wav"), normalize_clip(picked[-1][1], target_peak=0.5, max_gain=6.0), rate)
    add_confirm_chimes(pack_dir)
    print("Apple MacBook: done")

    # --- Cherry MX Blue ---
    pack_dir = os.path.join(SOUNDS_DIR, "Cherry MX Blue")
    os.makedirs(pack_dir, exist_ok=True)
    build_pack_clicks(wavs["cherry_mx_blue"], pack_dir, "click_down", 8, low_pct=50, high_pct=93, target_peak=0.65)
    big_keys, rate = pick_big_keys(wavs["cherry_mx_blue"], n=2)
    for label, (t, clip, peak) in zip(["space", "enter"], big_keys):
        write_wav(os.path.join(pack_dir, f"{label}_down_0.wav"), normalize_clip(clip, target_peak=0.6, max_gain=6.0), rate)
    write_shared_delete(pack_dir)
    add_confirm_chimes(pack_dir)
    print("Cherry MX Blue: done")

    shutil.rmtree(work_dir, ignore_errors=True)
    print("\nAll 6 packs assembled. See SOUND_CREDITS.md for full source/license details.")


if __name__ == "__main__":
    main()
