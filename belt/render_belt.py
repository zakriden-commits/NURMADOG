"""12.8s vertical hype promo: photo-real hero frames -> cinematic motion + confetti + sound."""
import math
import os
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageChops

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "video", "scripts"))
import fx
from fx import (W, H, put, clamp, ease_out, ease_in, ease_io, pop, fade, pulse, text_sprite,
                glass, grad_text, finish, sweep, shake, glitch)

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets")
OUT = os.path.join(HERE, "out")
FPS = 30
TOTAL = 12.8
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

GOLD = (255, 205, 120)
CYAN = (140, 235, 255)
WHITE = (248, 250, 255)

# ----------------------------------------------------------------- shots
SHOTS = [
    # name, t0, t1, zoom0, zoom1, panx, pany, blur_amt
    ("shot_portrait.png", 0.0, 3.2, 1.03, 1.12, 0.0, -0.35, 0.0),
    ("shot_belt.png", 3.2, 5.6, 1.10, 1.22, 0.55, 0.1, 0.0),
    ("shot_hero.png", 5.6, 9.4, 1.16, 1.02, 0.0, -0.05, 0.0),
    ("shot_roar.png", 9.4, TOTAL, 1.02, 1.14, -0.1, -0.15, 0.0),
]
CUTS = [s[1] for s in SHOTS[1:]]

_cache = {}


def base(name):
    if name not in _cache:
        im = Image.open(os.path.join(A, name)).convert("RGB")
        s = max(W / im.width, H / im.height) * 1.28
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2.0, percent=70, threshold=2))
        _cache[name] = im
    return _cache[name]


def cam(im, zoom, ox, oy):
    w, h = int(W / zoom), int(H / zoom)
    x0 = int((im.width - w) / 2 + ox * (im.width - w) / 2)
    y0 = int((im.height - h) / 2 + oy * (im.height - h) / 2)
    x0 = max(0, min(im.width - w, x0))
    y0 = max(0, min(im.height - h, y0))
    return im.crop((x0, y0, x0 + w, y0 + h)).resize((W, H), Image.BILINEAR)


def grade(im, amount=1.0):
    im = ImageEnhance.Contrast(im).enhance(1.10)
    im = ImageEnhance.Color(im).enhance(1.06)
    # teal shadows / warm highlights
    arr = np.asarray(im).astype(np.float32) / 255.0
    lum = arr.mean(axis=2, keepdims=True)
    warm = np.array([1.06, 1.0, 0.93], np.float32)
    cool = np.array([0.90, 0.99, 1.10], np.float32)
    w = np.clip((lum - 0.35) / 0.5, 0, 1)
    arr = arr * (cool * (1 - w) + warm * w)
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))


# ----------------------------------------------------------------- confetti
class Confetti:
    def __init__(self, n=90, seed=5, t0=0.0, burst=False):
        rng = np.random.default_rng(seed)
        self.p = []
        for i in range(n):
            self.p.append(dict(
                x=rng.uniform(-0.1, 1.1), y=rng.uniform(-0.4, 1.0),
                vy=rng.uniform(0.16, 0.42), vx=rng.uniform(-0.06, 0.06),
                sz=int(rng.uniform(6, 17)), rot=rng.uniform(0, 360), vr=rng.uniform(-160, 160),
                col=(GOLD if rng.random() < 0.6 else (255, 255, 255)),
                ph=rng.uniform(0, 6.28), t0=t0))

    def draw(self, f, t, density=1.0):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for q in self.p:
            tt = t - q["t0"]
            if tt < 0:
                continue
            y = ((q["y"] + q["vy"] * tt) % 1.45) - 0.2
            x = (q["x"] + q["vx"] * tt + 0.02 * math.sin(tt * 1.6 + q["ph"])) % 1.2 - 0.1
            px, py = x * W, y * H
            if px < -40 or px > W + 40 or py < -40 or py > H + 40:
                continue
            s = q["sz"] * density
            a = int(215 * clamp((1.0 - abs(y - 0.5)) * 1.5))
            ang = math.radians(q["rot"] + q["vr"] * tt)
            ca, sa = math.cos(ang), math.sin(ang)
            pts = [(px + ca * s / 2 - sa * s / 5, py + sa * s / 2 + ca * s / 5),
                   (px - ca * s / 2 - sa * s / 5, py - sa * s / 2 + ca * s / 5),
                   (px - ca * s / 2 + sa * s / 5, py - sa * s / 2 - ca * s / 5),
                   (px + ca * s / 2 + sa * s / 5, py + sa * s / 2 - ca * s / 5)]
            shade = 0.75 + 0.25 * math.sin(ang * 1.7)
            col = tuple(int(c * shade) for c in q["col"])
            d.polygon(pts, fill=col + (a,))
        return Image.alpha_composite(f, lay)


def flare(f, cx, cy, r=520, color=(255, 200, 120), a=95, streak=True):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    dd = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / r
    v = np.clip(1 - dd, 0, 1) ** 2.6
    lay = Image.new("RGBA", (W, H), color + (0,))
    lay.putalpha(Image.fromarray((v * a).astype(np.uint8), "L"))
    f = Image.alpha_composite(f, lay)
    if streak:
        st = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(st)
        for i in range(26):
            aa = int(a * 0.55 * (1 - i / 26))
            d.line([(0, cy + i * 0.6), (W, cy - i * 0.6)], fill=color + (max(0, aa),), width=2)
        st = st.filter(ImageFilter.GaussianBlur(9))
        f = Image.alpha_composite(f, st)
    return f


def scrim(f, frac=0.45, strength=215):
    h = int(H * frac)
    lay = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for i in range(h):
        t = i / h
        d.rectangle([0, i, W, i + 1], fill=(3, 4, 9, int(strength * t ** 1.7)))
    f.alpha_composite(lay, (0, H - h))
    return f


def vignette_soft(f, a=0.55):
    m = fx.VIGNETTE.point(lambda v: int(255 - (255 - v) * a))
    rgb = ImageChops.multiply(f.convert("RGB"), Image.merge("RGB", (m, m, m)))
    return rgb.convert("RGBA")


# ----------------------------------------------------------------- text
def T(txt, size, fill=WHITE, track=10, glow=None, glow_a=110, glow_r=20, squeeze=0.88):
    key = (txt, size, fill, track, glow, glow_a, glow_r, squeeze)
    if key not in _cache:
        _cache[key] = text_sprite(txt, size, fill=fill, tracking=track, squeeze=squeeze,
                                  glow=glow, glow_r=glow_r, glow_a=glow_a)
    return _cache[key]


def frame_at(t):
    # --- shot selection
    for i, (name, t0, t1, z0, z1, px, py, _b) in enumerate(SHOTS):
        if t0 <= t < t1:
            idx, shot = i, (name, t0, t1, z0, z1, px, py)
            break
    else:
        idx, shot = len(SHOTS) - 1, SHOTS[-1]
    name, t0, t1, z0, z1, px, py = shot
    k = clamp((t - t0) / (t1 - t0))

    im = base(name)
    # cinematic easing: fast settle at the shot start, slow drift after
    e = ease_out(clamp(k * 1.6)) * 0.35 + ease_io(k) * 0.65
    zoom = z0 + (z1 - z0) * e
    ox = px * (0.6 + 0.4 * k)
    oy = py * (0.6 + 0.4 * k)
    f = cam(im, zoom, ox, oy)
    f = grade(f).convert("RGBA")

    # filmic bloom on highlights
    bright = f.convert("L").point(lambda v: max(0, int((v - 185) * 3)))
    bloom = Image.new("RGBA", f.size, (0, 0, 0, 0))
    bloom.paste(Image.new("RGBA", f.size, (255, 235, 210, 255)), (0, 0),
                bright.filter(ImageFilter.GaussianBlur(26)))
    f = Image.alpha_composite(f, bloom)

    # --- per shot dressing
    t_local = t - t0
    if name == "shot_portrait.png":
        f = sweep(f, t_local + 0.4, 5.5, 26)
        f = flare(f, W * 0.72, H * 0.30, 620, (140, 220, 255), 60)
    elif name == "shot_belt.png":
        f = flare(f, W * 0.52, H * 0.34, 700, (255, 205, 140), 85)
        f = sweep(f, t_local + 2.0, 4.5, 30)
    elif name == "shot_hero.png":
        f = Confetti(120, seed=9, t0=0.0).draw(f, t_local, 1.0)
        f = flare(f, W * 0.5, H * 0.22, 760, (255, 210, 150), 80)
        f = sweep(f, t_local, 4.0, 22)
    else:
        f = Confetti(150, seed=17, t0=0.0).draw(f, t_local, 1.15)
        f = flare(f, W * 0.5, H * 0.34, 700, (255, 205, 140), 95)

    if name in ("shot_portrait.png", "shot_roar.png"):
        f = scrim(f, 0.46, 225)


    # --- text
    # persistent tiny concept tag
    tag = T("AI-КОНЦЕПТ", 26, (215, 220, 235), 8, squeeze=0.9)
    put(f, tag, W - 30, 90, anchor="rc", alpha=0.55)

    if name == "shot_portrait.png":
        p = pop(t_local, 0.45, 0.55, 1.5)
        if p > 0:
            put(f, T("БЕНУА", 122, WHITE, 12, glow=(120, 190, 255), glow_a=90), 90, 1330,
                anchor="lc", alpha=clamp(p))
        p = pop(t_local, 0.8, 0.55, 1.5)
        if p > 0:
            g = grad_text(T("СЕН-ДЕНИ", 112, WHITE, 10, glow=CYAN, glow_a=100), (255, 255, 255), (120, 200, 255))
            put(f, g, 90, 1448, anchor="lc", alpha=clamp(p))
        p = pop(t_local, 1.5, 0.55, 1.4)
        if p > 0:
            gg = grad_text(T("GOD OF WAR", 64, GOLD, 16, glow=(255, 170, 60), glow_a=110), (255, 235, 180), (230, 160, 70))
            put(f, gg, 90, 1556, anchor="lc", alpha=clamp(p))
        p = fade(t_local, 2.1, 0.5)
        if p > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(lay).line([(90, 1618), (90 + 300 * ease_io(p), 1618)],
                                     fill=(255, 255, 255, int(70 * p)), width=2)
            f = Image.alpha_composite(f, lay)

    elif name == "shot_roar.png":
        p = pop(t_local, 0.35, 0.55, 1.5)
        if p > 0:
            put(f, grad_text(T("САСНЫЙ ОДОБРЯЕТ", 74, WHITE, 10, glow=(255, 120, 60), glow_a=120),
                             (255, 240, 200), (255, 150, 60)), W // 2, 1640, alpha=clamp(p))

    # handheld micro-shake + impact kick
    amp = 3.0
    for c, g in ((5.6, 14), (9.4, 18), (0.0, 6)):
        if 0 <= t - c < 0.4:
            amp += g * (1 - (t - c) / 0.4) ** 2
    f = shake(f.convert("RGB"), t, amp).convert("RGBA")

    # light leak transition into every cut
    for c in CUTS:
        if 0 <= c - t < 0.22:
            p = 1 - (c - t) / 0.22
            f = Image.blend(f, Image.new("RGBA", (W, H), (255, 240, 220, 255)), 0.22 * p)
        if 0 <= t - c < 0.18:
            p = 1 - (t - c) / 0.18
            f = Image.blend(f, Image.new("RGBA", (W, H), (255, 245, 230, 255)), 0.16 * p)

    f = vignette_soft(f, 0.55)
    rgb = finish(f.convert("RGB"), t, grain=0.055, vig=0.0, scan=0.03)

    # fade in / out
    if t < 0.4:
        rgb = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), rgb, ease_out(t / 0.4))
    if t > TOTAL - 0.6:
        rgb = Image.blend(rgb, Image.new("RGB", (W, H), (0, 0, 0)), ease_in(clamp((t - (TOTAL - 0.6)) / 0.55)))
    return rgb


# ----------------------------------------------------------------- audio
def build_audio(path):
    import wave
    SR = 48000
    N = int(SR * (TOTAL + 0.3))
    rng = np.random.default_rng(11)

    def bp(x, f0, f1, o=2):
        from scipy import signal as sg
        sos = sg.butter(o, [min(f0 / (SR / 2), 0.97), min(f1 / (SR / 2), 0.99)], "band", output="sos")
        return sg.sosfilt(sos, x).astype(np.float32)

    def hp(x, fc, o=2):
        from scipy import signal as sg
        sos = sg.butter(o, min(fc / (SR / 2), 0.99), "high", output="sos")
        return sg.sosfilt(sos, x).astype(np.float32)

    def lp(x, fc, o=2):
        from scipy import signal as sg
        sos = sg.butter(o, min(fc / (SR / 2), 0.99), "low", output="sos")
        return sg.sosfilt(sos, x).astype(np.float32)

    out = np.zeros((2, N), np.float32)

    def add(sig, t, gain=1.0, pan=0.0):
        i = int(max(0, t) * SR)
        if i >= N:
            return
        n = min(len(sig), N - i)
        gl = gain * math.sqrt((1 - pan) / 2) * 1.414
        gr = gain * math.sqrt((1 + pan) / 2) * 1.414
        out[0, i:i + n] += sig[:n] * gl
        out[1, i:i + n] += sig[:n] * gr

    # arena crowd bed: filtered noise with slow random swells
    n = N
    crowd = bp(rng.standard_normal(n).astype(np.float32), 180, 2600)
    mod = 0.55 + 0.45 * np.sin(np.linspace(0, 9, n) * 2 * np.pi / 3.1)
    mod *= 0.7 + 0.3 * np.sin(np.linspace(0, 21, n))
    crowd = (crowd * mod * 0.5).astype(np.float32)
    crowd[-int(0.7 * SR):] *= np.linspace(1, 0, int(0.7 * SR)) ** 1.5
    for ch in range(2):
        out[ch] += crowd * 0.20 * (1.0 if ch == 0 else 0.92)

    # claps / shouts
    for i in range(46):
        tt = rng.uniform(0.0, TOTAL - 0.4)
        ln = int(SR * rng.uniform(0.04, 0.09))
        c = hp(rng.standard_normal(ln).astype(np.float32), 900) * np.exp(-np.arange(ln) / (ln * 0.35))
        add(c * 0.12, tt, 0.9, rng.uniform(-0.8, 0.8))

    # impact hits on cuts
    for tc, g in ((0.0, 0.9), (5.6, 1.0), (9.4, 1.0), (3.2, 0.6)):
        ln = int(SR * 1.1)
        fr = np.geomspace(90, 34, ln)
        body = np.sin(2 * np.pi * np.cumsum(fr) / SR).astype(np.float32) * np.exp(-np.arange(ln) / (SR * 0.35))
        add(body * 0.85 * g, tc, 1.0)

    # airy whooshes into cuts
    for tc in CUTS:
        ln = int(SR * 0.7)
        w = rng.standard_normal(ln).astype(np.float32)
        w = bp(w, 300, 4000)
        env = np.sin(np.pi * np.arange(ln) / ln) ** 2
        add((w * env * 0.5), tc - 0.35, 0.75, -0.2)

    # gold shimmer for the belt shot
    ln = int(SR * 2.0)
    sh = hp(rng.standard_normal(ln).astype(np.float32), 6000, 3)
    env = np.sin(np.pi * np.arange(ln) / ln) ** 2
    add(sh * env * 0.30, 3.25, 0.9, 0.3)

    # sub riser into the finale
    ln = int(SR * 1.6)
    fr = np.geomspace(60, 130, ln)
    r = np.sin(2 * np.pi * np.cumsum(fr) / SR).astype(np.float32)
    env = (np.arange(ln) / ln) ** 2.2
    add(r * env * 0.35, 9.4 - 1.55, 1.0)

    mix = np.tanh(out * 1.05) * 0.92
    mix = mix / max(np.abs(mix).max(), 1e-6) * 0.9
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix.T, -1, 1) * 32767).astype("<i2").tobytes())


def render():
    os.makedirs(OUT, exist_ok=True)
    fx.init_overlays()
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()

    wav = os.path.join(HERE, "audio.wav")
    build_audio(wav)

    vid = os.path.join(OUT, "video_only.mp4")
    n = int(round(TOTAL * FPS))
    cmd = [FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", vid]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame_at(i / FPS).tobytes())
        if i % 40 == 0:
            print(f"  frame {i}/{n}", flush=True)
    p.stdin.close()
    p.wait()

    final = os.path.join(OUT, "benua_belt_promo.mp4")
    subprocess.run([FF, "-v", "error", "-y", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final],
                   check=True)
    print("->", final)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "still":
        fx.init_overlays()
        for s in sys.argv[2:]:
            v = float(s)
            Image.new("RGB", (10, 10))
            frame_at(v).save(os.path.join(HERE, f"still_{v:05.2f}.png"))
            print("still", v)
    else:
        render()
