#!/usr/bin/env python3
"""Synthesize the Sit-up Tracker sound effects (no samples, all code).

Writes PhoneSDK/examples/situp-tracker/sounds-data.js: every sound as a small
MP3, embedded as base64. The page decodes them with Web Audio, so it needs no
network access (its security policy blocks fetch) and one tap unlocks them all.
Needs the MP3 encoder once:  py -m pip install lameenc
Then:  py GlassSDK/examples/situp_counter/tools/make_sounds.py
"""
import math
import random
import struct
from pathlib import Path

import lameenc

RATE = 16000
PLUGIN = Path(__file__).resolve().parents[4] / "PhoneSDK" / "examples" / "situp-tracker"
OUT_JS = PLUGIN / "sounds-data.js"
ENCODED = {}
rng = random.Random(1234)  # deterministic noise


def silence(sec):
    return [0.0] * int(sec * RATE)


def env(n, attack=0.005, release=0.08, sustain=1.0):
    """Linear attack, exponential-ish release over the tail."""
    a = max(1, int(attack * RATE))
    r = max(1, int(release * RATE))
    out = []
    for i in range(n):
        if i < a:
            v = i / a
        elif i > n - r:
            v = max(0.0, (n - i) / r) ** 2
        else:
            v = 1.0
        out.append(v * sustain)
    return out


def osc(kind, phase):
    p = phase % 1.0
    if kind == "sine":
        return math.sin(2 * math.pi * p)
    if kind == "square":
        return 1.0 if p < 0.5 else -1.0
    if kind == "tri":
        return 4 * abs(p - 0.5) - 1
    return 2 * p - 1  # saw


def tone(f0, sec, kind="sine", vol=0.5, f1=None, vib=0.0, vib_rate=6.0,
         attack=0.005, release=0.08, curve=1.0):
    n = int(sec * RATE)
    f1 = f0 if f1 is None else f1
    e = env(n, attack, release)
    out, ph = [], 0.0
    for i in range(n):
        t = i / max(1, n - 1)
        f = f0 + (f1 - f0) * (t ** curve)
        f *= 1 + vib * math.sin(2 * math.pi * vib_rate * i / RATE)
        ph += f / RATE
        out.append(osc(kind, ph) * vol * e[i])
    return out


def noise(sec, vol=0.5, lowpass=1.0, highpass=0.0, attack=0.005, release=0.1, am=0.0, am_rate=0.0):
    """White noise through one-pole low/high-pass filters (0..1 = cutoff-ish)."""
    n = int(sec * RATE)
    e = env(n, attack, release)
    out, lp, hp_prev, hp = [], 0.0, 0.0, 0.0
    for i in range(n):
        x = rng.uniform(-1, 1)
        lp += lowpass * (x - lp)
        y = lp
        if highpass > 0:
            hp = (1 - highpass) * (hp + y - hp_prev)
            hp_prev = y
            y = hp
        mod = 1.0 - am * (0.5 + 0.5 * math.sin(2 * math.pi * am_rate * i / RATE))
        out.append(y * vol * e[i] * mod)
    return out


def bandpass(sig, freq, q=4.0):
    """RBJ biquad band-pass."""
    w = 2 * math.pi * freq / RATE
    alpha = math.sin(w) / (2 * q)
    b0, b1, b2 = alpha, 0.0, -alpha
    a0, a1, a2 = 1 + alpha, -2 * math.cos(w), 1 - alpha
    x1 = x2 = y1 = y2 = 0.0
    out = []
    for x in sig:
        y = (b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x, y1, y
        out.append(y)
    return out


def mix(*parts):
    """Each part is (start_seconds, samples)."""
    length = max(int(s * RATE) + len(p) for s, p in parts)
    out = [0.0] * length
    for s, p in parts:
        o = int(s * RATE)
        for i, v in enumerate(p):
            out[o + i] += v
    return out


def seq(*parts):
    out = []
    for p in parts:
        out += p
    return out


def scale(sig, k):
    return [v * k for v in sig]


def note(name):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    semis = names[name[0]] + (1 if "#" in name else -1 if "b" in name[1:2] else 0)
    octave = int(name[-1])
    return 440.0 * 2 ** ((semis + (octave - 4) * 12) / 12)


def save(name, sig):
    # Match loudness (RMS) across sounds, without letting peaks clip.
    peak = max(1e-6, max(abs(v) for v in sig))
    rms = max(1e-6, math.sqrt(sum(v * v for v in sig) / len(sig)))
    k = min(0.89 / peak, 0.2 / rms)
    pcm = b"".join(struct.pack("<h", int(max(-1, min(1, v * k)) * 32767)) for v in sig)
    enc = lameenc.Encoder()
    enc.set_bit_rate(48)          # plenty for short sound effects
    enc.set_in_sample_rate(RATE)
    enc.set_channels(1)
    enc.set_quality(2)            # 2 = high quality encoding
    ENCODED[name] = bytes(enc.encode(pcm) + enc.flush())


# ------------------------------------------------------------ the sounds --

def meow(f_start, f_peak, f_end, sec, vol=0.6):
    """Saw glide through two sweeping formants: 'mee-ow'."""
    n = int(sec * RATE)
    src, ph = [], 0.0
    e = env(n, 0.03, 0.12)
    for i in range(n):
        t = i / n
        f = f_start + (f_peak - f_start) * min(1, t / 0.35) if t < 0.35 else \
            f_peak + (f_end - f_peak) * ((t - 0.35) / 0.65)
        ph += f / RATE
        src.append(osc("saw", ph) * e[i])
    a = bandpass(src, 1500, 3)
    b = bandpass(src, 900, 3)
    out = []
    for i in range(n):
        t = i / n
        out.append((a[i] * (1 - t) + b[i] * t) * vol * 3)
    return out


def purr(sec, vol=0.5):
    """Low rumble pulsing ~24 times a second."""
    rumble = noise(sec, 1.0, lowpass=0.08, am=0.9, am_rate=24, attack=0.05, release=0.15)
    return scale(bandpass(rumble, 140, 1.2), vol * 4)


def whistle(sec, vol=0.45):
    return tone(2900, sec, "sine", vol, vib=0.025, vib_rate=32, attack=0.01, release=0.03)


def snore():
    inhale = scale(bandpass(noise(0.7, 1, lowpass=0.2, attack=0.3, release=0.2), 300, 1.5), 3.0)
    rumble = tone(70, 0.7, "saw", 0.25, attack=0.3, release=0.2)
    exhale = scale(bandpass(noise(0.6, 1, lowpass=0.3, attack=0.05, release=0.4), 900, 2), 1.4)
    return seq(mix((0, inhale), (0, rumble)), silence(0.1), exhale)


def chord_arp(notes, step, sec, kind="square", vol=0.22):
    return mix(*[(i * step, tone(note(n), sec - i * step, kind, vol, release=0.25)) for i, n in enumerate(notes)])


def build():
    s = {}
    # Shared / Ring --------------------------------------------------------
    s["ding"] = mix((0, tone(1320, 0.5, "sine", 0.5, release=0.45)), (0, tone(2640, 0.3, "sine", 0.12, release=0.3)))
    s["blip"] = tone(660, 0.09, "sine", 0.5, f1=990, release=0.04)
    s["chime"] = chord_arp(["C6", "E6", "G6", "C7"], 0.09, 0.9, "sine", 0.35)
    s["down"] = seq(tone(523, 0.14, "tri", 0.45, release=0.05), tone(392, 0.25, "tri", 0.45, release=0.15))
    s["up"] = seq(tone(392, 0.12, "tri", 0.45, release=0.05), tone(523, 0.2, "tri", 0.45, release=0.12))
    # Coach Head -----------------------------------------------------------
    s["whistle"] = seq(whistle(0.12), silence(0.06), whistle(0.12), silence(0.06), whistle(0.45))
    s["whistle-short"] = whistle(0.25)
    s["hup"] = mix((0, scale(bandpass(noise(0.16, 1, lowpass=0.6, attack=0.005, release=0.1), 700, 1.5), 2.2)),
                   (0, tone(150, 0.16, "saw", 0.3, f1=120, release=0.1)))
    crowd = scale(bandpass(noise(1.4, 1, lowpass=0.7, attack=0.25, release=0.6), 1100, 0.8), 1.6)
    s["cheer"] = mix((0, crowd), (0.15, whistle(0.2, 0.25)), (0.5, whistle(0.3, 0.2)),
                     (0, chord_arp(["G5", "C6", "E6", "G6"], 0.08, 0.7, "square", 0.08)))
    s["snore"] = snore()
    # Sit-up Figure --------------------------------------------------------
    s["boing"] = tone(180, 0.45, "sine", 0.55, f1=520, vib=0.18, vib_rate=14, release=0.2, curve=0.5)
    s["boing-up"] = tone(250, 0.3, "sine", 0.5, f1=700, vib=0.12, vib_rate=18, release=0.15, curve=0.5)
    s["fanfare"] = seq(tone(note("G5"), 0.12, "square", 0.2), tone(note("G5"), 0.12, "square", 0.2),
                       tone(note("G5"), 0.12, "square", 0.2), tone(note("C6"), 0.5, "square", 0.22, release=0.3))
    # Glow-Up -------------------------------------------------------------
    s["power-on"] = mix((0, tone(110, 0.6, "saw", 0.25, f1=440, attack=0.05, release=0.15)),
                        (0.4, tone(880, 0.25, "sine", 0.3, release=0.2)))
    s["level"] = tone(note("A5"), 0.12, "square", 0.22, f1=note("E6"), release=0.06)
    for tier, notes in ((1, ["C5", "E5", "G5", "C6"]),
                        (2, ["C5", "E5", "G5", "C6", "E6", "G6"]),
                        (3, ["C5", "E5", "G5", "C6", "E6", "G6", "C7"])):
        arp = chord_arp(notes, 0.06, 0.6 + 0.08 * len(notes), "square", 0.16)
        if tier == 3:  # heavenly choir on top
            choir = mix(*[(0.35, tone(note(n), 1.6, "saw", 0.07, vib=0.006, vib_rate=5, attack=0.4, release=0.8))
                          for n in ("C4", "G4", "C5", "E5")])
            arp = mix((0, arp), (0, scale(bandpass(choir, 900, 0.7), 2.5)))
        s[f"power-{tier}"] = arp
    choir = mix(*[(0, tone(note(n), 1.5, "saw", 0.08, vib=0.006, vib_rate=5, attack=0.35, release=0.7))
                  for n in ("A3", "E4", "A4", "C#5", "E5")])
    s["choir"] = scale(bandpass(choir, 900, 0.7), 3.0)
    s["power-down"] = tone(440, 0.6, "saw", 0.25, f1=70, release=0.2, curve=0.6)
    # Aura ----------------------------------------------------------------
    s["shimmer"] = mix(*[(i * 0.045, tone(f, 0.35, "sine", 0.18, release=0.3))
                         for i, f in enumerate((1760, 2217, 2637, 3520, 2637, 3520))])
    s["sparkle"] = mix(*[(i * 0.035, tone(f, 0.22, "sine", 0.2, release=0.2))
                         for i, f in enumerate((2093, 2637, 3136, 4186))])
    boom = tone(90, 1.3, "sine", 0.9, f1=38, attack=0.002, release=1.0, curve=0.35)
    s["boom"] = [math.tanh(2.2 * v) for v in mix((0, boom), (0, noise(0.08, 0.5, lowpass=0.3, release=0.07)))]
    scratch = scale(bandpass(noise(0.35, 1, lowpass=0.9, attack=0.002, release=0.05), 1200, 1.0), 2.0)
    scratch = [v * (0.5 + 0.5 * math.sin(2 * math.pi * 9 * i / RATE)) for i, v in enumerate(scratch)]
    womp = [scale(bandpass(tone(note(n), d, "saw", 0.5, vib=v, vib_rate=7, attack=0.03, release=0.12), 700, 0.8), 2.2)
            for n, d, v in (("G3", 0.38, 0.0), ("F#3", 0.38, 0.0), ("F3", 0.38, 0.0), ("E3", 1.0, 0.03))]
    s["sad-trombone"] = seq(scratch, silence(0.12), *womp)
    # Judgy Cat -----------------------------------------------------------
    s["mrrp"] = meow(380, 620, 560, 0.3, 0.5)
    s["purr"] = purr(0.6)
    s["meow-happy"] = seq(meow(450, 900, 600, 0.55), purr(0.5, 0.35))
    s["hiss"] = scale(noise(0.8, 1, lowpass=1.0, highpass=0.6, attack=0.04, release=0.3), 0.7)
    # Stonks ----------------------------------------------------------------
    s["ticker"] = seq(*[seq(tone(1800, 0.05, "square", 0.15, release=0.02), silence(0.06)) for _ in range(3)])
    s["ka-ching"] = mix((0, noise(0.04, 0.6, lowpass=0.8, release=0.03)),
                        (0.03, tone(note("D6"), 0.15, "square", 0.12, release=0.08)),
                        (0.12, tone(2637, 0.6, "sine", 0.35, release=0.55)),
                        (0.12, tone(3951, 0.5, "sine", 0.18, release=0.45)))
    s["rocket"] = mix((0, scale(noise(1.4, 1, lowpass=0.25, attack=0.2, release=0.4), 0.9)),
                      (0, tone(200, 1.4, "saw", 0.12, f1=1600, attack=0.1, release=0.3, curve=2.0)),
                      (1.1, chord_arp(["C6", "G6", "C7"], 0.07, 0.6, "sine", 0.25)))
    s["crash"] = seq(tone(1800, 0.7, "sine", 0.35, f1=250, release=0.05, curve=0.7),
                     [math.tanh(2 * v) for v in mix((0, tone(70, 0.6, "sine", 0.9, f1=35, release=0.5)),
                                                    (0, noise(0.35, 0.6, lowpass=0.2, release=0.3)))])
    s["rolled"] = rolled()
    return s


def rolled():
    """Roll prank sting: an original, cheesy 80s synth-pop jingle (own melody
    and arrangement): drum machine, octave-bouncing bass, chord stabs, lead,
    and a "ta-da" at the end. 2 bars at 120 bpm in D major."""
    beat = 0.5
    parts = []
    # drums: kick on 1 and 3, snare on 2 and 4, closed hats on eighths
    for b in range(8):
        t = b * beat
        if b % 2 == 0:
            parts.append((t, tone(110, 0.18, "sine", 0.9, f1=45, release=0.15, curve=0.4)))
        else:
            parts.append((t, scale(bandpass(noise(0.16, 1, lowpass=0.9, release=0.12), 1800, 0.9), 2.2)))
        for h in (0, 0.25):
            parts.append((t + h, scale(noise(0.03, 0.5, lowpass=1.0, highpass=0.7, release=0.025), 0.6)))
    # progression D - Bm - G - A, two beats each; bass bounces root/octave in eighths
    chords = [("D3", ["D4", "F#4", "A4"]), ("B2", ["B3", "D4", "F#4"]),
              ("G2", ["G3", "B3", "D4"]), ("A2", ["A3", "C#4", "E4"])]
    for c, (root, triad) in enumerate(chords):
        base = note(root)
        for e in range(4):
            f = base * (2 if e % 2 else 1)
            parts.append((c * 2 * beat + e * beat / 2,
                          scale(bandpass(tone(f, beat / 2 * 0.9, "saw", 0.5, release=0.05), 400, 0.7), 2.0)))
        for st in (0.5, 1.5):  # off-beat stabs
            stab = mix(*[(0, tone(note(n), 0.16, "saw", 0.12, release=0.08)) for n in triad])
            parts.append((c * 2 * beat + st * beat, scale(bandpass(stab, 1500, 0.6), 2.0)))
    # lead melody (original): a bouncy hook that climbs, then lands home
    lead = [("F#5", 0, 0.5), ("A5", 0.5, 0.5), ("B5", 1, 0.75), ("A5", 1.75, 0.25),
            ("F#5", 2, 0.5), ("D5", 2.5, 0.5), ("E5", 3, 1.0),
            ("G5", 4, 0.5), ("F#5", 4.5, 0.5), ("E5", 5, 0.5), ("D5", 5.5, 0.5),
            ("E5", 6, 0.75), ("F#5", 6.75, 0.25), ("A5", 7, 1.0)]
    for n, start, dur in lead:
        parts.append((start * beat, tone(note(n), dur * beat * 0.95, "square", 0.13,
                                         vib=0.004, vib_rate=6, attack=0.01, release=0.06)))
    # ta-da: big D major chord with a sparkle on top
    tada_at = 8 * beat
    chord = mix(*[(0, tone(note(n), 1.1, "saw", 0.1, attack=0.01, release=0.8))
                  for n in ("D3", "A3", "D4", "F#4", "A4", "D5")])
    parts.append((tada_at, scale(bandpass(chord, 1200, 0.5), 2.6)))
    parts.append((tada_at, tone(110, 0.3, "sine", 0.9, f1=40, release=0.25, curve=0.4)))
    parts.append((tada_at, scale(noise(0.6, 0.5, lowpass=1.0, highpass=0.6, release=0.55), 0.5)))
    for i, f in enumerate((2349, 2960, 3520, 4699)):
        parts.append((tada_at + 0.05 + i * 0.06, tone(f, 0.3, "sine", 0.12, release=0.28)))
    return mix(*parts)


if __name__ == "__main__":
    import base64
    sounds = build()
    for name, sig in sounds.items():
        save(name, sig)
        print(f"  {name:14s} {len(sig) / RATE:4.2f}s  {len(ENCODED[name]) / 1024:5.1f} KB")
    lines = ["// Generated by GlassSDK/examples/situp_counter/tools/make_sounds.py - do not edit.",
             "// Every sound effect as a base64 MP3 (decoded with Web Audio in sounds.js).",
             "export const SOUND_DATA = {"]
    for name, data in ENCODED.items():
        lines.append(f"  '{name}': '{base64.b64encode(data).decode()}',")
    lines.append("};")
    OUT_JS.write_text("\n".join(lines) + "\n")
    print(f"wrote {len(sounds)} sounds, {OUT_JS.stat().st_size // 1024} KB, to {OUT_JS}")
