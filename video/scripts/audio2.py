"""Sound design v2 — voice + soft cinematic SFX, NO music (the user drops their own track on top)."""
import os
import subprocess
import wave
import numpy as np
from scipy import signal as sg
import imageio_ffmpeg

import plan2 as plan

HERE = plan.HERE
SR = 48000
FF = imageio_ffmpeg.get_ffmpeg_exe()
N = int(SR * (plan.TOTAL + 1.0))
rng = np.random.default_rng(3)


def zeros():
    return np.zeros((2, N), np.float32)


def add(buf, sig, t, gain=1.0, pan=0.0):
    if sig is None or len(sig) == 0:
        return
    i = int(t * SR)
    if i < 0:
        sig = sig[-i:]
        i = 0
    if i >= N:
        return
    n = min(len(sig), N - i)
    gl = gain * np.sqrt((1 - pan) / 2) * 1.414
    gr = gain * np.sqrt((1 + pan) / 2) * 1.414
    buf[0, i:i + n] += sig[:n] * gl
    buf[1, i:i + n] += sig[:n] * gr


def noise(n):
    return rng.standard_normal(n).astype(np.float32) * 0.5


def sweep(f0, f1, n, expo=True):
    k = np.geomspace(f0, f1, n) if expo else np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(k) / SR).astype(np.float32)


def bp(x, f0, f1, order=2):
    sos = sg.butter(order, [min(f0 / (SR / 2), 0.97), min(f1 / (SR / 2), 0.99)], "band", output="sos")
    return sg.sosfilt(sos, x).astype(np.float32)


def lp(x, fc, order=2):
    sos = sg.butter(order, min(fc / (SR / 2), 0.99), "low", output="sos")
    return sg.sosfilt(sos, x).astype(np.float32)


def hp(x, fc, order=2):
    sos = sg.butter(order, min(fc / (SR / 2), 0.99), "high", output="sos")
    return sg.sosfilt(sos, x).astype(np.float32)


def env_ad(n, a=0.01, d=0.3, curve=2.0):
    t = np.arange(n) / SR
    return (np.clip(t / max(a, 1e-4), 0, 1) * np.exp(-t / max(d, 1e-4) * curve)).astype(np.float32)


# ------------------------------------------------------------------ SFX
def sfx_air(dur=1.1, g=1.0):
    """smooth airy swoosh — the main transition sound"""
    n = int(SR * dur)
    x = noise(n)
    out = np.zeros(n, np.float32)
    blk = 1024
    for i in range(0, n - blk, blk):
        k = i / n
        c = 240 + 3600 * k ** 1.6
        out[i:i + blk] = bp(x[i:i + blk], c * 0.5, min(c * 2.2, 19000))
    t = np.arange(n) / SR
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2.4
    return (out * e * 1.25 * g).astype(np.float32)


def sfx_impact(dur=1.1, g=1.0, f0=78, f1=34):
    """soft cinematic low hit with air tail"""
    n = int(SR * dur)
    body = sweep(f0, f1, n) * env_ad(n, 0.004, dur * 0.28, 1.5)
    click = bp(noise(int(SR * 0.05)), 900, 6000) * env_ad(int(SR * 0.05), 0.0005, 0.02, 2.2) * 0.35
    tail = lp(noise(n), 2200) * env_ad(n, 0.02, dur * 0.5, 1.2) * 0.10
    out = body * 0.95
    out[:len(click)] += click
    out += tail
    return np.tanh(out * 1.2) * 0.9 * g


def sfx_tick(dur=0.16, g=1.0, f=2100):
    n = int(SR * dur)
    s = (np.sin(2 * np.pi * f * np.arange(n) / SR) * 0.5 +
         np.sin(2 * np.pi * f * 1.51 * np.arange(n) / SR) * 0.28)
    s = s * env_ad(n, 0.001, dur * 0.25, 2.6)
    air = hp(noise(n), 7000) * env_ad(n, 0.001, 0.02, 2.0) * 0.2
    return ((s + air) * 0.7 * g).astype(np.float32)


def sfx_swell(dur=1.4, g=1.0):
    n = int(SR * dur)
    x = noise(n)
    out = np.zeros(n, np.float32)
    blk = 1024
    for i in range(0, n - blk, blk):
        c = 500 + 2200 * (i / n)
        out[i:i + blk] = bp(x[i:i + blk], c * 0.6, min(c * 2.0, 18000))
    t = np.arange(n) / SR
    e = (t / dur) ** 2.0 * np.clip((dur - t) / 0.25, 0, 1)
    return (out * e * 1.0 * g).astype(np.float32)


def sfx_riser(dur=1.6, g=1.0):
    n = int(SR * dur)
    x = noise(n)
    out = np.zeros(n, np.float32)
    blk = 1024
    for i in range(0, n - blk, blk):
        c = 400 + 5200 * (i / n) ** 2
        out[i:i + blk] = bp(x[i:i + blk], c * 0.6, min(c * 1.9, 19000))
    t = np.arange(n) / SR
    tone = sweep(120, 620, n) * 0.18
    e = (t / dur) ** 2.4
    return ((out * 1.05 + tone) * e * g).astype(np.float32)


def sfx_shimmer(dur=1.6, g=1.0):
    n = int(SR * dur)
    x = hp(noise(n), 6000, 3)
    t = np.arange(n) / SR
    e = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    bell = (np.sin(2 * np.pi * 1760 * t) * 0.2 + np.sin(2 * np.pi * 2640 * t) * 0.12) * e
    return ((x * e * 0.5 + bell) * g).astype(np.float32)


# ------------------------------------------------------------------ build
sfx = zeros()
for tt, kind, g in plan.BEATS:
    pan = 0.25 if int(tt * 10) % 2 else -0.25
    if kind == "air":
        add(sfx, sfx_air(1.15, g), tt - 0.55, 0.55, pan * 0.6)
    elif kind == "impact":
        add(sfx, sfx_impact(1.0, g), tt - 0.02, 0.8, 0.0)
    elif kind == "tick":
        add(sfx, sfx_tick(0.15, g), tt, 0.4, pan)
    elif kind == "swell":
        add(sfx, sfx_swell(1.4, g), tt - 1.1, 0.5, pan)
    elif kind == "riser":
        add(sfx, sfx_riser(1.5, g), tt - 1.45, 0.5, pan * 0.4)
    elif kind == "shimmer":
        add(sfx, sfx_shimmer(1.5, g), tt - 0.3, 0.4, pan)

# ------------------------------------------------------------------ voice
voice = np.fromfile(os.path.join(HERE, "audio", "voice_raw.f32"), dtype=np.float32)[:N]
if len(voice) < N:
    voice = np.pad(voice, (0, N - len(voice)))

# keep the SFX polite under the voice (user will add their own music later, so leave headroom)
envv = np.abs(voice)
k = int(SR * 0.12)
envv = np.convolve(envv, np.ones(k) / k, mode="same")
duck = (1.0 - 0.45 * np.clip(envv / 0.10, 0, 1)).astype(np.float32)
duck = np.convolve(duck, np.ones(int(SR * 0.06)) / int(SR * 0.06), mode="same").astype(np.float32)
sfx *= duck

mixl = voice * 0.92 + sfx[0] * 0.5
mixr = voice * 0.92 + sfx[1] * 0.5
mix = np.stack([mixl, mixr], 0)
mix = np.tanh(mix * 1.02) * 0.9
mix = mix / max(np.abs(mix).max(), 1e-6) * 0.89

f = int(0.45 * SR)
mix[:, -f:] *= np.linspace(1, 0, f, dtype=np.float32) ** 0.7

raw = os.path.join(HERE, "audio", "mix2_raw.wav")
with wave.open(raw, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype("<i2").tobytes())

out = os.path.join(HERE, "audio", "mix2.wav")
subprocess.run([FF, "-v", "quiet", "-y", "-i", raw, "-af",
                "loudnorm=I=-15:TP=-2.0:LRA=11,aresample=48000", "-ar", "48000", out], check=True)
print("wrote", out, round(plan.TOTAL, 2), "s  (no music)")
