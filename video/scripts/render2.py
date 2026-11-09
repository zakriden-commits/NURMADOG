"""v2 renderer — smoother, more modern cut: glass UI, depth, dissolves, no music-driven cuts."""
import math
import os
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

import plan2 as plan
import fx
from fx import (W, H, text_sprite, put, clamp, ease_out, ease_in, ease_io, back_out, pop, fade,
                pulse, bg_fill, finish, glitch, speedlines, gradient_fade, glow_behind,
                glass, grad_text, reflection, sweep, camera, chromatic)

HERE = plan.HERE
A = os.path.join(HERE, "assets")
cy_ = W // 2

CYAN = (110, 232, 255)
BLUE = (58, 132, 255)
CORAL = (255, 92, 92)
AMBER = (255, 205, 90)
WHITE = (245, 248, 255)

# ------------------------------------------------------------------ assets
SPR = {}


def sprite(name, h, fade_bottom=0.0, bright=1.0, sat=1.0, tint_c=None, tint_a=0.0):
    key = (name, h, fade_bottom, bright, sat, tint_c, tint_a)
    if key not in SPR:
        im = Image.open(os.path.join(A, name)).convert("RGBA")
        s = h / im.height
        im = im.resize((max(1, int(im.width * s)), h), Image.LANCZOS)
        rgb = im.convert("RGB")
        rgb = ImageEnhance.Brightness(rgb).enhance(bright)
        rgb = ImageEnhance.Color(rgb).enhance(sat)
        if tint_c and tint_a:
            lay = Image.new("RGB", rgb.size, tint_c)
            rgb = Image.blend(rgb, Image.composite(lay, rgb, rgb.convert("L").point(lambda v: 90)), tint_a)
        rgb.putalpha(im.split()[3])
        im = rgb
        if fade_bottom:
            im = gradient_fade(im, from_bottom=fade_bottom)
        SPR[key] = im
    return SPR[key]


_TS = {}


def T(txt, size, **kw):
    key = (txt, size, tuple(sorted(kw.items())))
    if key not in _TS:
        kw.setdefault("squeeze", 0.86)
        _TS[key] = text_sprite(txt, size, **kw)
    return _TS[key]


def fit(spr, maxw, maxh=None):
    s = 1.0
    if spr.width > maxw:
        s = maxw / spr.width
    if maxh and spr.height * s > maxh:
        s = min(s, maxh / spr.height)
    if s < 1.0:
        spr = spr.resize((max(1, int(spr.width * s)), max(1, int(spr.height * s))), Image.LANCZOS)
    return spr


def caps(txt, size, color=WHITE, tracking=8, glow=None, glow_a=120, glow_r=18, stroke=0,
         stroke_fill=(6, 8, 16), squeeze=0.88):
    return T(txt, size, fill=color, tracking=tracking, squeeze=squeeze, glow=glow,
             glow_r=glow_r, glow_a=glow_a, stroke=stroke, stroke_fill=stroke_fill)


def pill(txt, size=36, color=WHITE, acc=CYAN, pad=(34, 18), track=6, alpha=255):
    """caps text inside a frosted pill with an accent dot"""
    s = caps(txt, size, color, track)
    dot = 10
    w = s.width + pad[0] * 2 + dot * 3
    h = s.height + pad[1] * 2
    g = glass(w, h, r=h // 2, a=30, ba=90, bw=2, sheen=0.08)
    d = ImageDraw.Draw(g)
    d.ellipse([pad[0] - dot, h / 2 - dot / 2, pad[0], h / 2 + dot / 2], fill=acc + (235,))
    g.alpha_composite(s, (pad[0] + dot * 2, pad[1]))
    if alpha < 255:
        g.putalpha(g.split()[3].point(lambda v: int(v * alpha / 255)))
    return g


def circle_photo(name, d, ring=CYAN, tint_c=None, tint_a=0.0, bright=1.0, sat=1.0):
    key = ("cp", name, d, ring, tint_c, tint_a, bright, sat)
    if key in SPR:
        return SPR[key]
    im = Image.open(os.path.join(A, name)).convert("RGBA")
    # head & shoulders crop
    w, h = im.size
    box = (int(w * 0.04), int(h * 0.01), int(w * 0.96), int(h * 0.01) + int(w * 0.92))
    head = im.crop(box).resize((d, d), Image.LANCZOS)
    if bright != 1.0 or sat != 1.0:
        rgb = ImageEnhance.Brightness(head.convert("RGB")).enhance(bright)
        rgb = ImageEnhance.Color(rgb).enhance(sat)
        rgb.putalpha(head.split()[3])
        head = rgb
    mask = Image.new("L", (d, d), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, d - 1, d - 1], fill=255)
    out = Image.new("RGBA", (d + 22, d + 22), (0, 0, 0, 0))
    ring_l = Image.new("RGBA", (d + 22, d + 22), (0, 0, 0, 0))
    ImageDraw.Draw(ring_l).ellipse([0, 0, d + 21, d + 21], outline=ring + (255,), width=5)
    inner = Image.new("RGBA", (d + 22, d + 22), (0, 0, 0, 0))
    ImageDraw.Draw(inner).ellipse([5, 5, d + 16, d + 16], fill=(10, 12, 22, 255))
    body = Image.new("RGBA", (d, d), (10, 12, 22, 255))
    body.paste(head, (0, 0), mask)
    body.putalpha(mask)
    out.alpha_composite(inner)
    out.alpha_composite(body, (11, 11))
    out.alpha_composite(ring_l)
    SPR[key] = out
    return out


def radial_glow(center, r, color, a=90):
    cx, cyy = center
    R = r * H
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - cx * W) ** 2 + (y - cyy * H) ** 2) / max(R, 1)
    v = np.clip(1 - d, 0, 1) ** 2.0
    lay = Image.new("RGBA", (W, H), color + (0,))
    lay.putalpha(Image.fromarray((v * a).astype(np.uint8), "L"))
    return lay


def scrim(f, y, h, strength=190, color=(4, 5, 12)):
    s = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    for i in range(h):
        d.rectangle([0, i, W, i + 1], fill=color + (int(strength * (i / h) ** 1.6),))
    f.alpha_composite(s, (0, y))
    return f


def particles(f, t, n=26, color=(180, 225, 255), seed=1, speed=18, alpha=70, ytop=0, ybot=None):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    ybot = H if ybot is None else ybot
    for i in range(n):
        x = rng.uniform(0, W)
        y0 = rng.uniform(ytop, ybot)
        r = rng.uniform(1.2, 3.2)
        yy = ytop + (y0 - ytop - t * speed * rng.uniform(0.5, 1.5)) % max(1, ybot - ytop)
        d.ellipse([x, yy, x + 2 * r, yy + 2 * r], fill=color + (int(alpha * rng.uniform(0.3, 1)),))
    return Image.alpha_composite(f, lay)


def contact_shadow(f, cx, cy, w=430, h=70, a=110, color=(0, 0, 0)):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.ellipse([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], fill=color + (a,))
    lay = lay.filter(ImageFilter.GaussianBlur(h * 0.45))
    return Image.alpha_composite(f, lay)


def glass_card(w, h, r=30, a=26, sheen=0.08, border=(255, 255, 255), ba=60):
    return glass(w, h, r=r, a=a, sheen=sheen, border=border, ba=ba)


def stat_row(label, pct, w=620, h=112, acc=CYAN, prog=1.0, size=40):
    """tech stat bar: label left, % right, thin filling track"""
    row = glass_card(w, h, r=h // 2, a=26, sheen=0.07, ba=70)
    d = ImageDraw.Draw(row)
    t = caps(label, size, WHITE, 6)
    row.alpha_composite(t, (34, (h - t.height) // 2 - 4))
    p = caps(f"{int(pct)}%", 34, acc, 4, glow=acc, glow_a=90, glow_r=12)
    row.alpha_composite(p, (w - p.width - 34, (h - p.height) // 2 - 2))
    # track
    ty = h - 18
    d.rounded_rectangle([30, ty, w - 30, ty + 6], 3, fill=(255, 255, 255, 40))
    fw = int((w - 60) * clamp(prog))
    if fw > 8:
        bar = Image.new("RGBA", (fw, 6), (0, 0, 0, 0))
        dbar = ImageDraw.Draw(bar)
        for x in range(fw):
            k = x / max(fw - 1, 1)
            c = (int(acc[0] * (0.75 + 0.25 * k)), int(acc[1] * (0.9 + 0.1 * k)), int(min(255, acc[2] * (1.05))), 245)
            dbar.line([(x, 0), (x, 6)], fill=c)
        row.alpha_composite(bar, (30, ty))
    return row


# ------------------------------------------------------------------ scenes
def s_hook(t, a, b):
    ts = t - a
    f = bg_fill(os.path.join(A, "bg_night.png"), scale=1.04, ox=math.sin(ts * 0.25) * 0.2,
                grade=((6, 8, 26), 0.3, 1.0, 1.1, 0.9)).convert("RGBA")
    f.alpha_composite(radial_glow((0.5, 0.34), 0.6, (90, 40, 160), 95))
    f.alpha_composite(radial_glow((0.5, 0.62), 0.5, (0, 90, 150), 60))
    f = particles(f, ts, 26, (190, 230, 255), 6, 14, 65)
    f = sweep(f, ts, 6.0, 16)

    p = pop(ts, 0.28, 0.45, 1.6)
    if p > 0:
        put(f, pill("ММА  •  МНЕНИЕ  •  БЕЗ ФИЛЬТРА", 34, WHITE, CYAN), cy_, 320,
            scale=1.0, alpha=clamp(p) * 0.95)

    p = pop(ts, 0.52, 0.5, 1.5)
    if p > 0:
        put(f, fit(caps("КТО ТАКОЙ", 124, WHITE, 14, glow=(90, 140, 255), glow_a=110, glow_r=26), W - 160),
            cy_, 520 + (1 - ease_out(clamp((ts - 0.52) / 0.55))) * 34, alpha=clamp(p), scale=1.0)

    p = pop(ts, 0.95, 0.55, 1.45)
    if p > 0:
        g = fit(caps("САСНЫЙ?", 212, WHITE, 12, glow=CYAN, glow_a=130, glow_r=32), W - 120)
        g = grad_text(g, (200, 250, 255), (60, 170, 255))
        put(f, g, cy_, 672 + 6 * math.sin(ts * 2.0), alpha=clamp(p),
            scale=1.0 + 0.03 * (1 - ease_out(clamp((ts - 0.95) / 0.6))))

    p = fade(ts, 1.5, 0.7)
    if p > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        wdt = int(620 * ease_io(p))
        d.line([(cy_ - wdt // 2, 830), (cy_ + wdt // 2, 830)], fill=(255, 255, 255, int(90 * p)), width=2)
        d.line([(cy_ - 40, 830), (cy_ + 40, 830)], fill=CYAN + (int(240 * p),), width=3)
        f = Image.alpha_composite(f, lay)

    for i, (nm, t0, x, ring, cap, col) in enumerate([
            ("benua_cut.png", 2.30, 330, CYAN, "ЛЮБИМЕЦ", CYAN),
            ("khabib_cut.png", 2.62, 750, CORAL, "ХЕЙТ", CORAL)]):
        pp = pop(ts, t0, 0.5, 1.6)
        if pp > 0:
            ph = circle_photo(nm, 244, ring, bright=1.06, sat=1.04)
            put(f, ph, x, 1210 + (1 - ease_out(clamp((ts - t0) / 0.55))) * 40, alpha=clamp(pp))
            lb = caps(cap, 34, col, 8, glow=col, glow_a=110, glow_r=14)
            put(f, lb, x, 1372, alpha=clamp(pp) * 0.95)

    p = pop(ts, 3.05, 0.5, 1.5)
    if p > 0:
        lab = caps("ЗА  30  СЕКУНД", 38, WHITE, 12)
        w, h = lab.width + 76, lab.height + 34
        g = glass(w, h, r=h // 2, a=18, ba=80, bw=2, sheen=0.05)
        g.alpha_composite(lab, (38, 17))
        put(f, g, cy_, 1520, alpha=clamp(p))
    return f


def s_bsd(t, a, b):
    ts = t - a
    f = bg_fill(os.path.join(A, "bg_stage.png"), scale=1.03 + 0.02 * ts / (b - a),
                ox=-0.08, grade=((0, 20, 40), 0.2, 1.0, 1.08, 0.92), blur=1.2).convert("RGBA")
    f = particles(f, ts, 22, (170, 235, 255), 4, 12, 55, 100, 1900)

    hgt = 1265
    sp = sprite("benua_cut.png", hgt, fade_bottom=0.0, bright=1.02, sat=1.02)
    base = 1885
    f = glow_behind(f, sp, 800, base - hgt / 2, CYAN, 130, 60)
    # soft light pool on the floor
    f.alpha_composite(radial_glow((0.74, 0.97), 0.22, (120, 220, 255), 70))
    f = contact_shadow(f, 800, base - 6, 400, 74, 130)
    rise = (1 - ease_out(clamp((ts - 0.05) / 0.7))) * 60
    put(f, sp, 800, base - hgt / 2 + rise, scale=1 + 0.006 * math.sin(ts * 1.6))

    x = 86
    p = fade(ts, 0.28, 0.5)
    if p > 0:
        put(f, caps("ЛЮБИМЫЙ БОЕЦ САСНОГО", 34, (165, 245, 255), 9, glow=CYAN, glow_a=70, glow_r=12),
            x, 372, anchor="lc", alpha=p)

    p = pop(ts, 0.62, 0.55, 1.4)
    if p > 0:
        put(f, fit(caps("БЕНУА", 124, WHITE, 10, glow=(120, 170, 255), glow_a=90, glow_r=22), 540),
            x, 470 + (1 - ease_out(clamp((ts - 0.62) / 0.6))) * 26, anchor="lc", alpha=clamp(p))

    p = pop(ts, 1.00, 0.55, 1.4)
    if p > 0:
        g = fit(caps("СЕН-ДЕНИ", 120, WHITE, 10, glow=CYAN, glow_a=110, glow_r=24), 580)
        g = grad_text(g, (215, 250, 255), (70, 185, 255))
        put(f, g, x, 606 + (1 - ease_out(clamp((ts - 1.00) / 0.6))) * 26, anchor="lc", alpha=clamp(p))

    p = fade(ts, 1.45, 0.6)
    if p > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        wdt = int(430 * ease_io(p))
        d.line([(x, 700), (x + wdt, 700)], fill=(255, 255, 255, int(70 * p)), width=2)
        d.line([(x, 700), (x + 70, 700)], fill=CYAN + (int(240 * p),), width=3)
        f = Image.alpha_composite(f, lay)

    p = pop(ts, 2.80, 0.5, 1.5)
    if p > 0:
        put(f, pill("БЫВШИЙ СПЕЦНАЗ", 38, WHITE, CORAL), x + 6, 800, anchor="lc", alpha=clamp(p))

    f = scrim(f, H - 520, 520, 245)
    p = pop(ts, 4.65, 0.45, 1.4)
    if p > 0:
        put(f, fit(caps("ВЫХОДИТ ЛОМАТЬ,", 48, WHITE, 4, glow=(0, 0, 0), glow_a=190, glow_r=10), 560),
            x, 1572, anchor="lc", alpha=clamp(p))
    p = pop(ts, 5.30, 0.45, 1.4)
    if p > 0:
        put(f, fit(caps("А НЕ БОКСИРОВАТЬ.", 48, CYAN, 4, glow=CYAN, glow_a=120, glow_r=14), 600),
            x, 1652, anchor="lc", alpha=clamp(p))
    return f


def s_style(t, a, b):
    ts = t - a
    f = bg_fill(os.path.join(A, "bg_tech.png"), scale=1.04 + 0.02 * ts / (b - a),
                ox=0.1, grade=((4, 14, 34), 0.34, 0.9, 1.12, 0.85), blur=1.4).convert("RGBA")
    f = particles(f, ts, 24, (150, 225, 255), 9, 10, 55, 80, 1900)
    f = sweep(f, ts + 3, 7.0, 14)

    hgt = 1150
    sp = sprite("benua_cut.png", hgt, bright=1.04, sat=0.98, tint_c=(20, 60, 110), tint_a=0.10)
    f = glow_behind(f, sp, 838, 1860 - hgt / 2, CYAN, 120, 55)
    f = contact_shadow(f, 838, 1856, 380, 66, 115)
    put(f, sp, 838, 1860 - hgt / 2, scale=1 + 0.006 * math.sin(ts * 1.5))

    put(f, caps("ПОЧЕМУ САСНЫЙ ЕГО ТАЩИТ", 32, WHITE, 8, glow=CYAN, glow_a=80, glow_r=12),
        86, 316, anchor="lc", alpha=0.95)

    rows = [("ДАВЛЕНИЕ", 100, 0.30, CYAN, 480),
            ("ТЕМП", 100, 1.45, AMBER, 626),
            ("МЯСОРУБКА", 100, 2.65, CORAL, 772)]
    for label, pct, t0, acc, y in rows:
        k = clamp((ts - t0) / 0.75)
        if k <= 0:
            continue
        pr = pop(ts, t0, 0.45, 1.5)
        row = stat_row(label, pct, 610, 116, acc, ease_out(k))
        put(f, row, 86, y, anchor="lc", alpha=clamp(pr))

    p = pop(ts, 4.40, 0.5, 1.5)
    if p > 0:
        f = sweep(f, ts + 1, 3.0, 18)
        put(f, pill("НОЛЬ ВОЗНИ", 38, WHITE, CORAL), 92, 940, anchor="lc", alpha=clamp(p))
        put(f, caps("ЧИСТЫЙ ПРЕССИНГ", 26, (200, 220, 240), 6), 100, 1012, anchor="lc",
            alpha=clamp(p) * 0.8)
    return f


def s_hate(t, a, b):
    ts = t - a
    f = bg_fill(os.path.join(A, "bg_crimson.png"), scale=1.05 + 0.02 * ts / (b - a),
                grade=((70, 0, 6), 0.32, 0.85, 1.16, 0.86), blur=1.2).convert("RGBA")
    f = particles(f, ts, 18, (255, 170, 160), 13, 12, 55, 100, 1900)
    f.alpha_composite(radial_glow((0.5, 0.42), 0.55, (255, 40, 40), 55))

    p = pop(ts, 0.32, 0.5, 1.4)
    if p > 0:
        put(f, fit(caps("САСНЫЙ ЛЮТО", 100, WHITE, 8, glow=(255, 60, 40), glow_a=100, glow_r=22), 860),
            cy_, 392, alpha=clamp(p))
    p = pop(ts, 0.75, 0.5, 1.4)
    if p > 0:
        g = fit(caps("ХЕЙТИТ", 126, WHITE, 10, glow=CORAL, glow_a=120, glow_r=26), 700)
        g = grad_text(g, (255, 220, 210), (255, 70, 60))
        put(f, g, cy_, 512, alpha=clamp(p))
    p = pop(ts, 1.10, 0.5, 1.4)
    if p > 0:
        put(f, fit(caps("НУРМАГОМЕДОВЫХ", 62, (255, 205, 200), 6), 900), cy_, 620, alpha=clamp(p) * 0.95)

    # quote card
    p = pop(ts, 2.25, 0.55, 1.4)
    if p > 0:
        q = caps("НУРМАДОГИ", 84, WHITE, 4, glow=CORAL, glow_a=120, glow_r=22)
        q = fit(q, 620)
        w, h = 860, 250
        card = glass_card(w, h, r=40, a=30, sheen=0.06, ba=80)
        d = ImageDraw.Draw(card)
        d.line([(0, 40), (0, h - 40)], fill=CORAL + (220,), width=5)
        qm = T("«", 130, fill=CORAL, squeeze=0.7, tracking=0)
        card.alpha_composite(qm, (40, 26))
        card.alpha_composite(q, ((w - q.width) // 2, 62))
        sub = caps("ТАК ИХ НАЗЫВАЕТ САСНЫЙ", 26, (230, 205, 210), 6)
        card.alpha_composite(sub, ((w - sub.width) // 2, h - 66))
        put(f, card, cy_, 900, scale=0.96 + 0.04 * p, alpha=clamp(p))

    for i, (nm, t0, x, ring, lab, col, kw) in enumerate([
            ("benua_cut.png", 1.95, 330, CYAN, "БЕНУА", CYAN, {}),
            ("khabib_cut.png", 2.20, 750, CORAL, "ХАБИБ", CORAL,
             {"bright": 0.78, "sat": 0.6, "tint_c": (90, 20, 20), "tint_a": 0.18})]):
        pp = pop(ts, t0, 0.5, 1.5)
        if pp > 0:
            put(f, circle_photo(nm, 206, ring, **kw), x, 1330, alpha=clamp(pp))
            put(f, caps(lab, 32, col, 8, glow=col, glow_a=100, glow_r=12), x, 1472,
                alpha=clamp(pp) * 0.95)

    p = fade(ts, 4.4, 0.6)
    if p > 0:
        put(f, caps("МНЕНИЕ ПЕРСОНАЖА", 24, (235, 200, 200), 8), cy_, 1690, alpha=p * 0.7)
    return f


def s_vs(t, a, b):
    ts = t - a
    f = bg_fill(os.path.join(A, "bg_tech.png"), scale=1.08 + 0.02 * ts / (b - a),
                grade=((10, 4, 30), 0.36, 0.95, 1.14, 0.72), blur=1.6).convert("RGBA")
    f.alpha_composite(radial_glow((0.3, 0.4), 0.45, (0, 120, 200), 70))
    f.alpha_composite(radial_glow((0.72, 0.4), 0.45, (200, 30, 50), 60))
    f = particles(f, ts, 22, (200, 220, 255), 21, 10, 50)

    put(f, caps("САСНЫЙ СЧИТАЕТ", 32, (220, 235, 255), 8), cy_, 300, alpha=0.9)

    pb = pop(ts, 0.12, 0.55, 1.4)
    pk = pop(ts, 0.30, 0.55, 1.4)
    if pb > 0:
        put(f, circle_photo("benua_cut.png", 356, CYAN),
            330 - (1 - ease_out(clamp((ts - 0.12) / 0.6))) * 60, 800, alpha=clamp(pb))
    if pk > 0:
        put(f, circle_photo("khabib_cut.png", 356, CORAL),
            750 + (1 - ease_out(clamp((ts - 0.30) / 0.6))) * 60, 800, alpha=clamp(pk))

    pv = pop(ts, 0.55, 0.45, 1.6)
    if pv > 0:
        w = 168
        g = glass(w, w, r=w // 2, a=42, ba=110, bw=2, sheen=0.06)
        vtxt = caps("VS", 64, WHITE, 2, glow=(255, 120, 160), glow_a=110, glow_r=20)
        g.alpha_composite(vtxt, ((w - vtxt.width) // 2, (w - vtxt.height) // 2 - 2))
        put(f, g, cy_, 800, scale=0.92 + 0.08 * pv, alpha=clamp(pv))

    for x, lab, col, t0 in [(330, "БЕНУА", CYAN, 0.7), (750, "ХАБИБ", CORAL, 0.85)]:
        pp = fade(ts, t0, 0.5)
        if pp > 0:
            put(f, caps(lab, 36, col, 8, glow=col, glow_a=100, glow_r=12), x, 1010, alpha=pp)

    p = pop(ts, 0.9, 0.5, 1.4)
    if p > 0:
        put(f, fit(caps("БЕНУА ОСТАНОВИЛ БЫ", 62, WHITE, 5), 880), cy_, 1180, alpha=clamp(p))
    p = pop(ts, 1.35, 0.5, 1.5)
    if p > 0:
        g = fit(caps("ХАБИБА", 104, WHITE, 8, glow=CORAL, glow_a=130, glow_r=26), 520)
        g = grad_text(g, (255, 220, 210), (255, 70, 60))
        put(f, g, cy_, 1300, alpha=clamp(p), scale=1.0 + 0.02 * (1 - ease_out(clamp((ts - 1.35) / 0.6))))

    p = pop(ts, 2.35, 0.5, 1.5)
    if p > 0:
        put(f, pill("ХАБИБУ ДАВАЛИ ПРОХОДНЫХ", 34, WHITE, CORAL), cy_, 1450, alpha=clamp(p))
        put(f, caps("ПО СТИЛЮ", 26, (230, 210, 215), 8), cy_, 1520, alpha=clamp(p) * 0.75)
    return f


def s_cta(t, a, b):
    ts = t - a
    f = bg_fill(os.path.join(A, "bg_night.png"), scale=1.05 + 0.03 * ts / (b - a),
                grade=((10, 6, 34), 0.32, 1.0, 1.12, 0.82)).convert("RGBA")
    f.alpha_composite(radial_glow((0.5, 0.4), 0.62, (120, 30, 170), 80))
    f = particles(f, ts, 24, (210, 220, 255), 31, 12, 55)
    f = sweep(f, ts, 6.5, 16)

    p = pop(ts, 0.25, 0.5, 1.4)
    if p > 0:
        put(f, fit(caps("СНИМАТЬ", 128, WHITE, 12, glow=(150, 120, 255), glow_a=100, glow_r=24), 700),
            cy_, 560, alpha=clamp(p))
    p = pop(ts, 0.85, 0.55, 1.45)
    if p > 0:
        g = fit(caps("ЕЩЁ ТАКОЕ?", 112, WHITE, 8, glow=CYAN, glow_a=120, glow_r=26), 880)
        g = grad_text(g, (210, 250, 255), (90, 180, 255))
        put(f, g, cy_, 700, alpha=clamp(p))

    p = pop(ts, 1.45, 0.5, 1.5)
    if p > 0:
        yes = glass(310, 124, r=62, a=52, ba=255, bw=3, sheen=0.10)
        tint_l = Image.new("RGBA", yes.size, CYAN + (46,))
        yes = Image.alpha_composite(yes, tint_l)
        d = ImageDraw.Draw(yes)
        d.rounded_rectangle([0, 0, 309, 123], 62, outline=CYAN + (255,), width=3)
        ty = caps("ДА", 66, WHITE, 6, glow=CYAN, glow_a=140, glow_r=20)
        yes.alpha_composite(ty, ((310 - ty.width) // 2, (124 - ty.height) // 2 - 2))
        no = glass(310, 124, r=62, a=30, ba=150, bw=2, sheen=0.05)
        tx = caps("НЕТ", 66, (215, 225, 245), 6)
        no.alpha_composite(tx, ((310 - tx.width) // 2, (124 - tx.height) // 2 - 2))
        pl = 1 + 0.02 * pulse(ts, 0.9)
        put(f, yes, 330, 960, scale=pl, alpha=clamp(p))
        put(f, no, 750, 960, alpha=clamp(p) * 0.92)

    p = pop(ts, 2.10, 0.5, 1.4)
    if p > 0:
        put(f, caps("ПЛЮС В КОММЕНТЫ", 40, WHITE, 8, glow=CYAN, glow_a=90, glow_r=16), cy_, 1130,
            alpha=clamp(p))

    p = pop(ts, 2.45, 0.55, 1.4)
    if p > 0:
        # chat bubbles
        for i, (bx, by, bw2) in enumerate([(330, 1300, 250), (720, 1240, 210)]):
            ph = 0.5 * ts + i * 0.8
            off = 8 * math.sin(ph * 2.2)
            b = glass(bw2, 96, r=34, a=34, ba=70, bw=2, sheen=0.06)
            dd = ImageDraw.Draw(b)
            for k in range(3):
                dd.ellipse([34 + k * 42, 40, 58 + k * 42, 64], fill=(230, 240, 255, 210))
            dd.polygon([(40, 94), (86, 94), (54, 126)], fill=(255, 255, 255, 34))
            put(f, b, bx, by + off, alpha=clamp(p) * (0.9 - i * 0.12))

    p = fade(ts, 3.0, 0.6)
    if p > 0:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.line([(170, 1660), (400, 1660)], fill=(255, 255, 255, int(70 * p)), width=2)
        d.line([(680, 1660), (910, 1660)], fill=(255, 255, 255, int(70 * p)), width=2)
        f = Image.alpha_composite(f, lay)
        put(f, caps("С А С Н Ы Й", 44, WHITE, 10), cy_, 1660, alpha=p * 0.95)

    p = fade(ts, 3.45, 0.5)
    if p > 0:
        put(f, caps("ММА  •  МНЕНИЕ  •  БЕЗ  ФИЛЬТРА", 22, (190, 205, 230), 8), cy_, 1730, alpha=p * 0.7)
    return f


SCENE_FN = {"hook": s_hook, "bsd": s_bsd, "style": s_style, "hate": s_hate, "vs": s_vs, "cta": s_cta}
SCENE_IDX = {s[0]: i for i, s in enumerate(plan.SCENES)}


def scene_frame(name, a, b, t):
    tt = min(max(t, a), b - 1.0 / plan.FPS)
    f = SCENE_FN[name](tt, a, b)
    # gentle ken-burns per scene for a floating, modern feel
    f = camera(f, tt, a, b, 1.0, 1.032)
    return f


def frame_at(t):
    # find scene
    cur = None
    for i, (name, a, b) in enumerate(plan.SCENES):
        if a <= t < b:
            cur = i
            break
    if cur is None:
        cur = len(plan.SCENES) - 1
    name, a, b = plan.SCENES[cur]
    f = scene_frame(name, a, b, t)

    # smooth cross dissolve around each cut
    for i, c in enumerate(plan.CUTS):
        if c - plan.XFADE / 2 <= t < c + plan.XFADE / 2:
            prev = plan.SCENES[i]
            nx = plan.SCENES[i + 1]
            k = ease_io((t - (c - plan.XFADE / 2)) / plan.XFADE) ** 0.72
            fa = scene_frame(prev[0], prev[1], prev[2], t)
            fb = scene_frame(nx[0], nx[1], nx[2], t)
            f = Image.blend(fa, fb, k)
            soft = math.sin(math.pi * k) ** 1.5
            if soft > 0.03:
                f = f.filter(ImageFilter.GaussianBlur(2.6 * soft)).convert("RGBA")
            break

    # top progress line
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, W, 4], fill=(255, 255, 255, 26))
    d.rectangle([0, 0, int(W * clamp(t / plan.TOTAL)), 4], fill=(140, 225, 255, 150))
    f = Image.alpha_composite(f, lay)

    rgb = f.convert("RGB")
    rgb = finish(rgb, t, grain=0.035, vig=0.42, scan=0.0)

    if t < 0.35:
        rgb = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), rgb, ease_out(t / 0.35))
    if t > plan.TOTAL - 0.55:
        rgb = Image.blend(rgb, Image.new("RGB", (W, H), (0, 0, 0)),
                          ease_in(clamp((t - (plan.TOTAL - 0.55)) / 0.5)))
    return rgb


def render(out_path):
    fx.init_overlays()
    import imageio_ffmpeg
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    n = int(round(plan.TOTAL * plan.FPS))
    cmd = [FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(plan.FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "medium",
           "-crf", "19", "-pix_fmt", "yuv420p", "-tune", "film", out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame_at(i / plan.FPS).tobytes())
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
            frame_at(v).save(os.path.join(HERE, "frames", f"v2_{v:05.2f}.png"))
            print("still", v)
    else:
        render(os.path.join(HERE, "out", "video_v2.mp4"))
