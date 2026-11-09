"""Decode narration clips, trim silence, time-compress so the whole voice-over fits the target
length, and write the timeline (JSON) that the video renderer uses."""
import json
import subprocess
import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
SR = 48000
TARGET_TOTAL = 30.5      # seconds of finished video
GAP = 0.22               # silence between lines


def load(path):
    raw = subprocess.run(
        [FF, "-v", "quiet", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def trim(x, rel=0.02, pad=0.05):
    env = np.abs(x)
    # smooth envelope
    k = int(SR * 0.01)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    thr = max(env.max() * rel, 1e-4)
    idx = np.where(env > thr)[0]
    a, b = idx[0], idx[-1]
    a = max(0, a - int(pad * SR))
    b = min(len(x), b + int(pad * SR))
    return x[a:b]


def atempo(x, rate):
    """Time-stretch by resampling the spectrum-free way: use ffmpeg atempo for quality."""
    if abs(rate - 1.0) < 1e-3:
        return x
    p = subprocess.run(
        [FF, "-v", "quiet", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
         "-filter:a", f"atempo={rate:.5f}", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
        input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


clips = [trim(load(f"video/audio/n{i}.mp3")) for i in range(1, 7)]
raw_total = sum(len(c) for c in clips) / SR
speech_target = TARGET_TOTAL - GAP * (len(clips) - 1) - 0.6
rate = raw_total / speech_target
rate = float(np.clip(rate, 1.0, 1.34))
print(f"raw speech {raw_total:.2f}s -> rate {rate:.3f}")

clips = [atempo(c, rate) for c in clips]

timeline, t = [], 0.35          # small lead-in
for c in clips:
    d = len(c) / SR
    timeline.append({"start": round(t, 3), "dur": round(d, 3)})
    t += d + GAP
total = round(t - GAP + 0.55, 3)
print("total video length:", total)

voice = np.zeros(int(SR * (total + 1)), dtype=np.float32)
for c, seg in zip(clips, timeline):
    s = int(seg["start"] * SR)
    voice[s:s + len(c)] += c
peak = np.abs(voice).max()
voice = voice / max(peak, 1e-6) * 0.89
voice.astype(np.float32).tofile("video/audio/voice_raw.f32")
json.dump({"sr": SR, "total": total, "gaps": GAP, "lines": timeline},
          open("video/audio/timeline.json", "w"), indent=1)
print(json.dumps(timeline, indent=0))
