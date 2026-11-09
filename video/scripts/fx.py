"""Drawing helpers for the SANY / MMA short: comic-style type, sprites, grades, glitch."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops, ImageEnhance

W, H = 1080, 1920
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

_fc = {}


def font(size, bold=True):
    key = (size, bold)
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FB if bold else FR, size)
    return _fc[key]


# ---------------------------------------------------------------- type
def text_sprite(txt, size, fill=(255, 255, 255), stroke=0, stroke_fill=(10, 8, 14),
                glow=None, glow_r=22, glow_a=210, squeeze=0.80, tracking=0,
                shadow=None, shadow_off=(7, 9), shadow_blur=0, rotate=0.0, bold=True,
                pad=40):
    """Render a line of text as a tight RGBA sprite with optional squash/stroke/glow/shadow."""
    f = font(size, bold)
    # measure with tracking
    widths = [f.getlength(c) for c in txt]
    total = sum(widths) + tracking * max(0, len(txt) - 1)
    asc, desc = f.getmetrics()
    iw = int(total + pad * 2 + stroke * 2 + glow_r * 3 + 60)
    ih = int(asc + desc + pad * 2 + stroke * 2 + glow_r * 3 + 60)
    img = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad + glow_r * 2
    y = pad + glow_r * 2
    for c, w in zip(txt, widths):
        d.text((x, y), c, font=f, fill=fill + (255,) if len(fill) == 3 else fill,
               stroke_width=stroke, stroke_fill=stroke_fill + (255,) if len(stroke_fill) == 3 else stroke_fill)
        x += w + tracking
    if squeeze != 1.0:
        img = img.resize((max(1, int(iw * squeeze)), ih), Image.LANCZOS)
    if rotate:
        img = img.rotate(rotate, expand=True, resample=Image.BICUBIC)

    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    a = img.split()[3]
    if glow is not None:
        g = Image.new("RGBA", img.size, glow + (0,))
        g.putalpha(a.point(lambda v: int(v * glow_a / 255)))
        g = g.filter(ImageFilter.GaussianBlur(glow_r))
        out = Image.alpha_composite(out, g)
    if shadow is not None:
        s = Image.new("RGBA", img.size, shadow + (0,))
        s.putalpha(a)
        if shadow_blur:
            s = s.filter(ImageFilter.GaussianBlur(shadow_blur))
        tmp = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tmp.paste(s, shadow_off, s)
        out = Image.alpha_composite(out, tmp)
    out = Image.alpha_composite(out, img)
    return out.crop(out.getbbox())


def put(frame, spr, cx, cy, scale=1.0, alpha=1.0, rot=0.0, anchor="cc"):
    if scale != 1.0 and spr.width > 1:
        spr = spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))), Image.LANCZOS)
    if rot:
        spr = spr.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        s = spr.copy()
        s.putalpha(s.split()[3].point(lambda v: int(v * alpha)))
        spr = s
    x = int(cx - spr.width / 2) if anchor[0] == "c" else int(cx)
    y = int(cy - spr.height / 2) if anchor[-1] == "c" else int(cy)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(frame.width, x + spr.width), min(frame.height, y + spr.height)
    if x1 <= x0 or y1 <= y0:
        return frame
    if (x0, y0, x1, y1) != (x, y, x + spr.width, y + spr.height):
        spr = spr.crop((x0 - x, y0 - y, x1 - x, y1 - y))
    frame.alpha_composite(spr, (x0, y0))
    return frame


# ---------------------------------------------------------------- easing
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def ease_io(x):
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


def back_out(x, s=2.2):
    x = clamp(x) - 1
    return 1 + x * x * ((s + 1) * x + s)


def pop(t, t0, dur=0.28, s=2.4):
    """0..1 slam-in with overshoot, then settle at 1."""
    if t < t0:
        return 0.0
    x = clamp((t - t0) / dur)
    if x >= 1:
        return 1.0
    return back_out(x, s)


def fade(t, t0, dur=0.3):
    return clamp((t - t0) / dur)


def pulse(t, hz=2.0, lo=0.0, hi=1.0):
    return lo + (hi - lo) * (0.5 + 0.5 * math.sin(t * hz * 2 * math.pi))


# ---------------------------------------------------------------- backgrounds
_bgcache = {}


def load_rgb(path):
    if path not in _bgcache:
        _bgcache[path] = Image.open(path).convert("RGB")
    return _bgcache[path]


def bg_fill(path, scale=1.0, ox=0.0, oy=0.0, grade=None, blur=0.0):
    """Cover-fill the frame from a background image, with zoom/offset."""
    im = load_rgb(path)
    s = max(W / im.width, H / im.height) * scale
    nw, nh = int(im.width * s), int(im.height * s)
    im = im.resize((nw, nh), Image.LANCZOS)
    x = int((nw - W) / 2 + ox * (nw - W) / 2)
    y = int((nh - H) / 2 + oy * (nh - H) / 2)
    x = max(0, min(nw - W, x))
    y = max(0, min(nh - H, y))
    im = im.crop((x, y, x + W, y + H))
    if grade is not None:
        im = tint(im, *grade)
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


def tint(im, color, amount=0.35, sat=1.0, contrast=1.0, bright=1.0):
    im = im.convert("RGB")
    if sat != 1.0:
        im = ImageEnhance.Color(im).enhance(sat)
    if amount:
        lay = Image.new("RGB", im.size, color)
        im = Image.blend(im, ImageChops.multiply(im, lay), amount)
    if contrast != 1.0:
        im = ImageEnhance.Contrast(im).enhance(contrast)
    if bright != 1.0:
        im = ImageEnhance.Brightness(im).enhance(bright)
    return im


# ---------------------------------------------------------------- overlays
def _noise(seed, w, h, blur=0):
    rng = np.random.default_rng(seed)
    a = rng.integers(0, 255, (h, w, 1), dtype=np.uint8)
    im = Image.fromarray(np.repeat(a, 3, axis=2))
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return im


VIGNETTE = None
GRAIN = None


def init_overlays():
    global VIGNETTE, GRAIN
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = W / 2, H / 2
    r = np.sqrt(((x - cx) / (W * 0.62)) ** 2 + ((y - cy) / (H * 0.72)) ** 2)
    v = np.clip(1.08 - 0.55 * np.clip(r, 0, 1.6) ** 2.1, 0.18, 1.0)
    VIGNETTE = Image.fromarray((v * 255).astype(np.uint8), "L")
    GRAIN = [_noise(s, W // 3, H // 3, 0.5).resize((W, H), Image.BILINEAR) for s in range(6)]


def finish(frame, t, grain=0.05, vig=0.55, scan=0.07):
    rgb = frame.convert("RGB")
    if scan:
        sy = np.ones((H, 1, 1), np.float32)
        yy = np.arange(H)
        sy[:, 0, 0] = 1.0 - scan * (0.5 + 0.5 * np.cos(yy * math.pi / 4.0))
        rgb = Image.fromarray(np.clip(np.asarray(rgb, np.float32) * sy, 0, 255).astype(np.uint8))
    g = GRAIN[int(t * 17) % len(GRAIN)]
    rgb = Image.blend(rgb, ImageChops.overlay(rgb, g), grain) if grain else rgb
    if vig:
        rgb = Image.composite(rgb, ImageChops.multiply(rgb, Image.merge("RGB", (VIGNETTE,) * 3)), VIGNETTE)
        # simpler: darken edges
        m = VIGNETTE.point(lambda v: int(255 - (255 - v) * vig))
        rgb = ImageChops.multiply(rgb, Image.merge("RGB", (m, m, m)))
    return rgb


def shake(im, t, amp, hz=17, seed=0):
    if amp <= 0:
        return im
    dx = amp * (math.sin(t * hz * 2 * math.pi + seed) * 0.7 + math.sin(t * hz * 5.7 + 1.3) * 0.3)
    dy = amp * (math.cos(t * hz * 2.3 * math.pi + seed) * 0.7 + math.sin(t * hz * 6.1) * 0.3)
    canvas = Image.new("RGB", (W, H), (0, 0, 0))
    canvas.paste(im, (int(dx), int(dy)))
    return canvas


def chromatic(im, shift=6, t=0.0):
    im = im.convert("RGB")
    r, g, b = im.split()
    r = ImageChops.offset(r, shift, int(shift * 0.2))
    b = ImageChops.offset(b, -shift, int(-shift * 0.2))
    return Image.merge("RGB", (r, g, b))


def glitch(im, t, amount=1.0, seed=0):
    """Blocky RGB-split row displacement."""
    if amount <= 0.01:
        return im
    mode = im.mode
    arr = np.asarray(chromatic(im, int(6 * amount))).copy()
    rng = np.random.default_rng(int(t * 60) + seed)
    n = rng.integers(3, 9)
    for _ in range(int(n * amount)):
        y0 = int(rng.integers(0, H - 40))
        h = int(rng.integers(6, int(50 + 90 * amount)))
        dx = int(rng.normal(0, 55 * amount))
        arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], dx, axis=1)
    if amount > 0.6:
        k = int(rng.integers(2, 5))
        for _ in range(k):
            y0 = int(rng.integers(0, H - 10))
            h = int(rng.integers(2, 8))
            arr[y0:y0 + h] = 255 - arr[y0:y0 + h]
    out = Image.fromarray(arr)
    if mode == "RGBA":
        out = out.convert("RGBA")
    return out


def flash(frame, a):
    if a <= 0:
        return frame
    white = Image.new("RGB", (W, H), (255, 255, 255))
    return Image.blend(frame.convert("RGB"), white, clamp(a))


def speedlines(frame, cx, cy, t, color=(255, 255, 255), n=90, alpha=90, rmin=380, seed=3):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi) + t * 0.15
        r0 = rmin + rng.uniform(-40, 260)
        r1 = r0 + rng.uniform(120, 420)
        wgt = rng.uniform(1.5, 5)
        d.line([(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                (cx + math.cos(a) * r1, cy + math.sin(a) * r1)], fill=color + (int(alpha * rng.uniform(0.4, 1)),), width=int(wgt))
    return Image.alpha_composite(frame, lay)


def dot_halftone(frame, color=(255, 40, 90), alpha=40, step=14, r=3):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for y in range(0, H, step):
        for x in range(0, W, step):
            d.ellipse([x, y, x + r, y + r], fill=color + (alpha,))
    return Image.alpha_composite(frame, lay)


def brackets(frame, color=(255, 255, 255), a=200, m=70, ln=90, w=5):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = color + (a,)
    for (x, y, sx, sy) in [(m, m, 1, 1), (W - m, m, -1, 1), (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
        d.line([(x, y), (x + ln * sx, y)], fill=c, width=w)
        d.line([(x, y), (x, y + ln * sy)], fill=c, width=w)
    return Image.alpha_composite(frame, lay)


def gradient_fade(img, from_bottom=0.0, from_top=0.0, color=(0, 0, 0)):
    """Fade the sprite into `color` at its edges (keeps alpha)."""
    a = np.asarray(img.split()[3], np.float32) / 255.0
    hh = a.shape[0]
    if from_bottom:
        k = int(hh * from_bottom)
        ramp = np.linspace(0, 1, k, dtype=np.float32)
        a[hh - k:] *= ramp[:, None]
    if from_top:
        k = int(hh * from_top)
        ramp = np.linspace(1, 0, k, dtype=np.float32)
        a[:k] *= ramp[:, None]
    out = img.copy()
    out.putalpha(Image.fromarray((a * 255).astype(np.uint8), "L"))
    return out


def glow_behind(frame, spr, cx, cy, color=(80, 220, 255), r=120, a=110):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = Image.new("RGBA", spr.size, color + (0,))
    m.putalpha(spr.split()[3].point(lambda v: int(v * a / 255)))
    m = m.filter(ImageFilter.GaussianBlur(r))
    lay.alpha_composite(m, (int(cx - m.width / 2), int(cy - m.height / 2)))
    return Image.alpha_composite(frame, lay)


def card(wh, color=(0, 0, 0), alpha=180, r=28, border=None, bw=6):
    w, h = wh
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w - 1, h - 1], r, fill=color + (alpha,),
                        outline=(border + (255,)) if border else None, width=bw if border else 0)
    return lay


# ---------------------------------------------------------------- modern extras
def glass(w, h, r=34, tint=(255, 255, 255), a=26, border=(255, 255, 255), ba=70, bw=2, sheen=0.10):
    """Frosted panel: soft top sheen, thin border."""
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, w - 1, h - 1], r, fill=tint + (a,), outline=border + (ba,), width=bw)
    if sheen:
        sheenl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sheenl)
        ds.rounded_rectangle([0, 0, w - 1, int(h * 0.5)], r, fill=(255, 255, 255, int(255 * sheen)))
        lay = Image.alpha_composite(lay, sheenl)
    return lay


def vgrad_mask(size, start=0.0, end=1.0, from_alpha=0, to_alpha=255):
    w, h = size
    m = np.zeros((h, w), np.float32)
    a, b = int(h * start), int(h * end)
    if b > a:
        ramp = np.linspace(from_alpha, to_alpha, b - a, dtype=np.float32)[:, None]
        m[a:b] = ramp
        m[b:] = to_alpha
        m[:a] = from_alpha
    else:
        m[:] = to_alpha
    return Image.fromarray(m.astype(np.uint8), "L")


def grad_text(spr, c1, c2, angle=90):
    """Fill the glyphs with a vertical gradient."""
    w, h = spr.size
    g = Image.new("RGB", (w, h))
    px = np.zeros((h, w, 3), np.uint8)
    t = np.linspace(0, 1, h)[:, None]
    for i in range(3):
        px[:, :, i] = (c1[i] + (c2[i] - c1[i]) * t).astype(np.uint8)
    g = Image.fromarray(px)
    g.putalpha(spr.split()[3])
    return g


def reflection(spr, alpha=0.22, blur=5, squash=0.55, fade=1.0):
    r = spr.transpose(Image.FLIP_TOP_BOTTOM)
    r = r.resize((r.width, max(1, int(r.height * squash))), Image.LANCZOS)
    r = r.filter(ImageFilter.GaussianBlur(blur))
    m = vgrad_mask(r.size, 0.0, fade, 255, 0)
    a = ImageChops.multiply(r.split()[3], m)
    r.putalpha(a.point(lambda v: int(v * alpha)))
    return r


def sweep(frame, t, period=5.0, alpha=26, tilt=0.45):
    """Slow diagonal light band moving across the frame."""
    ph = (t % period) / period
    x = -W * 0.6 + ph * W * 1.8
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    band = 260
    for i in range(band):
        a_ = int(alpha * (1 - abs(i - band / 2) / (band / 2)) ** 2)
        off = int(x + i + (i * tilt))
        d.line([(off, 0), (off - H * tilt * 0.5, H)], fill=(255, 255, 255, a_), width=2)
    return Image.alpha_composite(frame, lay)


def camera(im, t, t0, t1, z0=1.0, z1=1.035, dx=0.0, dy=0.0):
    """Ken-burns crop over a scene."""
    k = (t - t0) / max(t1 - t0, 1e-4)
    k = clamp(k)
    z = z0 + (z1 - z0) * ease_io(k)
    w, h = int(W / z), int(H / z)
    x0 = int((W - w) / 2 + dx * (W - w) / 2 * k)
    y0 = int((H - h) / 2 + dy * (H - h) / 2 * k)
    x0 = max(0, min(W - w, x0))
    y0 = max(0, min(H - h, y0))
    return im.crop((x0, y0, x0 + w, y0 + h)).resize((W, H), Image.BILINEAR)
