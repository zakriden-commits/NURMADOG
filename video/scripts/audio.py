"""Sound design: synthesised trap-ish bed + all the whooshes/punches/stamps, ducked under the VO."""
import json
import os
import subprocess
import numpy as np
from scipy import signal as sg
import imageio_ffmpeg

import plan

HERE = plan.HERE
SR = 48000
FF = imageio_ffmpeg.get_ffmpeg_exe()
N = int(SR * (plan.TOTAL + 1.0))
rng = np.random.default_rng(7)


def zeros():
    return np.zeros((2, N), np.float32)


def add(buf, sig, t, gain=1.0, pan=0.0):
    """pan -1..1"""
    if sig is None or len(sig) == 0:
        return
    i = int(t * SR)
    if i >= N:
        return
    if i < 0:
        sig = sig[-i:]
        i = 0
    n = min(len(sig), N - i)
    gl = gain * np.sqrt((1 - pan) / 2) * 1.414
    gr = gain * np.sqrt((1 + pan) / 2) * 1.414
    buf[0, i:i + n] += sig[:n] * gl
    buf[1, i:i + n] += sig[:n] * gr


def env(n, a=0.002, d=0.2, curve=2.0):
    t = np.arange(n) / SR
    atk = np.clip(t / max(a, 1e-5), 0, 1)
    dec = np.exp(-t / max(d, 1e-5) * curve)
    return (atk * dec).astype(np.float32)


def sine(f, n, phase=0.0):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t + phase).astype(np.float32)


def sweep(f0, f1, n, expo=True):
    t = np.arange(n) / SR
    k = np.geomspace(f0, f1, n) if expo else np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(k) / SR).astype(np.float32)


def noise(n):
    return rng.standard_normal(n).astype(np.float32) * 0.5


def lp(x, fc, order=2):
    sos = sg.butter(order, min(fc / (SR / 2), 0.99), "low", output="sos")
    return sg.sosfilt(sos, x).astype(np.float32)


def hp(x, fc, order=2):
    sos = sg.butter(order, min(fc / (SR / 2), 0.99), "high", output="sos")
    return sg.sosfilt(sos, x).astype(np.float32)


def bp(x, f0, f1, order=2):
    sos = sg.butter(order, [min(f0 / (SR / 2), 0.98), min(f1 / (SR / 2), 0.99)], "band", output="sos")
    return sg.sosfilt(sos, x).astype(np.float32)


# ------------------------------------------------------------------ instruments
def kick(dur=0.5, f0=150, f1=44, click=0.5):
    n = int(SR * dur)
    body = sweep(f0, f1, n) * env(n, 0.001, dur * 0.35, 2.4)
    clk = hp(noise(int(SR * 0.012)), 2500) * np.linspace(1, 0, int(SR * 0.012)) * click
    out = body * 1.0
    out[:len(clk)] += clk
    return lp(out, 9000) * 0.9


def sub808(dur=1.0, f0=95, f1=34):
    n = int(SR * dur)
    s = sweep(f0, f1, n) * env(n, 0.002, dur * 0.45, 1.8)
    return np.tanh(s * 1.6) * 0.75


def snare(dur=0.22):
    n = int(SR * dur)
    nz = bp(noise(n), 900, 7000) * env(n, 0.001, dur * 0.22, 1.6)
    tone = sine(190, n) * env(n, 0.001, dur * 0.1, 2.0) * 0.4
    return (nz * 0.55 + tone) * 0.8


def hat(dur=0.06, open_=False):
    d = dur * (5 if open_ else 1)
    n = int(SR * d)
    return hp(noise(n), 7000, 4) * env(n, 0.0005, d * 0.3, 2.2) * 0.22


def pad(freqs, dur, cutoff=1400, detune=0.006, attack=0.4):
    n = int(SR * dur)
    out = np.zeros(n, np.float32)
    for f in freqs:
        for k in (-1, 0, 1):
            ph = rng.uniform(0, 6.28)
            saw = sg.sawtooth(2 * np.pi * (f * (1 + k * detune)) * np.arange(n) / SR + ph)
            out += saw.astype(np.float32) / (len(freqs) * 3)
    out = lp(out, cutoff)
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-3), 0, 1) ** 1.5
    r = np.clip((dur - t) / 0.25, 0, 1)
    return (out * a * r).astype(np.float32)


# ------------------------------------------------------------------ sfx
def sfx_punch(g=1.0):
    n = int(SR * 0.18)
    thump = sweep(120, 48, n) * env(n, 0.001, 0.05, 2.5)
    smack = bp(noise(n), 700, 5200) * env(n, 0.0005, 0.035, 2.0) * 0.8
    return (thump * 1.1 + smack) * g


def sfx_stamp(g=1.0):
    n = int(SR * 0.55)
    thump = sweep(105, 40, n) * env(n, 0.001, 0.16, 2.2)
    metal = bp(noise(n), 1400, 6500) * env(n, 0.0005, 0.05, 1.6) * 0.6
    ring = (sine(640, n) * 0.25 + sine(970, n) * 0.18) * env(n, 0.004, 0.14, 1.6)
    return (thump + metal + ring) * g


def sfx_whoosh(dur=0.5, up=True):
    n = int(SR * dur)
    x = noise(n)
    fc = np.linspace(400, 5200, n) if up else np.linspace(5200, 400, n)
    out = np.zeros(n, np.float32)
    # cheap time-varying bandpass via block processing
    blk = 1024
    for i in range(0, n - blk, blk):
        c = fc[i]
        out[i:i + blk] = bp(x[i:i + blk], c * 0.6, min(c * 1.7, 20000))
    t = np.arange(n) / SR
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return (out * e * 1.6).astype(np.float32)


def sfx_riser(dur=1.2, g=1.0):
    n = int(SR * dur)
    x = noise(n)
    out = np.zeros(n, np.float32)
    blk = 1024
    for i in range(0, n - blk, blk):
        c = 300 + 6000 * (i / n) ** 2
        out[i:i + blk] = bp(x[i:i + blk], c * 0.7, min(c * 1.6, 20000))
    t = np.arange(n) / SR
    tone = sweep(180, 900, n) * 0.25
    e = (t / dur) ** 2.2
    return ((out * 1.5 + tone) * e * g).astype(np.float32)


def sfx_glitch(dur=0.4, g=1.0):
    n = int(SR * dur)
    x = noise(n)
    hold = 24
    sq = np.repeat(x[::hold], hold)[:n]  # sample-and-hold crush
    sq = hp(sq, 200, 2)
    gate = (rng.random(n // 1200 + 1) > 0.4).astype(np.float32)
    g2 = np.repeat(gate, 1200)[:n]
    t = np.arange(n) / SR
    return (sq * g2 * np.linspace(1, 0.2, n) * g * 0.9).astype(np.float32)


def sfx_blip(f=1180, dur=0.13, g=1.0):
    n = int(SR * dur)
    s = (sine(f, n) * 0.7 + sine(f * 2.01, n) * 0.3) * env(n, 0.001, dur * 0.3, 2.4)
    return (s * g).astype(np.float32)


def sfx_boom(g=1.0):
    n = int(SR * 1.3)
    s = sub808(1.3, 110, 30) * 1.0
    crack = bp(noise(n), 250, 3000) * env(n, 0.001, 0.12, 2.0) * 0.5
    return ((s + crack) * g).astype(np.float32)


def sfx_ui_pop(g=1.0):
    n = int(SR * 0.2)
    s = sweep(600, 1400, n) * env(n, 0.001, 0.05, 2.0)
    return (s * g).astype(np.float32)


# ------------------------------------------------------------------ build
music = zeros()
drums = zeros()

BPM = 140.0
b = 60.0 / BPM
T0 = 4.95
end = plan.TOTAL - 0.35

# --- pad / drone bed (whole clip, chord shifts per scene)
chords = [(0.00, 4.95, [55.0, 110.0, 164.8, 220.0], 900),
          (4.95, 10.76, [55.0, 110.0, 130.8, 196.0], 1500),
          (10.76, 16.55, [55.0, 110.0, 146.8, 196.0], 1700),
          (16.55, 21.55, [49.0, 98.0, 138.6, 174.6], 1200),
          (21.55, 26.02, [55.0, 110.0, 130.8, 220.0], 2000),
          (26.02, plan.TOTAL, [55.0, 110.0, 164.8, 261.6], 2400)]
for a, bb, fr, cut in chords:
    add(music, pad(fr, bb - a + 0.35, cutoff=cut, attack=0.35), a, 0.55)

# --- drums
t = T0
bar = 0
while t < end:
    for step in range(8):
        ts = t + step * b / 2
        if ts >= end:
            break
        if step in (0, 3, 6):
            add(drums, kick(), ts, 0.95 if step == 0 else 0.75)
            add(music, sub808(0.9), ts, 0.55)
        if step in (4,):
            add(drums, snare(), ts, 0.7)
        if step == 7:
            add(drums, snare(0.3), ts, 0.35)
        # hats
        vel = 0.9 if step % 2 == 0 else 0.55
        add(drums, hat(0.045, open_=(step == 5)), ts, vel, pan=0.15)
        add(drums, hat(0.03), ts + b / 4, 0.25, pan=-0.2)
    t += 4 * b
    bar += 1

# hook section: sparse hats + heartbeat kicks
th = 1.05
while th < T0 - 0.05:
    add(drums, hat(0.04), th, 0.5, pan=0.1)
    th += b / 2

# --- beat-driven SFX layer
for tt, kind, g in plan.BEATS:
    if kind == "punch":
        add(drums, sfx_punch(), tt, 0.85 * g)
    elif kind == "stamp":
        add(drums, sfx_stamp(), tt, 0.75 * g)
    elif kind == "whoosh":
        add(music, sfx_whoosh(0.45), tt - 0.22, 0.5 * g, pan=-0.25)
    elif kind == "riser":
        add(music, sfx_riser(0.9, g), tt - 0.85, 0.42, pan=0.2)
    elif kind == "glitch":
        add(drums, sfx_glitch(0.42, g), tt, 0.5, pan=-0.3)
    elif kind == "blip":
        add(drums, sfx_blip(1100 + 300 * g, 0.12, g), tt, 0.34, pan=0.3)
    elif kind == "bass":
        add(music, sfx_boom(g), tt - 0.02, 0.9, pan=0.0)

# extra UI pops for the CTA buttons
add(drums, sfx_ui_pop(0.8), 27.42, 0.4, pan=-0.35)
add(drums, sfx_ui_pop(0.8), 27.55, 0.35, pan=0.35)

# --- music dropout right before the VS reveal for impact
def gate(buf, a, b, fade=0.12):
    i0, i1 = int(a * SR), int(b * SR)
    f = int(fade * SR)
    ramp = np.linspace(0, 1, f, dtype=np.float32)
    buf[:, i0 - f:i0] *= ramp
    buf[:, i0:i1] *= 0.02
    buf[:, i1:i1 + f] *= ramp[::-1]
    buf[:, i1 + f:] *= 1.0


gate(music, 21.30, 21.62, 0.1)
gate(drums, 21.30, 21.62, 0.1)

# ------------------------------------------------------------------ voice
voice = np.fromfile(os.path.join(HERE, "audio", "voice_raw.f32"), dtype=np.float32)[:N]
if len(voice) < N:
    voice = np.pad(voice, (0, N - len(voice)))

# duck the bed under the voice
envv = np.abs(voice)
k = int(SR * 0.15)
envv = np.convolve(envv, np.ones(k) / k, mode="same")
duck = 1.0 - 0.55 * np.clip(envv / 0.12, 0, 1)
duck = np.convolve(duck, np.ones(int(SR * 0.08)) / int(SR * 0.08), mode="same").astype(np.float32)
music *= duck
drums *= duck * 0.92

# ------------------------------------------------------------------ master
mixl = voice * 0.95 + music[0] * 0.62 + drums[0] * 0.62
mixr = voice * 0.95 + music[1] * 0.62 + drums[1] * 0.62
mix = np.stack([mixl, mixr], 0)

# gentle glue + limiter
mix = np.tanh(mix * 1.05) * 0.92
peak = np.abs(mix).max()
mix = mix / max(peak, 1e-6) * 0.95

# fade out the very end
f = int(0.45 * SR)
mix[:, -f:] *= np.linspace(1, 0, f, dtype=np.float32) ** 0.7

mix16 = (np.clip(mix.T, -1, 1) * 32767).astype("<i2")
raw = os.path.join(HERE, "audio", "mix_raw.wav")
import wave
with wave.open(raw, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(mix16.tobytes())

# loudness-normalise for social platforms
out = os.path.join(HERE, "audio", "mix.wav")
subprocess.run([FF, "-v", "quiet", "-y", "-i", raw, "-af",
                "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-ar", "48000", out], check=True)
print("wrote", out, round(plan.TOTAL, 2), "s")
