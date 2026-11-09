"""Frame renderer for the 30s SANY / MMA short. Renders 1080x1920@30 straight into ffmpeg."""
import math
import os
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

import plan
import fx
from fx import (W, H, text_sprite, put, clamp, ease_out, ease_in, ease_io, back_out, pop, fade,
                pulse, bg_fill, tint, finish, shake, glitch, flash, speedlines, brackets,
                gradient_fade, glow_behind, card, chromatic)

HERE = plan.HERE
A = os.path.join(HERE, "assets")
cy_, sy_ = W / 2, H / 2

# ------------------------------------------------------------------ assets
SPR = {}


def sprite(name, h, fade_bottom=0.0, bright=1.0, sat=1.0):
    key = (name, h, fade_bottom, bright, sat)
    if key not in SPR:
        im = Image.open(os.path.join(A, name)).convert("RGBA")
        s = h / im.height
        im = im.resize((max(1, int(im.width * s)), h), Image.LANCZOS)
        if fade_bottom:
            im = gradient_fade(im, from_bottom=fade_bottom)
        if bright != 1.0 or sat != 1.0:
            rgb = im.convert("RGB")
            from PIL import ImageEnhance
            rgb = ImageEnhance.Brightness(rgb).enhance(bright)
            rgb = ImageEnhance.Color(rgb).enhance(sat)
            rgb.putalpha(im.split()[3])
            im = rgb
        SPR[key] = im
    return SPR[key]


_TS = {}


def T(txt, size, **kw):
    key = (txt, size, tuple(sorted(kw.items(), key=lambda kv: kv[0])))
    if key not in _TS:
        _TS[key] = text_sprite(txt, size, **kw)
    return _TS[key]


def label(txt, size=40, color=(255, 255, 255), box=(250, 30, 30), pad=(26, 12), rot=0.0,
          border=None, glow=None):
    """small chip on a translucent rounded box"""
    s = T(txt, size, fill=color, stroke=0, squeeze=0.86, tracking=2)
    w, h = s.width + pad[0] * 2, s.height + pad[1] * 2
    c = card((w, h), color=box, alpha=225, r=int(h / 2.6), border=border, bw=4)
    c.alpha_composite(s, (pad[0], pad[1]))
    if rot:
        c = c.rotate(rot, expand=True, resample=Image.BICUBIC)
    return c


def fit(spr, maxw, maxh=None):
    s = 1.0
    if spr.width > maxw:
        s = maxw / spr.width
    if maxh and spr.height * s > maxh:
        s = min(s, maxh / spr.height)
    if s < 1.0:
        spr = spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.LANCZOS)
    return spr


def particles(f, t, n=34, color=(180, 230, 255), seed=1, speed=26, alpha=95, ytop=0, ybot=None):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    ybot = H if ybot is None else ybot
    for i in range(n):
        x = rng.uniform(0, W)
        y0 = rng.uniform(ytop, ybot)
        r = rng.uniform(1.6, 4.2)
        sp = speed * rng.uniform(0.5, 1.6)
        yy = ytop + (y0 - ytop - t * sp) % max(1, (ybot - ytop))
        d.ellipse([x, yy, x + r * 2, yy + r * 2],
                  fill=color + (int(alpha * rng.uniform(0.35, 1)),))
    return Image.alpha_composite(f, lay)


def stamp(txt, size, fg=(255, 255, 255), bg=(226, 26, 51), rot=-5.0, pad=(46, 22), border=None):
    s = T(txt, size, fill=fg, stroke=0, squeeze=0.80, tracking=3)
    w, h = s.width + pad[0] * 2, s.height + pad[1] * 2
    c = card((w, h), color=bg, alpha=245, r=14, border=border or fg, bw=6)
    c.alpha_composite(s, (pad[0], pad[1]))
    return c.rotate(rot, expand=True, resample=Image.BICUBIC)


def bg_radial(center=(0.5, 0.55), r=0.75, color=(90, 210, 255), a=110):
    cx, cyy = center[0] * W, center[1] * H
    R = r * H
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - cx) ** 2 + (y - cyy) ** 2) / R
    v = np.clip(1 - d, 0, 1) ** 2.2
    lay = Image.new("RGBA", (W, H), color + (0,))
    lay.putalpha(Image.fromarray((v * a).astype(np.uint8), "L"))
    return lay


# ------------------------------------------------------------------ hit helpers
def hit(t, kinds=("punch", "stamp", "bass"), decay=0.28):
    v = 0.0
    for tt, kind, g in plan.BEATS:
        if kind in kinds and 0 <= t - tt < decay:
            v = max(v, g * (1 - (t - tt) / decay) ** 2)
    return v


def glitch_amount(t):
    v = 0.0
    for tt, kind, g in plan.BEATS:
        if kind in ("glitch", "stamp") and 0 <= t - tt < 0.3:
            v = max(v, g * (1 - (t - tt) / 0.3) ** 1.4)
    return v


def cut_zoom(t):
    """whip-zoom snap around hard cuts"""
    z, dx = 1.0, 0.0
    for c in plan.CUTS:
        if 0 <= c - t < 0.14:
            x = (t - (c - 0.14)) / 0.14
            z = 1.0 + 0.13 * x ** 2
            dx = 70 * x ** 2
        if 0 <= t - c < 0.13:
            x = (t - c) / 0.13
            z = max(z, 1.0 + 0.10 * (1 - x) ** 2)
            dx = min(dx, -55 * (1 - x) ** 2)
    return z, dx


def apply_cut_motion(im, z, dx):
    if abs(z - 1.0) < 1e-3 and abs(dx) < 0.5:
        return im
    w, h = int(W / z), int(H / z)
    x0 = int((W - w) / 2 - dx / z)
    y0 = int((H - h) / 2)
    im = im.crop((x0, y0, x0 + w, y0 + h)).resize((W, H), Image.BILINEAR)
    return im


# ------------------------------------------------------------------ scenes
def head_inset(name, d, ring=(80, 220, 255), ang=0.0):
    """Circular mug-shot crop of a fighter's head with a coloured ring."""
    im = Image.open(os.path.join(A, name)).convert("RGBA")
    w, h = im.size
    box = (int(w * 0.16), int(h * 0.02), int(w * 0.84), int(h * 0.02) + int(w * 0.68))
    head = im.crop(box)
    side = max(head.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.alpha_composite(head, ((side - head.width) // 2, (side - head.height) // 2))
    sq = sq.resize((d, d), Image.LANCZOS)
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d - 1, d - 1], fill=255)
    out = Image.new("RGBA", (d + 24, d + 24), (0, 0, 0, 0))
    ringl = Image.new("RGBA", (d + 24, d + 24), (0, 0, 0, 0))
    ImageDraw.Draw(ringl).ellipse([0, 0, d + 23, d + 23], fill=ring + (255,))
    out.alpha_composite(ringl)
    body = Image.new("RGBA", (d, d), (18, 10, 24, 255))
    body.paste(sq, (0, 0), mask)
    out.alpha_composite(body, (12, 12))
    if ang:
        out = out.rotate(ang, expand=True, resample=Image.BICUBIC)
    return out


def s_hook(t, a, b):
    ts = t - a
    f = bg_fill(os.path.join(A, "bg_glitch.png"), scale=1.06 + 0.04 * ts, ox=math.sin(ts * 0.7) * 0.3,
                grade=((10, 0, 30), 0.25, 1.05, 1.15, 0.85)).convert("RGBA")
    f.alpha_composite(bg_radial((0.5, 0.4), 0.55, (255, 30, 140), 90))
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(band)
    for i in range(440):
        a_ = int(160 * (1 - abs(i - 220) / 220) ** 1.4)
        dd.rectangle([0, 380 + i * 2, W, 382 + i * 2], fill=(4, 1, 10, a_))
    f.alpha_composite(band)

    if ts < 0.9:
        f = speedlines(f, W // 2, 700, ts, (255, 255, 255), 70, int(120 * (1 - ts / 0.9)), 460, 5)

    p = pop(ts, 0.18, 0.3)
    if p > 0:
        put(f, label("ММА  •  МНЕНИЕ  •  БЕЗ ФИЛЬТРА", 40, (255, 255, 255), (18, 6, 24), (24, 11),
                     border=(255, 40, 130)), cy_, 330, scale=p, alpha=clamp(p))

    p = pop(ts, 0.50, 0.26, 2.6)
    if p > 0:
        put(f, fit(T("КТО ТАКОЙ", 158, fill=(255, 255, 255), stroke=9, stroke_fill=(12, 4, 20),
                     glow=(255, 30, 140), glow_r=26, squeeze=0.78, tracking=2), W - 100),
            cy_, 530, scale=0.9 + 0.1 * p + 0.02 * math.sin(ts * 6), alpha=clamp(p), rot=-4)

    p = pop(ts, 0.86, 0.3, 2.8)
    if p > 0:
        s_ = fit(T("САСНЫЙ?", 240, fill=(255, 214, 60), stroke=11, stroke_fill=(14, 6, 20),
                   glow=(255, 40, 60), glow_r=32, squeeze=0.80, tracking=4), W - 90)
        put(f, s_, cy_, 740 + 12 * math.sin(ts * 5.0), scale=1.14 - 0.14 * p, rot=2.5)
        if ts < 1.6:
            f = glitch(f, ts, 0.9 * (1 - (ts - 0.86) / 0.74), 11)

    p = pop(ts, 1.52, 0.3, 2.4)
    if p > 0:
        st = stamp("ЗА 30 СЕКУНД", 60, fg=(255, 255, 255), bg=(232, 22, 44), rot=5.5)
        put(f, st, cy_ + 20, 960, scale=1.25 - 0.25 * p, alpha=clamp(p))

    # teaser portraits: favourite vs hate target
    for i, (nm, t0, x, ring, cap, col) in enumerate([
            ("bsd_cut.png", 2.32, 320, (0, 220, 255), "ЛЮБИМЕЦ", (0, 220, 255)),
            ("khabib_cut.png", 2.72, 760, (255, 60, 60), "ХЕЙТ", (255, 70, 60))]):
        pp = pop(ts, t0, 0.3, 2.4)
        if pp > 0:
            ins = head_inset(nm, 300, ring, ang=-5 + i * 10)
            put(f, ins, x, 1350, scale=1.25 - 0.25 * pp, alpha=clamp(pp),
                rot=(-4 + i * 7) + 1.5 * math.sin(ts * 2 + i))
            put(f, label(cap, 40, (255, 255, 255), (10, 4, 16), (22, 10), border=col),
                x, 1560, scale=0.9 + 0.1 * pp, alpha=clamp(pp))

    p = fade(ts, 3.1, 0.5)
    if p > 0:
        put(f, label("КТО ОН И ЧЕГО ХОЧЕТ", 44, (235, 245, 255), (8, 4, 14), (26, 12),
                     border=(255, 214, 60)), cy_, 1165, alpha=p * 0.95)

    f = ticker(f, ts * 260, "САСНЫЙ   •   ММА   •   СТИЛЬ   •   ХЕЙТ НУРМАДОГОВ   •   ")
    return f


def ticker(f, offset, text, y=None, size=44, alpha=235):
    y = H - 250 if y is None else y
    band = Image.new("RGBA", (W, 96), (6, 4, 10, 210))
    f.alpha_composite(band, (0, y - 48))
    s = T(text, size, fill=(255, 255, 255), stroke=0, squeeze=0.92, tracking=6)
    if s.width < 10:
        return f
    n = int(W / s.width) + 2
    strip = Image.new("RGBA", (s.width * n, s.height), (0, 0, 0, 0))
    for i in range(n):
        strip.alpha_composite(s, (i * s.width, 0))
    off = int(offset) % s.width
    f.alpha_composite(strip.crop((off, 0, off + W, strip.height)), (0, y - strip.height // 2))
    return f


def s_bsd(t, a, b):
    ts = t - a
    dur = b - a
    f = bg_fill(os.path.join(A, "bg_cage.png"), scale=1.02 + 0.055 * ts / dur,
                oy=-0.05 + 0.1 * ts / dur, grade=((0, 10, 30), 0.18, 1.0, 1.12, 0.92)).convert("RGBA")
    f.alpha_composite(bg_radial((0.5, 0.62), 0.62, (70, 210, 255), 95))

    f = particles(f, ts, 28, (170, 230, 255), 4, 22, 85, 200, 1900)
    # fighter
    p = pop(ts, 0.03, 0.42, 1.7)
    hgt = 1180
    sp = sprite("bsd_cut.png", hgt, fade_bottom=0.10)
    rise = (1 - ease_out(clamp(ts / 0.45))) * 320
    breathe = 1 + 0.008 * math.sin(ts * 2.2)
    f = glow_behind(f, sp, W / 2, 1940 - hgt / 2 + rise, (60, 200, 255), 120, 70)
    put(f, sp, W / 2, 1940 - hgt / 2 + 10 + rise, scale=(0.94 + 0.06 * p) * breathe, alpha=clamp(p))

    # name
    p1 = pop(ts, 0.40, 0.26, 2.4)
    if p1 > 0:
        put(f, T("БЕНУА", 158, fill=(255, 255, 255), stroke=8, stroke_fill=(8, 10, 18),
                 glow=(20, 200, 255), glow_r=24, squeeze=0.80, tracking=3),
            cy_, 292, scale=1.06 - 0.06 * p1, alpha=clamp(p1), rot=-2)
    p2 = pop(ts, 0.83, 0.26, 2.4)
    if p2 > 0:
        put(f, T("СЕН-ДЕНИ", 158, fill=(120, 230, 255), stroke=8, stroke_fill=(8, 10, 18),
                 glow=(0, 90, 255), glow_r=26, squeeze=0.80, tracking=3),
            cy_, 432, scale=1.06 - 0.06 * p2, alpha=clamp(p2), rot=2)

    p3 = pop(ts, 1.67, 0.3, 2.2)
    if p3 > 0:
        put(f, label("★  ЛЮБИМЫЙ БОЕЦ САСНОГО", 44, (255, 255, 255), (12, 8, 22), (26, 12),
                     border=(80, 220, 255)), cy_, 560, scale=0.9 + 0.1 * p3, alpha=clamp(p3))

    # specialists stamp
    p4 = pop(ts, 3.07, 0.26, 2.6)
    if p4 > 0:
        st = stamp("БЫВШИЙ СПЕЦНАЗ", 78, fg=(255, 255, 255), bg=(214, 18, 40), rot=-5.5,
                   border=(255, 255, 255))
        amp = 16 * hit(t, ("stamp", "punch"), 0.3)
        put(f, st, cy_ + amp * 0.4, 700 + amp * 0.3, scale=1.3 - 0.3 * p4, alpha=clamp(p4))
        f = brackets(f, (255, 60, 80), int(200 * clamp(p4)), 54, 84, 5)

    # bottom scrim
    scrim = Image.new("RGBA", (W, 460), (0, 0, 0, 0))
    dsc = ImageDraw.Draw(scrim)
    for i in range(460):
        dsc.rectangle([0, i, W, i + 1], fill=(4, 2, 8, int(175 * (i / 460) ** 1.5)))
    f.alpha_composite(scrim, (0, H - 460))

    # caption lines
    q1 = pop(ts, 4.37, 0.24, 2.2)
    if q1 > 0:
        put(f, T("выходит ломать,", 64, fill=(255, 255, 255), stroke=6, stroke_fill=(10, 6, 16),
                 squeeze=0.86, tracking=1, shadow=(0, 0, 0), shadow_off=(5, 6)), cy_, 1600,
            scale=1.04 - 0.04 * q1, alpha=clamp(q1))
    q2 = pop(ts, 5.00, 0.24, 2.2)
    if q2 > 0:
        put(f, T("а не боксировать.", 64, fill=(255, 214, 60), stroke=6, stroke_fill=(10, 6, 16),
                 squeeze=0.86, tracking=1, shadow=(0, 0, 0), shadow_off=(5, 6)), cy_, 1690,
            scale=1.04 - 0.04 * q2, alpha=clamp(q2))

    # hud corner
    put(f, label("01 / БЕНУА СЕН-ДЕНИ", 30, (200, 240, 255), (8, 12, 22), (18, 9),
                 border=(40, 160, 220)), 210, 150, alpha=0.9)
    return f


def s_style(t, a, b):
    ts = t - a
    dur = b - a
    f = bg_fill(os.path.join(A, "bg_cage.png"), scale=1.16 - 0.06 * ts / dur,
                ox=0.25, grade=((0, 40, 90), 0.28, 0.9, 1.2, 0.78), blur=1.6).convert("RGBA")
    f.alpha_composite(bg_radial((0.68, 0.5), 0.55, (0, 220, 255), 80))

    f = particles(f, ts, 30, (150, 240, 255), 11, 30, 80, 100, 1900)
    hgt = 1520
    sp = sprite("bsd_cut.png", hgt, fade_bottom=0.14)
    breathe = 1 + 0.01 * math.sin(ts * 2.6)
    f = glow_behind(f, sp, 800, 1250, (0, 220, 255), 140, 80)
    put(f, sp, 800, 1250, scale=breathe * (1 + 0.02 * hit(t, ("punch",), 0.2)), alpha=1.0, rot=-1.5)

    p = pop(ts, 0.14, 0.26)
    if p > 0:
        put(f, label("ПОЧЕМУ САСНЫЙ ЕГО ТАЩИТ", 42, (255, 255, 255), (10, 6, 16), (24, 11),
                     border=(255, 214, 60)), cy_, 232, scale=0.92 + 0.08 * p, alpha=clamp(p))

    items = [("ДАВЛЕНИЕ", 0.24, 330, 530, (255, 214, 60), -6, 128),
             ("ТЕМП", 1.34, 265, 700, (60, 230, 255), 5, 136),
             ("МЯСОРУБКА", 2.64, 330, 870, (255, 70, 90), -3, 118)]
    for txt, t0, x, y, col, rot, size in items:
        p = pop(ts, t0, 0.26, 2.8)
        if p > 0:
            s = T(txt, size, fill=col, stroke=9, stroke_fill=(8, 4, 12),
                  glow=col, glow_r=22, squeeze=0.80, tracking=2)
            put(f, s, x, y + 10 * math.sin(ts * 4 + x), scale=1.25 - 0.25 * p, rot=rot, alpha=clamp(p))

    p = pop(ts, 3.86, 0.3, 1.8)
    if p > 0:
        f = speedlines(f, 800, 950, ts, (255, 255, 255), 80, int(95 * clamp(p)), 520, 9)
        put(f, stamp("НОЛЬ ВОЗНИ", 62, fg=(10, 6, 14), bg=(255, 214, 60), rot=4.5,
                     border=(10, 6, 14)), 320, 1055, scale=1.2 - 0.2 * p, alpha=clamp(p))

    if 3.86 < ts < 4.3:
        f = chromatic(f.convert("RGB"), int(10 * (1 - (ts - 3.86) / 0.44))).convert("RGBA")
    put(f, label("02 / СТИЛЬ", 30, (255, 240, 200), (8, 6, 14), (18, 9), border=(255, 190, 40)),
        190, 150, alpha=0.9)
    return f


def s_hate(t, a, b):
    ts = t - a
    dur = b - a
    f = bg_fill(os.path.join(A, "bg_red.png"), scale=1.05 + 0.09 * ts / dur,
                grade=((90, 0, 0), 0.3, 0.75, 1.25, 0.8)).convert("RGBA")
    f.alpha_composite(bg_radial((0.5, 0.45), 0.6, (255, 40, 30), 80))

    # BSD leaves at 2.5s
    if ts < 2.9:
        hgt = 880
        sp = sprite("bsd_cut.png", hgt, fade_bottom=0.16, bright=0.92, sat=0.9)
        out = ease_in(clamp((ts - 2.35) / 0.5))
        f = glow_behind(f, sp, 235 - out * 700, 1470, (255, 40, 30), 100, 60)
        put(f, sp, 235 - out * 700, 1470, scale=1.0, alpha=1 - out, rot=-3)

    # khabib slides in
    pk = pop(ts, 2.45, 0.34, 1.8)
    if pk > 0:
        hgt = 1240
        sp = sprite("khabib_cut.png", hgt, fade_bottom=0.14, bright=0.62, sat=0.55)
        f = glow_behind(f, sp, 700, 1240, (255, 30, 30), 130, 90)
        put(f, sp, 700, 1240, scale=0.95 + 0.05 * pk, alpha=pk, rot=0)
        # red X
        xx = pop(ts, 2.75, 0.2, 2.0)
        if xx > 0:
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            al = int(225 * clamp(xx))
            d.line([(410, 900), (990, 1420)], fill=(255, 30, 40, al), width=int(26 * xx))
            d.line([(990, 900), (410, 1420)], fill=(255, 30, 40, al), width=int(26 * xx))
            f = Image.alpha_composite(f, lay)

    p = pop(ts, 0.2, 0.26, 2.2)
    if p > 0:
        put(f, T("САСНЫЙ", 128, fill=(255, 255, 255), stroke=8, stroke_fill=(10, 0, 4),
                 glow=(255, 40, 30), glow_r=22, squeeze=0.80, tracking=2),
            cy_, 330, scale=1.1 - 0.1 * p, alpha=clamp(p), rot=-3)
    p = pop(ts, 0.55, 0.26, 2.4)
    if p > 0:
        put(f, T("ЛЮТО ХЕЙТИТ", 150, fill=(255, 214, 60), stroke=9, stroke_fill=(12, 0, 6),
                 glow=(255, 30, 30), glow_r=26, squeeze=0.80, tracking=2),
            cy_, 460, scale=1.12 - 0.12 * p, alpha=clamp(p), rot=2)
    p = pop(ts, 0.97, 0.24, 2.6)
    if p > 0:
        put(f, T("НУРМАГОМЕДОВЫХ", 96, fill=(255, 255, 255), stroke=7, stroke_fill=(12, 0, 6),
                 glow=(255, 30, 60), glow_r=20, squeeze=0.72, tracking=1),
            cy_, 588, scale=1.1 - 0.1 * p, alpha=clamp(p))
        if ts < 1.8:
            f = glitch(f, ts, 0.55 * (1 - (ts - 0.97) / 0.83), 22)

    # the nickname stamp
    p = pop(ts, 2.47, 0.24, 2.9)
    if p > 0:
        st = stamp("«НУРМАДОГИ»", 104, fg=(255, 255, 255), bg=(20, 4, 10), rot=-7,
                   border=(255, 40, 48))
        amp = 18 * hit(t, ("stamp",), 0.32)
        put(f, st, cy_ + 20 + amp, 800 + amp, scale=1.35 - 0.35 * p, alpha=clamp(p))
        if ts < 3.3:
            f = glitch(f, ts, 0.7 * (1 - (ts - 2.47) / 0.83), 33)

    p = fade(ts, 3.85, 0.4)
    if p > 0:
        put(f, label("ЭТО МНЕНИЕ САСНОГО, БЕЗ ОБИД", 38, (255, 255, 255), (8, 0, 2), (26, 12),
                     border=(255, 60, 60)), cy_, 1710, alpha=p * 0.97)
    put(f, label("03 / ХЕЙТ", 30, (255, 210, 210), (10, 2, 4), (18, 9), border=(230, 40, 40)),
        150, 150, alpha=0.9)
    return f


def s_vs(t, a, b):
    ts = t - a
    dur = b - a
    f = bg_fill(os.path.join(A, "bg_glitch.png"), scale=1.12 + 0.03 * ts,
                grade=((20, 0, 30), 0.42, 0.8, 1.3, 0.5)).convert("RGBA")
    f.alpha_composite(bg_radial((0.5, 0.55), 0.7, (255, 40, 120), 70))

    # VS burst
    p = pop(ts, 0.07, 0.24, 3.0)
    if p > 0:
        vs_a = clamp(p) * (1.0 - 0.85 * clamp((ts - 0.95) / 0.45))
        if vs_a > 0.02:
            f = speedlines(f, cy_, 820, ts, (255, 255, 255), 90, int(110 * clamp(p)), 380, 13)
            put(f, T("VS", 208, fill=(255, 255, 255), stroke=12, stroke_fill=(10, 0, 8),
                     glow=(255, 40, 90), glow_r=40, squeeze=1.0, tracking=6),
                cy_, 790, scale=1.45 - 0.45 * p, alpha=vs_a * 0.95, rot=-4)

    # fighters
    hi = 1060
    pin = pop(ts, 0.18, 0.4, 1.6)
    if pin > 0:
        sp = sprite("bsd_cut.png", hi, fade_bottom=0.12)
        off = (1 - ease_out(clamp(ts / 0.45))) * 420
        f = glow_behind(f, sp, 300 - off, 1450, (0, 210, 255), 110, 70)
        put(f, sp, 300 - off, 1450, scale=1.0, alpha=clamp(pin), rot=1)
        put(f, label("БЕНУА", 40, (0, 230, 255), (6, 10, 20), (22, 10), border=(0, 200, 240)),
            300, 1790, alpha=clamp(pin))
    pin2 = pop(ts, 0.32, 0.4, 1.6)
    if pin2 > 0:
        sp = sprite("khabib_cut.png", hi, fade_bottom=0.12)
        off = (1 - ease_out(clamp((ts - 0.14) / 0.45))) * 420
        f = glow_behind(f, sp, 780 + off, 1450, (255, 60, 40), 110, 65)
        put(f, sp, 780 + off, 1450, scale=1.0, alpha=clamp(pin2), rot=-1)
        put(f, label("ХАБИБ", 40, (255, 120, 110), (20, 6, 8), (22, 10), border=(255, 60, 50)),
            780, 1790, alpha=clamp(pin2))

    p = pop(ts, 0.85, 0.3)
    if p > 0:
        put(f, label("САСНЫЙ СЧИТАЕТ:", 40, (255, 255, 255), (10, 4, 18), (22, 10),
                     border=(255, 214, 60)), cy_, 200, scale=0.9 + 0.1 * p, alpha=clamp(p))

    lines = [("БЕНУА", 1.35, 320, (0, 235, 255), 118),
             ("ОСТАНОВИЛ БЫ", 1.75, 445, (255, 255, 255), 100),
             ("ХАБИБА", 2.17, 570, (255, 60, 60), 126)]
    for txt, t0, y, col, size in lines:
        p = pop(ts, t0, 0.24, 2.6)
        if p > 0:
            put(f, T(txt, size, fill=col, stroke=8, stroke_fill=(8, 2, 10),
                     glow=col, glow_r=22, squeeze=0.80, tracking=2),
                cy_, y, scale=1.18 - 0.18 * p, alpha=clamp(p), rot=-1.5 if y != 470 else 1.5)

    p = pop(ts, 3.07, 0.24, 2.6)
    if p > 0:
        st = stamp("ХАБИБУ ДАВАЛИ ПРОХОДНЫХ", 60, fg=(255, 255, 255), bg=(214, 18, 40), rot=-4.5,
                   border=(255, 255, 255))
        amp = 16 * hit(t, ("stamp",), 0.3)
        put(f, st, cy_ + amp * 0.5, 800 + amp, scale=1.3 - 0.3 * p, alpha=clamp(p))

    put(f, label("04 / VS", 30, (255, 230, 240), (10, 2, 8), (18, 9), border=(255, 60, 90)),
        160, 150, alpha=0.9)
    return f


def s_cta(t, a, b):
    ts = t - a
    dur = b - a
    f = bg_fill(os.path.join(A, "bg_glitch.png"), scale=1.1 + 0.05 * ts / dur,
                grade=((30, 0, 40), 0.45, 0.75, 1.32, 0.5)).convert("RGBA")
    f.alpha_composite(bg_radial((0.5, 0.45), 0.62, (255, 30, 140), 85))

    p = pop(ts, 0.16, 0.26, 2.6)
    if p > 0:
        put(f, T("СНИМАТЬ", 170, fill=(255, 255, 255), stroke=9, stroke_fill=(10, 2, 16),
                 glow=(255, 40, 140), glow_r=28, squeeze=0.80, tracking=3),
            cy_, 470, scale=1.1 - 0.1 * p, alpha=clamp(p), rot=-3)
    p = pop(ts, 0.68, 0.26, 2.8)
    if p > 0:
        put(f, T("ЕЩЁ ТАКОЕ?", 150, fill=(255, 214, 60), stroke=9, stroke_fill=(10, 2, 16),
                 glow=(255, 60, 40), glow_r=28, squeeze=0.76, tracking=2),
            cy_, 640, scale=1.12 - 0.12 * p, alpha=clamp(p), rot=2)

    # poll buttons
    p = pop(ts, 1.36, 0.28, 2.2)
    if p > 0:
        yes = label("ДА", 76, (255, 255, 255), (232, 22, 96), (54, 22), border=(255, 255, 255))
        no = label("НЕТ", 76, (235, 240, 255), (30, 30, 46), (54, 22), border=(120, 130, 160))
        pl = 1 + 0.05 * pulse(ts, 1.6)
        put(f, yes, 330, 900, scale=(1.1 - 0.1 * p) * pl, alpha=clamp(p))
        put(f, no, 750, 900, scale=1.1 - 0.1 * p, alpha=clamp(p) * 0.9)
        put(f, label("голосуй в комментах", 34, (220, 220, 240), (8, 8, 14), (20, 9),
                     border=(120, 130, 160)), cy_, 1012, alpha=clamp(p) * 0.9)

    p = pop(ts, 2.58, 0.28, 2.0)
    if p > 0:
        put(f, T("ПЛЮС В КОММЕНТЫ", 86, fill=(255, 255, 255), stroke=8, stroke_fill=(10, 2, 16),
                 glow=(255, 40, 140), glow_r=24, squeeze=0.80, tracking=2),
            cy_, 1200, scale=1.0 + 0.03 * pulse(ts, 1.4), alpha=clamp(p))
        # bouncing arrow
        yy = 1310 + 16 * math.sin((ts - 2.58) * 7)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        al = int(230 * clamp(p))
        d.polygon([(cy_ - 52, yy - 58), (cy_ + 52, yy - 58), (cy_, yy + 40)],
                  fill=(255, 214, 60, al))
        f = Image.alpha_composite(f, lay)

    p = pop(ts, 2.9, 0.26, 2.0)
    if p > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        bw, bh = 300, 170
        x0, y0 = int(cy_ - bw / 2), 1400
        dd.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 40, fill=(20, 10, 30, 230),
                             outline=(255, 60, 160, 255), width=6)
        dd.polygon([(x0 + 60, y0 + bh - 4), (x0 + 130, y0 + bh - 4), (x0 + 72, y0 + bh + 52)],
                   fill=(20, 10, 30, 230))
        for i in range(3):
            dd.ellipse([x0 + 60 + i * 70, y0 + bh / 2 - 14, x0 + 88 + i * 70, y0 + bh / 2 + 14],
                       fill=(255, 255, 255, 230))
        dd.line([(x0 + bw - 62, y0 - 34), (x0 + bw - 62, y0 + 6)], fill=(255, 214, 60, 255), width=14)
        dd.line([(x0 + bw - 82, y0 - 14), (x0 + bw - 42, y0 - 14)], fill=(255, 214, 60, 255), width=14)
        lay.putalpha(lay.split()[3].point(lambda v: int(v * p)))
        f = Image.alpha_composite(f, lay)

    # outro brand
    p = fade(ts, 3.2, 0.5)
    if p > 0:
        put(f, label("САСНЫЙ  •  MMA CONTENT", 42, (255, 255, 255), (10, 4, 18), (26, 12),
                     border=(255, 40, 140)), cy_, 1690, alpha=p * 0.95)
    put(f, label("05 / ВОПРОС", 30, (255, 230, 240), (10, 2, 8), (18, 9), border=(255, 60, 160)),
        175, 150, alpha=0.9)
    return f


SCENE_FN = {"hook": s_hook, "bsd": s_bsd, "style": s_style, "hate": s_hate, "vs": s_vs, "cta": s_cta}


def progress_bar(f, t):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, W, 7], fill=(255, 255, 255, 40))
    d.rectangle([0, 0, int(W * clamp(t / plan.TOTAL)), 7], fill=(255, 255, 255, 190))
    return Image.alpha_composite(f, lay)


def frame_at(t):
    for name, a, b in plan.SCENES:
        if a <= t < b:
            fn = SCENE_FN[name]
            f = fn(t, a, b)
            break
    else:
        f = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    z, dx = cut_zoom(t)
    f = apply_cut_motion(f, z, dx)

    fl = 0.28 * hit(t, ("punch", "stamp", "bass"), 0.12)
    if fl > 0.01:
        f = flash(f, fl * 0.55).convert("RGBA")
    f = progress_bar(f, t).convert("RGB")

    g = glitch_amount(t)
    if g > 0.02:
        f = glitch(f, t, g, 5)

    amp = 0.0
    for kinds, k in ((("punch", "stamp"), 16), (("bass",), 10)):
        amp = max(amp, k * hit(t, kinds, 0.3))
    if amp > 0.5:
        f = shake(f, t, amp)

    f = finish(f, t, grain=0.055, vig=0.5, scan=0.06)

    # fade in from black / out to black
    if t < 0.18:
        f = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), f, t / 0.18)
    if t > plan.TOTAL - 0.45:
        f = Image.blend(f, Image.new("RGB", (W, H), (0, 0, 0)),
                        clamp((t - (plan.TOTAL - 0.45)) / 0.42))
    return f


def render(out_path, audio=False):
    fx.init_overlays()
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    n = int(round(plan.TOTAL * plan.FPS))
    cmd = [FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(plan.FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
           "-crf", "18", "-pix_fmt", "yuv420p", "-tune", "animation", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        t = i / plan.FPS
        p.stdin.write(frame_at(t).tobytes())
        if i % 60 == 0:
            print(f"  frame {i}/{n}", flush=True)
    p.stdin.close()
    p.wait()
    print("video ->", out_path)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "still":
        fx.init_overlays()
        for tt in sys.argv[2:]:
            v = float(tt)
            frame_at(v).save(os.path.join(HERE, "frames", f"still_{v:05.2f}.png"))
            print("still", v)
    else:
        render(os.path.join(HERE, "out", "video_only.mp4"))
