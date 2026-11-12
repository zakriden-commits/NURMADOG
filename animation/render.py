#!/usr/bin/env python3
"""Five original 2-D, keyframe-animated shorts rendered with the pygame engine.

All characters, sets and props are drawn as vectors. There are no photographs,
pre-rendered illustrations, or image-to-video effects in the animation.
"""
import argparse
import math
import os
import random
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import imageio_ffmpeg
import numpy as np
import pygame
import pygame.gfxdraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "videos"
W, H, FPS, DURATION = 1280, 720, 25, 10
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def col(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i+2], 16) for i in (0, 2, 4))


def mix(a, b, k):
    return tuple(int(a[i] * (1-k) + b[i] * k) for i in range(3))


def clamp(x, a=0, b=1):
    return min(b, max(a, x))


def smooth(a, b, x):
    p = clamp((x-a) / (b-a))
    return p*p*(3-2*p)


def lerp(a, b, t):
    return a + (b-a)*t


def point(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t))


@dataclass(frozen=True)
class Style:
    key: str
    title: str
    filename: str
    kind: str
    colors: dict


def style(key, title, filename, kind, **values):
    return Style(key, title, filename, kind, {k: col(v) for k, v in values.items()})

STYLES = [
    style("sunny", "СОЛНЕЧНЫЙ МУЛЬТ", "01_sunny_cartoon.mp4", "sunny",
          ink="243650", sky="B9E8F3", sky2="EEF7E7", wall="F9E7C7", floor="C78566", grass="8BCB90", roof="DC7867", house="F7C995", wood="A8664C", window="96DCEB", hero="40B9AC", hero_dark="208B84", skin="F3BE91", hair="303446", police="43689B", police_dark="253E68", accent="FFC958", white="FFF9EC", red="F16C69", blue="518DD4"),
    style("comic", "КОМИКС-ДЕТЕКТИВ", "02_detective_comic.mp4", "comic",
          ink="1F2934", sky="DFD1A9", sky2="F5E6BD", wall="EAD4A8", floor="AA785F", grass="8DAD92", roof="C65B52", house="EABF88", wood="81564B", window="8DB9B6", hero="6BA6A0", hero_dark="417A79", skin="E8B48E", hair="252A33", police="394F61", police_dark="25323F", accent="F3C35C", white="FFF4D7", red="D95449", blue="568E9A"),
    style("neon", "НЕОНОВАЯ НОЧЬ", "03_neon_night.mp4", "neon",
          ink="13102C", sky="11142F", sky2="323158", wall="353452", floor="232B45", grass="264D57", roof="633D75", house="535276", wood="3A3559", window="75D8D5", hero="26C8BD", hero_dark="167D85", skin="F1AF91", hair="17172E", police="3D5D98", police_dark="222D59", accent="FFD773", white="E8F7F3", red="FF58B1", blue="33DAEF"),
    style("paper", "БУМАЖНЫЙ ТЕАТР", "04_paper_theater.mp4", "paper",
          ink="534B4A", sky="C9E1D7", sky2="FAEBD8", wall="EFE0C8", floor="CB9D80", grass="A1BE9E", roof="CA8875", house="EAC8A4", wood="9D7664", window="ABD2D1", hero="81B6A9", hero_dark="608D86", skin="E5B495", hair="514A4A", police="71879C", police_dark="4F6076", accent="EBC780", white="F8F3E8", red="D8887C", blue="7EA6C1"),
    style("pixel", "ПИКСЕЛЬНОЕ ПРИКЛЮЧЕНИЕ", "05_pixel_adventure.mp4", "pixel",
          ink="26304A", sky="84D4DF", sky2="DAF2D5", wall="F7DEAD", floor="C47E5D", grass="78BF84", roof="D96F65", house="F2BD80", wood="9B5B50", window="70C3DB", hero="39ABAA", hero_dark="217780", skin="EFB38D", hair="30304A", police="4B71A5", police_dark="263F6D", accent="FFD369", white="FFF3D7", red="F36772", blue="55A9DC"),
]


@lru_cache(maxsize=256)
def font(path, size):
    return pygame.font.Font(path, max(1, size))


@lru_cache(maxsize=1024)
def text_image(path, size, text, rgb):
    return font(path, size).render(text, True, rgb)


# A small original 5x7 Cyrillic bitmap font keeps the pixel-art version crisp.
PIXEL_GLYPHS = {
    'А': ['01110','10001','10001','11111','10001','10001','10001'],
    'Б': ['11111','10000','10000','11110','10001','10001','11110'],
    'В': ['11110','10001','10001','11110','10001','10001','11110'],
    'Г': ['11111','10000','10000','10000','10000','10000','10000'],
    'Д': ['00110','01010','01010','01010','11111','10001','10001'],
    'Е': ['11111','10000','10000','11110','10000','10000','11111'],
    'Ё': ['01010','00000','11111','10000','11110','10000','11111'],
    'Ж': ['10101','10101','01110','00100','01110','10101','10101'],
    'З': ['11110','00001','00001','01110','00001','00001','11110'],
    'И': ['10001','10011','10101','10101','11001','10001','10001'],
    'Й': ['01010','00100','10001','10011','10101','11001','10001'],
    'К': ['10001','10010','10100','11000','10100','10010','10001'],
    'Л': ['00111','01001','01001','01001','01001','01001','10001'],
    'М': ['10001','11011','10101','10101','10001','10001','10001'],
    'Н': ['10001','10001','10001','11111','10001','10001','10001'],
    'О': ['01110','10001','10001','10001','10001','10001','01110'],
    'П': ['11111','10001','10001','10001','10001','10001','10001'],
    'Р': ['11110','10001','10001','11110','10000','10000','10000'],
    'С': ['01111','10000','10000','10000','10000','10000','01111'],
    'Т': ['11111','00100','00100','00100','00100','00100','00100'],
    'У': ['10001','10001','01001','00111','00001','00010','11100'],
    'Ф': ['00100','01110','10101','10101','01110','00100','00100'],
    'Х': ['10001','10001','01010','00100','01010','10001','10001'],
    'Ц': ['10010','10010','10010','10010','10010','11111','00001'],
    'Ч': ['10001','10001','10001','01111','00001','00001','00001'],
    'Ш': ['10001','10001','10001','10101','10101','10101','11111'],
    'Щ': ['10101','10101','10101','10101','11111','00001','00001'],
    'Ъ': ['11000','01000','01000','01110','01001','01001','01110'],
    'Ы': ['10001','10001','10001','11101','10101','10101','11101'],
    'Ь': ['10000','10000','10000','11110','10001','10001','11110'],
    'Э': ['11110','00001','00001','01111','00001','00001','11110'],
    'Ю': ['10110','11001','10001','11001','10001','11001','10110'],
    'Я': ['01111','10001','10001','01111','00101','01001','10001'],
    '0': ['01110','10001','10011','10101','11001','10001','01110'],
    '1': ['00100','01100','00100','00100','00100','00100','01110'],
    '2': ['01110','10001','00001','00010','00100','01000','11111'],
    '3': ['11110','00001','00001','01110','00001','00001','11110'],
    '4': ['00010','00110','01010','10010','11111','00010','00010'],
    '5': ['11111','10000','10000','11110','00001','00001','11110'],
    '6': ['01110','10000','10000','11110','10001','10001','01110'],
    '7': ['11111','00001','00010','00100','01000','01000','01000'],
    '8': ['01110','10001','10001','01110','10001','10001','01110'],
    '9': ['01110','10001','10001','01111','00001','00001','01110'],
    ':': ['00000','00100','00100','00000','00100','00100','00000'],
    '-': ['00000','00000','00000','11111','00000','00000','00000'],
    '!': ['00100','00100','00100','00100','00100','00000','00100'],
    '?': ['01110','10001','00001','00010','00100','00000','00100'],
    ' ': ['00000']*7,
}

@lru_cache(maxsize=512)
def pixel_text_image(text, rgb, multiplier=1):
    text=text.upper()
    out=pygame.Surface((max(1,len(text)*6-1)*multiplier,7*multiplier),pygame.SRCALPHA)
    for i,ch in enumerate(text):
        glyph=PIXEL_GLYPHS.get(ch,PIXEL_GLYPHS['?'])
        for y,row in enumerate(glyph):
            for x,value in enumerate(row):
                if value=='1': pygame.draw.rect(out,rgb,((i*6+x)*multiplier,y*multiplier,multiplier,multiplier))
    return out


class Draw:
    """Coordinates are in the shared 1280x720 stage, scaled for pixel art."""
    def __init__(self, surf, st):
        self.s = surf
        self.st = st
        self.q = surf.get_width()/W
        self.aa = st.kind != "pixel"

    def xy(self, p):
        return (round(p[0]*self.q), round(p[1]*self.q))

    def n(self, v, at_least=0):
        return max(at_least, round(v*self.q))

    def rect(self, color, rect, radius=0, outline=None, width=3):
        x,y,w,h = rect
        r = pygame.Rect(*self.xy((x,y)), max(1,self.n(w)), max(1,self.n(h)))
        rad = self.n(radius)
        pygame.draw.rect(self.s, color, r, border_radius=rad)
        if outline:
            pygame.draw.rect(self.s, outline, r, width=self.n(width,1), border_radius=rad)

    def frame(self, color, rect, width=3, radius=0):
        x,y,w,h = rect
        r = pygame.Rect(*self.xy((x,y)), max(1,self.n(w)), max(1,self.n(h)))
        pygame.draw.rect(self.s, color, r, width=self.n(width,1), border_radius=self.n(radius))

    def ellipse(self, color, rect, outline=None, width=3):
        x,y,w,h = rect
        r = pygame.Rect(*self.xy((x,y)), max(1,self.n(w)), max(1,self.n(h)))
        pygame.draw.ellipse(self.s, color, r)
        if outline:
            pygame.draw.ellipse(self.s, outline, r, width=self.n(width,1))

    def circle(self, color, center, radius, outline=None, width=3):
        p = self.xy(center)
        r = self.n(radius,1)
        pygame.draw.circle(self.s, color, p, r)
        if outline:
            pygame.draw.circle(self.s, outline, p, r, self.n(width,1))
        if self.aa and outline is None and r >= 3:
            pygame.gfxdraw.aacircle(self.s, p[0], p[1], r, color)

    def poly(self, color, pts, outline=None, width=3):
        coords = [self.xy(p) for p in pts]
        pygame.draw.polygon(self.s, color, coords)
        if outline:
            pygame.draw.lines(self.s, outline, True, coords, self.n(width,1))
            if self.aa:
                pygame.gfxdraw.aapolygon(self.s, coords, outline)
        elif self.aa:
            pygame.gfxdraw.aapolygon(self.s, coords, color)

    def line(self, color, a, b, width=3):
        pygame.draw.line(self.s, color, self.xy(a), self.xy(b), self.n(width,1))

    def lines(self, color, pts, width=3, closed=False):
        if len(pts) >= 2:
            pygame.draw.lines(self.s, color, closed, [self.xy(p) for p in pts], self.n(width,1))

    def limb(self, ink, fill, a, b, thick):
        self.line(ink, a, b, thick+7)
        self.circle(ink, a, (thick+7)/2)
        self.circle(ink, b, (thick+7)/2)
        self.line(fill, a, b, thick)
        self.circle(fill, a, thick/2)
        self.circle(fill, b, thick/2)

    def text_surface(self, text, size, color, path=FONT_SANS):
        if self.st.kind == 'pixel':
            multiplier=max(1,round(size*self.q/7))
            return pixel_text_image(text,tuple(color),multiplier)
        return text_image(path,self.n(size,1),text,tuple(color))

    def text(self, text, x, y, size, color, path=FONT_SANS, anchor="topleft"):
        im = self.text_surface(text,size,color,path)
        r = im.get_rect()
        setattr(r, anchor, self.xy((x,y)))
        self.s.blit(im, r)
        return r.width/self.q, r.height/self.q

    def arc(self, color, rect, start, end, width=3):
        x,y,w,h = rect
        r = pygame.Rect(*self.xy((x,y)), max(1,self.n(w)), max(1,self.n(h)))
        pygame.draw.arc(self.s, color, r, start, end, self.n(width,1))


def star(d, x, y, r, fill, outline=None, n=5, inner=.47):
    pts = []
    for i in range(n*2):
        a = -math.pi/2 + i*math.pi/n
        rr = r if i%2 == 0 else r*inner
        pts.append((x+rr*math.cos(a), y+rr*math.sin(a)))
    d.poly(fill, pts, outline, 2)


def cloud(d, x, y, s, c, edge=None):
    d.ellipse(c, (x-58*s,y,116*s,33*s), edge, 2)
    d.circle(c, (x-23*s,y+4*s), 25*s)
    d.circle(c, (x+8*s,y-6*s), 31*s)
    d.circle(c, (x+39*s,y+5*s), 22*s)
    d.rect(c, (x-52*s,y+5*s,104*s,21*s))


def tree(d, x, ground, s, st):
    c=st.colors
    d.rect(c['wood'], (x-10*s, ground-80*s, 20*s, 85*s), 4*s, c['ink'], 2)
    for dx,dy,rr in [(-33,-95,34),(0,-120,42),(34,-96,34),(0,-88,36)]:
        fill=mix(c['grass'], c['ink'], .15 if dx == -33 else 0)
        d.circle(fill,(x+dx*s,ground+dy*s),rr*s,c['ink'],2)
    d.circle(mix(c['grass'],c['white'],.26),(x-8*s,ground-122*s),10*s)


def paper_texture(surf, seed=42):
    # An actual translucent paper grain layer, not an image background.
    rng = random.Random(seed)
    q = surf.get_width()/W
    grain = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for i in range(2100):
        x = rng.randrange(surf.get_width())
        y = rng.randrange(surf.get_height())
        tone = (72,50,40,16) if i%2 else (255,255,255,34)
        r = max(1, int((1 if i%4 else 2)*q))
        pygame.draw.circle(grain,tone,(x,y),r)
    surf.blit(grain,(0,0))


def halftone(d, area, color, step=22, radius=2.2):
    x,y,w,h=area
    for iy, yy in enumerate(range(int(y),int(y+h),step)):
        for xx in range(int(x)+(iy%2)*(step//2),int(x+w),step):
            d.circle(color,(xx,yy),radius)


def floor(d, st, y=525):
    c=st.colors
    d.rect(c['floor'], (0,y,W,H-y))
    d.line(mix(c['floor'],c['ink'],.28), (0,y), (W,y), 7)
    for yy in (y+52,y+113,y+182):
        d.line(mix(c['floor'],c['ink'],.12),(0,yy),(W,yy),2)
    for x in range(-300,1600,245):
        d.line(mix(c['floor'],c['ink'],.1),(x,y+52),(x+95,y+113),2)


def picture(d, st, x, y):
    c=st.colors
    d.rect(c['wood'],(x,y,124,92),4,c['ink'],4)
    d.rect(c['white'],(x+10,y+10,104,72),0)
    d.poly(c['grass'],[(x+14,y+76),(x+48,y+37),(x+75,y+66),(x+90,y+48),(x+111,y+76)])
    d.circle(c['accent'],(x+88,y+28),9)


def interior(st, size):
    c=st.colors
    surf=pygame.Surface(size).convert()
    d=Draw(surf,st)
    d.rect(c['wall'],(0,0,W,H))
    if st.kind == 'neon':
        for y in range(0,525,4):
            k=y/525
            d.rect(mix(c['wall'], c['sky'], .34*(1-k)),(0,y,W,4))
    # Each version has a different art treatment, not just a new palette.
    if st.kind == 'comic':
        halftone(d,(0,54,W,470),mix(c['wall'],c['ink'],.16),18,2.2)
        for i in range(7):
            d.line(mix(c['wall'],c['ink'],.20),(700+i*22,92),(850+i*22,243),2)
    elif st.kind == 'neon':
        glow(d,350,210,160,c['blue'],45)
        glow(d,910,310,185,c['red'],55)
        d.rect(c['red'],(42,91,360,6),3)
        d.rect(c['blue'],(888,476,267,6),3)
    elif st.kind == 'paper':
        # Suspended paper bunting and offset cut edges.
        d.line(mix(c['wood'],c['white'],.35),(660,114),(1215,91),3)
        for i in range(7):
            x=685+i*72; y=113-i*3
            shade=[c['red'],c['hero'],c['accent']][i%3]
            d.poly(shade,[(x+4,y+4),(x+56,y+2),(x+30,y+57)],c['white'],3)
    # Framing and subtle wall panels.
    d.rect(mix(c['wall'],c['ink'],.06),(0,50,W,13))
    d.line(mix(c['wall'],c['ink'],.12),(0,360),(W,360),3)
    for x in (56,447,865,1234):
        d.line(mix(c['wall'],c['ink'],.1),(x,60),(x,525),3)
    floor(d,st)
    # Window, with the same house's outside colors.
    d.rect(c['wood'],(85,136,310,265),8,c['ink'],5)
    d.rect(c['window'] if st.kind!='neon' else c['sky'],(100,150,280,237))
    if st.kind == 'neon':
        d.circle(c['accent'],(305,196),28)
        for i in range(7):
            d.rect(mix(c['sky'],c['ink'],.3),(110+i*40,258-(i%3)*18,33,124))
            for j in range(4):
                d.rect(c['blue'],(116+i*40,275+j*24,5,7))
    else:
        d.circle(c['accent'],(310,200),28)
        d.ellipse(c['grass'],(100,286,280,100))
        cloud(d,180,196,.48,c['white'])
    d.line(c['wood'],(240,150),(240,386),9)
    d.line(c['wood'],(100,266),(380,266),9)
    d.rect(c['wood'],(71,390,338,19),5,c['ink'],3)
    # Sofa: deep enough behind the actor.
    d.ellipse(mix(c['floor'],c['ink'],.17),(190,557,675,55))
    d.rect(mix(c['hero_dark'],c['white'],.26),(210,382,642,176),34,c['ink'],5)
    d.rect(mix(c['hero'],c['white'],.32),(240,405,581,109),23,c['ink'],4)
    d.line(mix(c['hero_dark'],c['ink'],.3),(526,408),(526,503),3)
    d.rect(mix(c['hero'],c['white'],.15),(195,468,70,110),22,c['ink'],5)
    d.rect(mix(c['hero'],c['white'],.15),(797,468,70,110),22,c['ink'],5)
    d.rect(c['ink'],(231,567,42,22),4)
    d.rect(c['ink'],(800,567,42,22),4)
    picture(d,st,520,112)
    # Side table and plant.
    d.rect(c['wood'],(924,453,202,24),8,c['ink'],4)
    d.line(c['ink'],(946,475),(928,575),9)
    d.line(c['ink'],(1104,475),(1123,575),9)
    d.ellipse(mix(c['floor'],c['ink'],.18),(914,568,222,36))
    d.rect(c['white'],(980,408,72,45),6,c['ink'],3)
    d.poly(c['grass'],[(1015,412),(1000,372),(1005,355),(1018,385),(1022,345),(1031,334),(1030,386),(1051,361),(1059,361),(1042,411)], c['ink'],3)
    # Clock; hands are animated separately.
    d.circle(c['white'],(1124,205),53,c['ink'],5)
    for i in range(12):
        a=i*math.pi/6
        d.circle(c['ink'],(1124+42*math.sin(a),205-42*math.cos(a)),2.5)
    if st.kind == 'comic':
        halftone(d,(10,65,60,430),mix(c['wall'],c['ink'],.16),14,2)
    if st.kind == 'paper':
        paper_texture(surf,17)
    return surf


def exterior(st,size, close=False):
    c=st.colors
    surf=pygame.Surface(size).convert()
    d=Draw(surf,st)
    for y in range(0,550,5):
        d.rect(mix(c['sky'], c['sky2'], y/550*.7),(0,y,W,6))
    if st.kind=='neon':
        d.circle(c['accent'],(1040,130),46)
        for i in range(18):
            x=(i*179+67)%1280; y=(i*83+37)%285
            star(d,x,y,3+(i%3),c['white'],n=4)
        for i in range(9):
            x=810+i*60
            d.rect(mix(c['sky'],c['ink'],.3),(x,255-(i%3)*27,56,270))
            for yy in range(285-(i%3)*27,490,36):
                d.rect(mix(c['blue'],c['sky'],.36),(x+11,yy,7,12))
    else:
        d.circle(c['accent'],(1050,117),54)
        cloud(d,145,110,.75,c['white'])
        cloud(d,896,190,.55,mix(c['white'],c['sky'],.2))
    if st.kind == 'paper':
        d.line(mix(c['wood'],c['white'],.35),(830,60),(1240,100),3)
        for i in range(6):
            x=844+i*65; y=62+i*6
            d.poly([c['red'],c['hero'],c['accent']][i%3],[(x,y),(x+48,y+5),(x+18,y+46)],c['white'],3)
    if not close:
        # Large house, bushes, sidewalk and street.
        d.rect(c['grass'],(0,495,W,127))
        tree(d,87,531,1.13,st)
        tree(d,1190,539,1.04,st)
        d.rect(c['house'],(159,255,612,291),4,c['ink'],6)
        d.poly(c['roof'],[(120,256),(465,65),(811,256),(779,277),(465,110),(154,277)],c['ink'],6)
        d.rect(c['wood'],(565,111,66,95),3,c['ink'],4)
        # redo foreground roof edge across chimney base
        d.line(c['ink'],(150,257),(465,89),5)
        d.line(c['ink'],(465,89),(781,257),5)
        if st.kind == 'neon':
            d.line(c['red'],(155,252),(465,86),4)
            d.line(c['blue'],(465,86),(777,252),4)
        if st.kind == 'comic':
            for i in range(12):
                x=185+i*47
                d.line(mix(c['roof'],c['ink'],.45),(x,232-i*1.2),(x+14,226-i*1.2),2)
        d.rect(mix(c['house'],c['white'],.16),(180,282,570,13))
        # Door is left of the window in both exterior shots.
        d.rect(c['wood'],(252,326,143,218),4,c['ink'],5)
        d.rect(mix(c['wood'],c['white'],.14),(267,341,113,184),4,c['ink'],3)
        d.rect(c['window'],(282,358,83,70),3,c['ink'],3)
        d.circle(c['accent'],(355,469),5)
        d.rect(c['white'],(231,538,188,15),3,c['ink'],3)
        d.rect(c['wood'],(500,320,173,148),5,c['ink'],4)
        d.rect(c['window'],(511,331,151,126))
        d.line(c['wood'],(586,332),(586,457),7)
        d.line(c['wood'],(511,394),(662,394),7)
        d.line(c['white'],(524,345),(557,345),4)
        # walkway leading to door
        d.poly(mix(c['white'],c['floor'],.35),[(250,551),(397,551),(485,617),(170,617)])
        for xx,yy,rr in [(179,520,34),(216,527,26),(689,523,31),(728,522,29)]:
            d.circle(c['grass'],(xx,yy),rr,c['ink'],3)
        d.rect(mix(c['floor'],c['ink'],.42),(0,608,W,112))
        d.rect(mix(c['white'],c['floor'],.42),(0,594,W,17))
        for xx in range(-40,1350,190):
            d.rect(mix(c['white'],c['accent'],.28),(xx,674,100,6),2)
    else:
        d.rect(c['grass'],(0,553,W,95))
        d.rect(c['house'],(0,0,810,583),0,c['ink'],6)
        d.rect(c['roof'],(0,0,810,34),0,c['ink'],4)
        # siding makes the close shot recognisably the same house.
        for yy in range(85,540,78):
            d.line(mix(c['house'],c['ink'],.09),(0,yy),(810,yy),3)
        d.rect(c['wood'],(225,205,218,378),5,c['ink'],6)
        d.rect(mix(c['ink'],c['house'],.18),(238,218,192,352),3)
        # The swinging door is animated over this doorway.
        d.rect(c['wood'],(539,242,193,164),4,c['ink'],5)
        d.rect(c['window'],(552,255,167,138))
        d.line(c['wood'],(635,255),(635,393),8)
        d.line(c['wood'],(552,325),(719,325),8)
        d.line(c['white'],(568,274),(605,274),4)
        d.rect(c['white'],(212,576,246,16),3,c['ink'],3)
        d.ellipse(c['grass'],(740,513,210,92),c['ink'],3)
        d.ellipse(c['grass'],(-55,519,210,80),c['ink'],3)
        d.rect(mix(c['white'],c['floor'],.37),(0,596,W,124))
        for xx in (100,390,680,970,1260):
            d.line(mix(c['floor'],c['ink'],.15),(xx,596),(xx-42,720),3)
        d.line(mix(c['floor'],c['ink'],.16),(0,663),(W,663),3)
    if st.kind=='comic':
        halftone(d,(817 if close else 0,45,450 if close else 112,350),mix(c['sky'],c['ink'],.2),17,2)
    if st.kind=='paper':
        paper_texture(surf,25 if close else 23)
    return surf


def moving_clock(d,st,t):
    c=st.colors
    x,y=1124,205
    d.line(c['ink'],(x,y),(x-13,y-17),4)
    a=t*.75
    d.line(c['ink'],(x,y),(x+29*math.sin(a),y-29*math.cos(a)),3)
    d.circle(c['red'],(x,y),4)


def glow(d,x,y,r,c,alpha=70):
    q=d.q
    rr=max(1,round(r*q))
    layer=pygame.Surface((rr*2+4,rr*2+4),pygame.SRCALPHA)
    for j in range(5,0,-1):
        pygame.draw.circle(layer,(*c, max(1,alpha//(j+3))), (rr+2,rr+2), max(1,round(rr*j/5)))
    d.s.blit(layer,(round(x*q)-rr-2,round(y*q)-rr-2))


def animated_door(d, st, local):
    c=st.colors
    opened=smooth(0,.48,local)
    # Slab rotates about its left edge, exposing the dark interior.
    w=192*(1-.70*opened)
    pts=[(238,219),(238+w,230+16*opened),(238+w,562-10*opened),(238,570)]
    d.poly(mix(c['wood'],c['white'],.14),pts,c['ink'],4)
    if w>22:
        d.line(mix(c['wood'],c['ink'],.35),(248,256),(238+w-10,259+12*opened),3)
        # This is the same blue glass panel seen on the door in the wide shot.
        d.poly(c['window'],[(238+w*.17,274),(238+w*.83,276+9*opened),
                            (238+w*.83,341+9*opened),(238+w*.17,339)],c['ink'],2)
        d.circle(c['accent'],(238+w-14,400),5)


def person(d, st, x, ground, scale, role='hero', t=0, walk=0, phase=0,
           phone=0, reach=0, phone_visible=False, second=False):
    """An articulated character: legs, arms, head, hands and face have separate poses."""
    c=st.colors
    ishero=role=='hero'
    # Body rises and falls with the walk cycle; legs articulate independently.
    bounce=abs(math.sin(phase))*5*walk
    yy=ground-bounce*scale
    def p(v): return (x+v[0]*scale, yy+v[1]*scale)
    def line_limb(a,b,fill,thick): d.limb(c['ink'],fill,p(a),p(b),thick*scale)
    pants = mix(c['ink'],c['police_dark'],.30) if ishero else c['police_dark']
    sleeve = c['hero'] if ishero else c['police']
    dark = c['hero_dark'] if ishero else c['police_dark']
    skin = c['skin'] if not second else mix(c['skin'], c['wood'], .30)
    # Grounded contact shadow does not bounce with the actor.
    d.ellipse(mix(c['floor'],c['ink'],.27),(x-55*scale,ground-8*scale,110*scale,17*scale))
    if st.kind == 'paper':
        # An offset physical cutout shadow follows the articulated puppet.
        shade=mix(c['wall'],c['ink'],.35)
        d.ellipse(shade,(x-40*scale+8,yy-284*scale+10,85*scale,84*scale))
        d.poly(shade,[(x-43*scale+8,yy-205*scale+10),(x+43*scale+8,yy-205*scale+10),
                      (x+55*scale+8,yy-111*scale+10),(x-50*scale+8,yy-111*scale+10)])
    step=math.sin(phase)*27*walk
    lift1=max(0,math.sin(phase))*13*walk
    lift2=max(0,-math.sin(phase))*13*walk
    hips=[(-22,-120),(22,-120)]
    feet=[(-24-step,-16-lift1),(24+step,-16-lift2)]
    for i in (0,1):
        h=hips[i]; f=feet[i]
        knee=(lerp(h[0],f[0],.60),lerp(h[1],f[1],.52)-3*walk)
        fill=mix(pants,c['ink'],.12) if i==0 else pants
        line_limb(h,knee,fill,26)
        line_limb(knee,f,fill,24)
        footx, footy=p((f[0]+(5 if ishero else -5), f[1]+4))
        d.ellipse(c['ink'],(footx-22*scale,footy-6*scale,46*scale,21*scale))
        d.ellipse(c['white'] if ishero else mix(c['police_dark'],c['ink'],.2),(footx-18*scale,footy-1*scale,37*scale,10*scale))
    # Far arm: independently rigged at shoulder, elbow and wrist.
    lshoulder=(-34,-193)
    lelbow=(-52+step*.38,-153)
    lhand=(-48+step*.63,-123)
    if ishero:
        lelbow=point(lelbow,(-36,-146),reach)
        lhand=point(lhand,(65,-125),reach)
    else:
        lelbow=point(lelbow,(-62,-150),reach)
        lhand=point(lhand,(-86,-130),reach)
    line_limb(lshoulder,lelbow,sleeve,23)
    line_limb(lelbow,lhand,sleeve,21)
    d.circle(skin,p(lhand),11*scale,c['ink'],2.5*scale)
    # Neck, torso and clothing details.
    d.rect(skin,(*p((-17,-225)),34*scale,34*scale),8*scale,c['ink'],3*scale)
    torso=[(-36,-207),(-52,-197),(-50,-158),(-55,-121),(-43,-109),(43,-109),(54,-121),(50,-158),(52,-197),(35,-207)]
    d.poly(sleeve,[p(v) for v in torso],c['ink'],4*scale)
    d.poly(dark,[p(v) for v in [(-50,-157),(-55,-121),(-43,-109),(43,-109),(54,-121),(50,-147),(39,-137),(-38,-137)]])
    d.line(c['ink'],p((-43,-113)),p((43,-113)),3*scale)
    if st.kind == 'comic':
        for row in range(4):
            for col in range(5):
                d.circle(mix(sleeve,c['ink'],.37),p((-36+col*6+(row%2)*3,-175+row*6)),1.15*scale)
    elif st.kind == 'neon':
        d.line(c['blue'],p((-48,-184)),p((-49,-150)),2.5*scale)
        d.line(c['red'],p((48,-181)),p((49,-160)),2.5*scale)
    elif st.kind == 'paper':
        for px in range(-32,38,10):
            d.line(c['white'],p((px,-116)),p((px+4,-116)),1.6*scale)
    if ishero:
        # Hood opening, drawstrings, pocket and cloth shine.
        d.poly(mix(c['hero'],c['white'],.26),[p((-24,-204)),p((0,-178)),p((24,-204)),p((15,-214)),p((-15,-214))],c['ink'],3*scale)
        d.line(c['ink'],p((-10,-188)),p((-13,-156)),2.4*scale)
        d.line(c['ink'],p((10,-188)),p((13,-156)),2.4*scale)
        d.lines(mix(c['hero_dark'],c['ink'],.2),[p((-25,-136)),p((-18,-149)),p((18,-149)),p((25,-136))],2.5*scale)
        d.line(mix(c['hero'],c['white'],.38),p((-38,-184)),p((-40,-166)),2*scale)
    else:
        # Shirt collar, tie, shoulder tabs, shield and utility belt.
        d.poly(c['white'],[p((-20,-205)),p((0,-185)),p((20,-205)),p((10,-211)),p((-10,-211))],c['ink'],2.5*scale)
        d.poly(c['police_dark'],[p((-5,-197)),p((5,-197)),p((7,-168)),p((0,-161)),p((-7,-168))])
        d.rect(c['police_dark'],(*p((-48,-132)),96*scale,12*scale),2*scale,c['ink'],2*scale)
        d.rect(c['accent'],(*p((-8,-132)),16*scale,11*scale),1*scale,c['ink'],1*scale)
        star(d,*p((25,-180)),8*scale,c['accent'],c['ink'])
        d.line(c['accent'],p((-47,-197)),p((-26,-194)),3*scale)
        d.line(c['accent'],p((27,-194)),p((46,-197)),3*scale)
    # Ears/head. Head moves independently with a subtle expressive lean.
    nod=(math.sin(t*3.0)*1.2 if walk==0 else math.sin(phase)*2.5*walk)
    def hp(v): return p((v[0],v[1]+nod))
    d.ellipse(c['hair'],(*hp((-47,-286)),94*scale,84*scale),c['ink'],3*scale)
    d.circle(skin,hp((-40,-246)),12*scale,c['ink'],2.5*scale)
    d.circle(skin,hp((40,-246)),12*scale,c['ink'],2.5*scale)
    if st.kind == 'comic':
        d.poly(skin,[hp(v) for v in [(-38,-274),(-29,-283),(29,-283),(39,-273),(39,-242),
                                     (27,-215),(0,-204),(-27,-215),(-39,-242)]],c['ink'],3.5*scale)
        # Three hand-inked cheek hatches: a print-comic visual language.
        for i in range(3):
            d.line(mix(skin,c['ink'],.32),hp((-28+i*6,-235)),hp((-22+i*6,-230)),1.5*scale)
    else:
        d.ellipse(skin,(*hp((-39,-280)),78*scale,75*scale),c['ink'],3.5*scale)
    if st.kind == 'paper':
        d.ellipse(mix(skin,c['red'],.32),(*hp((-31,-237)),15*scale,7*scale))
        d.ellipse(mix(skin,c['red'],.32),(*hp((20,-237)),15*scale,7*scale))
    if ishero:
        # Distinctive dark curly hair remains the same in all five styles.
        for hx,hy,hr in [(-29,-277,14),(-16,-286,15),(1,-289,16),(18,-285,14),(31,-275,12),(-37,-264,10)]:
            d.circle(c['hair'],hp((hx,hy)),hr*scale,c['ink'],1.5*scale)
        d.line(mix(c['hair'],c['white'],.23),hp((-17,-289)),hp((-4,-294)),2.2*scale)
    else:
        # Blue peaked cap.
        d.poly(c['police_dark'],[hp((-43,-277)),hp((-36,-301)),hp((34,-301)),hp((42,-277))],c['ink'],3*scale)
        d.rect(c['police'],(*hp((-41,-282)),82*scale,13*scale),4*scale,c['ink'],2*scale)
        d.ellipse(c['police_dark'],(*hp((-45,-277)),92*scale,10*scale),c['ink'],2*scale)
        star(d,*hp((0,-293)),7*scale,c['accent'],c['ink'])
        if second:
            d.circle(c['hair'],hp((39,-266)),12*scale,c['ink'],2*scale)
    # Eyes, pupils and eyebrows are posed independently.
    look=5 if ishero else -5
    blink=(t%3.3 < .12) or (ishero and phone_visible and 1.75 < t < 1.87)
    for ex in (-16,14):
        if blink:
            d.line(c['ink'],hp((ex-7,-249)),hp((ex+7,-249)),3*scale)
        else:
            d.ellipse(c['white'],(*hp((ex-8,-257)),16*scale,16*scale),c['ink'],1.5*scale)
            d.circle(c['ink'],hp((ex+look,-249)),3.5*scale)
        brow_y=-266 - (3 if (ishero and (phone_visible or reach>.15)) else 0)
        d.line(c['ink'],hp((ex-8,brow_y+1)),hp((ex+7,brow_y-1)),2.5*scale)
    d.circle(mix(skin,c['wood'],.17),hp((3,-237)),4*scale)
    if ishero and (reach>.25 or (phone_visible and t>1.1 and math.sin(t*10)>0)):
        d.ellipse(c['ink'],(*hp((-5,-226)),14*scale,9*scale))
        d.ellipse(c['red'],(*hp((-1,-221)),7*scale,3*scale))
    elif not ishero:
        d.line(c['ink'],hp((-8,-225)),hp((10,-225)),2.4*scale)
    else:
        d.arc(c['ink'],(*hp((-10,-231)),23*scale,12*scale),3.3,5.95,2.4*scale)
    # On arrest, the far forearm comes around in front of the torso so both
    # articulated hands visibly meet the handcuffs (rather than floating).
    if ishero and reach>.01:
        line_limb(lelbow,lhand,sleeve,21)
        d.circle(skin,p(lhand),11*scale,c['ink'],2.5*scale)
    # Near arm and phone. Raising the phone is a continuous pose, not a frame swap.
    rshoulder=(36,-193)
    relbow=(53-step*.35,-154)
    rhand=(49-step*.55,-123)
    if ishero:
        relbow=point(relbow,(78,-184),phone)
        rhand=point(rhand,(45,-251),phone)
        relbow=point(relbow,(66,-143),reach)
        rhand=point(rhand,(84,-125),reach)
    else:
        relbow=point(relbow,(58,-157),reach)
        rhand=point(rhand,(43,-134),reach)
    line_limb(rshoulder,relbow,sleeve,23)
    line_limb(relbow,rhand,sleeve,21)
    d.circle(skin,p(rhand),11*scale,c['ink'],2.5*scale)
    if st.kind == 'paper':
        # Tiny rivets make the elbow and knee joints read like a paper puppet.
        for joint in (relbow,):
            d.circle(c['white'],p(joint),3.5*scale,c['wood'],1*scale)
    if ishero and phone_visible:
        xx,py=p((rhand[0]+1,rhand[1]-12))
        # The handset stays attached to the hand throughout the movement.
        d.rect(c['ink'],(xx-10*scale,py-18*scale,20*scale,34*scale),4*scale,c['white'],1.5*scale)
        d.rect(mix(c['blue'],c['white'],.37),(xx-7*scale,py-13*scale,14*scale,22*scale),1*scale)
        d.circle(c['white'],(xx,py+12*scale),1.5*scale)
        if t < 1.15:
            for i in range(2):
                rr=(21+i*10+3*math.sin(t*12))*scale
                d.arc(c['accent'],(xx-rr,py-rr,rr*2,rr*2),.45,1.35,3*scale)
                d.arc(c['accent'],(xx-rr,py-rr,rr*2,rr*2),1.8,2.7,3*scale)
    return {'left_hand':p(lhand), 'right_hand':p(rhand)}


def car(d,st,x,ground,s,t,rotation=0, flashing=True):
    c=st.colors
    def p(v): return (x+v[0]*s,ground+v[1]*s)
    def poly(fill,ps,outline=True,width=4): d.poly(fill,[p(v) for v in ps],c['ink'] if outline else None,width*s)
    def rect(fill,r,rad=0,outline=True,width=3): d.rect(fill,(*p((r[0],r[1])),r[2]*s,r[3]*s),rad*s,c['ink'] if outline else None,width*s)
    d.ellipse(mix(c['floor'],c['ink'],.35),(x+12*s,ground-5*s,400*s,24*s))
    # Window cabin, rounded fenders, door and bumper.
    poly(c['police_dark'],[(82,-87),(125,-145),(276,-145),(338,-88)])
    poly(c['window'],[(100,-92),(135,-133),(193,-133),(193,-92)])
    poly(mix(c['window'],c['white'],.18),[(203,-133),(269,-133),(317,-92),(203,-92)])
    d.line(c['white'],p((139,-127)),p((118,-102)),3*s)
    poly(c['white'],[(15,-85),(80,-99),(341,-99),(391,-78),(405,-51),(405,-27),(9,-27),(5,-51)])
    poly(c['blue'],[(13,-70),(403,-70),(405,-46),(9,-46)],False)
    d.line(c['ink'],p((197,-95)),p((197,-28)),3*s)
    d.line(c['ink'],p((326,-94)),p((333,-31)),3*s)
    d.line(c['ink'],p((211,-82)),p((229,-82)),4*s)
    d.line(c['ink'],p((343,-81)),p((359,-81)),4*s)
    # Emblem avoids relying on tiny printed text in the pixel version.
    d.circle(c['white'],p((261,-57)),24*s,c['ink'],2.5*s)
    star(d,*p((261,-57)),16*s,c['accent'],c['ink'])
    rect(c['accent'],(4,-70,19,17),3)
    rect(c['red'],(389,-69,14,16),2)
    rect(c['ink'],(0,-36,24,12),2,False)
    rect(c['ink'],(388,-36,23,12),2,False)
    # Wheels really rotate with car position.
    for wx in (95,328):
        center=p((wx,-27))
        d.circle(c['ink'],center,33*s)
        d.circle(mix(c['white'],c['ink'],.2),center,18*s,c['ink'],3*s)
        d.circle(c['ink'],center,5*s)
        for i in range(4):
            a=rotation+i*math.pi/2
            d.line(c['ink'],(center[0]+math.cos(a)*6*s,center[1]+math.sin(a)*6*s),
                   (center[0]+math.cos(a)*14*s,center[1]+math.sin(a)*14*s),2.5*s)
    # Alternating animated siren, including transparent beams/glow.
    rect(c['ink'],(192,-158,56,13),3,False)
    a=math.sin(t*math.pi*5) >= 0
    red=c['red'] if (a or not flashing) else mix(c['red'],c['ink'],.55)
    blue=c['blue'] if ((not a) or not flashing) else mix(c['blue'],c['ink'],.55)
    if flashing:
        glow(d,*p((204,-157)),52*s,c['red'],95 if a else 25)
        glow(d,*p((235,-157)),52*s,c['blue'],25 if a else 95)
    rect(red,(194,-171,24,13),4)
    rect(blue,(222,-171,24,13),4)
    if flashing:
        bright=c['red'] if a else c['blue']
        for i in range(3):
            an=-math.pi*.83+i*math.pi*.25
            u=p((220,-170))
            start=(u[0]+math.cos(an)*27*s,u[1]+math.sin(an)*27*s)
            end=(u[0]+math.cos(an)*43*s,u[1]+math.sin(an)*43*s)
            d.line(bright,start,end,4*s)


def call_card(d,st,t):
    c=st.colors
    pop=smooth(.12,.43,t)
    if pop<=0: return
    x=844+35*(1-pop); y=174+12*(1-pop)
    d.rect(mix(c['ink'],c['wall'],.24),(x+9,y+12,354,162),20)
    d.rect(c['white'],(x,y,354,162),20,c['ink'],4)
    d.circle(c['hero'],(x+51,y+80),32,c['ink'],3)
    # Universal handset shape, animated only during the ring.
    k=math.sin(t*14)*2 if t<1.2 else 0
    d.arc(c['white'],(x+34+k,y+57,34,44),3.55,5.9,8)
    if st.kind == 'pixel':
        d.text('ЗВОНОК',x+98,y+28,20,mix(c['ink'],c['white'],.38),FONT_SANS)
        d.text('ПОЛИЦИЯ',x+98,y+67,27,c['ink'],FONT_SANS)
        d.text('НА СВЯЗИ',x+98,y+111,20,mix(c['ink'],c['white'],.35),FONT_REG)
    else:
        d.text('ВХОДЯЩИЙ ЗВОНОК',x+98,y+39,17,mix(c['ink'],c['white'],.38),FONT_SANS)
        d.text('ПОЛИЦИЯ',x+98,y+68,34,c['ink'],FONT_SANS)
        d.text('на связи',x+99,y+112,20,mix(c['ink'],c['white'],.35),FONT_REG)
    if t<1.15:
        for i in range(3):
            theta=(t*4+i)*math.pi*2/3
            star(d,x+53+math.cos(theta)*48,y+80+math.sin(theta)*48,4,c['accent'],n=4)


def cuffs(d,st,hero_hands,local):
    if local<2.48: return
    c=st.colors
    # Hinged arcs close around both animated wrists, with a connecting chain.
    q=smooth(2.48,2.84,local)
    a,b=hero_hands['left_hand'],hero_hands['right_hand']
    r=11
    d.line(c['ink'],(a[0]+8,a[1]),(b[0]-8,b[1]),7)
    d.line(c['white'],(a[0]+8,a[1]-1),(b[0]-8,b[1]-1),3)
    for x,y in (a,b):
        d.circle(c['ink'],(x,y),r+2)
        d.circle(c['white'],(x,y),r)
        d.circle(c['ink'],(x,y),r-4)
        d.circle(c['skin'],(x,y),r-7)
        if q<1:
            d.line(c['white'],(x+r*.4,y-r*.65),(x+r*(.4+q),y-r*(1.35-q*.5)),4)
    if local<3.16:
        star(d,b[0]+21,b[1]-19,10,c['accent'],c['ink'],4)


def comics_accents(d,st,t,scene):
    if st.kind != 'comic': return
    c=st.colors
    if scene==0 and t<1.3:
        pop=smooth(0,.2,t)*(1-smooth(1.0,1.3,t))
        star(d,742,139,69*pop,c['accent'],c['ink'],n=12,inner=.70)
        if pop>.65: d.text('ДЗЫНЬ!',742,139,23,c['ink'],FONT_SERIF,'center')
    elif scene==1:
        for y in (320,352,384):
            d.line(c['ink'],(1100,y),(1200,y),3)
        if t>3.45:
            star(d,1022,341,65,c['red'],c['ink'],n=11,inner=.68)
            d.text('ВИУ!',1022,341,27,c['white'],FONT_SERIF,'center')
    elif scene==2 and 7.25<t<8.8:
        star(d,610,158,51,c['accent'],c['ink'],n=10,inner=.67)
        d.text('!?',610,158,35,c['ink'],FONT_SERIF,'center')
    # Comic ink frame, deliberately only a border, never a static panel.
    d.frame(c['white'],(14,14,W-28,H-28),4)
    d.frame(c['ink'],(20,20,W-40,H-40),6)


def overlay(d, st, index, t, scene):
    c=st.colors
    # Contrasting editorial label; the same story can be compared in every style.
    label_path=FONT_SERIF if st.kind=='comic' else (FONT_MONO if st.kind=='pixel' else FONT_SANS)
    fs=25 if st.kind!='pixel' else 23
    text_w=d.text_surface(st.title,fs,c['white'],label_path).get_width()/d.q
    bx,by=37,32
    bw=92+text_w+27
    d.rect(c['ink'],(bx+5,by+6,bw,49),11 if st.kind!='pixel' else 0)
    d.rect(c['white'],(bx,by,bw,49),11 if st.kind!='pixel' else 0,c['ink'],3)
    d.rect(c['red'] if st.kind=='comic' else c['hero_dark'],(bx+6,by+6,54,37),7 if st.kind!='pixel' else 0)
    d.text(f'{index:02}',bx+33,by+25,22,c['white'],FONT_MONO,'center')
    d.text(st.title,bx+72,by+25,fs,c['ink'],label_path,'midleft')
    # Animated progress line in the top right.
    d.rect(c['ink'],(1044,37,195,13),6)
    d.rect(c['accent'],(1047,40,189*clamp(t/DURATION),7),3)
    labels=['ВХОДЯЩИЙ ЗВОНОК: ПОЛИЦИЯ','ПОЛИЦИЯ ПРИЕЗЖАЕТ К ДОМУ','ГЕРОЯ ЗАДЕРЖИВАЮТ']
    caption=labels[scene]
    f=25 if st.kind!='pixel' else 23
    path=FONT_MONO if st.kind=='pixel' else FONT_SANS
    tw=d.text_surface(caption,f,c['white'],path).get_width()/d.q
    bw=tw+76
    d.rect(c['ink'],((W-bw)/2+4,657,bw,48),12 if st.kind!='pixel' else 0)
    d.rect(c['ink'],((W-bw)/2,653,bw,48),12 if st.kind!='pixel' else 0,c['white'],2)
    d.circle(c['accent'],((W-bw)/2+20,677),5)
    d.text(caption,W/2+4,677,f,c['white'],path,'center')


def neon_rain(d, st, t, scene):
    c=st.colors
    old_clip=d.s.get_clip()
    if scene==0:
        d.s.set_clip(pygame.Rect(*d.xy((100,150)),d.n(280),d.n(237)))
    for i in range(55):
        x=(i*157+37)%1280
        y=(i*91+t*(85+(i%4)*15))%570
        d.line(mix(c['blue'],c['sky'],.50),(x,y),(x-5,y+18),1.5)
    d.s.set_clip(old_clip)


def render_frame(st,index,t,cache,size):
    if t<3.0: scene=0
    elif t<5.7: scene=1
    else: scene=2
    surf=cache[scene].copy()
    d=Draw(surf,st)
    c=st.colors
    if st.kind == 'neon':
        neon_rain(d,st,t,scene)
    if scene==0:
        moving_clock(d,st,t)
        # Animated lift from waist to ear; the eye, mouth and fingers are separate.
        phone=smooth(.60,1.26,t)
        person(d,st,565,618,1.48,'hero',t=t,phone=phone,phone_visible=True)
        call_card(d,st,t)
    elif scene==1:
        local=t-3.0
        journey=smooth(.05,1.85,local)
        xpos=lerp(1410,750,journey)
        velocity=1-smooth(1.4,2.0,local)
        if velocity>.1:
            for i in range(3):
                yy=531+i*23
                d.line(mix(c['white'],c['sky'],.25),(xpos+422+i*10,yy),(xpos+500+i*20,yy),4)
        car(d,st,xpos,618,1.0,t,rotation=(1410-xpos)/32,flashing=True)
    else:
        local=t-5.7
        animated_door(d,st,local)
        # The car stays parked by the same house throughout the arrest.
        car(d,st,906,580,.90,t,rotation=0,flashing=True)
        hero_walk=1-smooth(.55,1.0,local)
        hx=lerp(350,486,smooth(.03,.95,local))
        officer_walk=1-smooth(1.48,1.9,local)
        ox=lerp(1128,720,smooth(.07,1.85,local))
        sx=lerp(1260,973,smooth(.12,2.0,local))
        reach=smooth(1.58,2.45,local)
        # The second officer remains behind; front officer and hero remain planted.
        person(d,st,sx,620,1.24,'police',t=t,walk=officer_walk,phase=local*11-.8,second=True)
        hands=person(d,st,hx,620,1.33,'hero',t=t,walk=hero_walk,phase=local*12,reach=reach)
        person(d,st,ox,620,1.33,'police',t=t,walk=officer_walk,phase=local*11,reach=reach)
        cuffs(d,st,hands,local)
    comics_accents(d,st,t,scene)
    overlay(d,st,index,t,scene)
    if st.kind=='paper':
        # Small independent stitching details reinforce the cut-paper aesthetic.
        for i in range(10):
            d.line(c['white'],(14+i*14,703),(20+i*14,703),2)
    return surf


def audio(st):
    """Original procedural score plus ring, engine, siren, footsteps and cuffs."""
    sr=44100
    n=sr*DURATION
    tt=np.arange(n,dtype=np.float64)/sr
    left=np.zeros(n,dtype=np.float64)
    right=np.zeros(n,dtype=np.float64)
    rng=np.random.default_rng(2026)
    def add(start, data, amp=1.0, pan=0.0):
        i=max(0,int(start*sr)); nn=min(len(data),n-i)
        if nn<=0: return
        left[i:i+nn]+=data[:nn]*amp*(1-pan*.32)
        right[i:i+nn]+=data[:nn]*amp*(1+pan*.32)
    scales={
        'sunny':[261.63,329.63,392.00,523.25,392,329.63,293.66,349.23],
        'comic':[220.00,261.63,293.66,329.63,349.23,329.63,261.63,246.94],
        'neon':[196,233.08,293.66,349.23,293.66,233.08,220,261.63],
        'paper':[261.63,329.63,392,440,392,349.23,329.63,293.66],
        'pixel':[261.63,329.63,392,523.25,493.88,392,329.63,293.66],
    }
    notes=scales[st.kind]
    beat=.30 if st.kind in ('sunny','pixel') else .34
    for k,start in enumerate(np.arange(0,DURATION,beat)):
        dur=.23 if st.kind!='paper' else .32
        t=np.arange(int(sr*dur))/sr
        f=notes[(k+(k//8)*2)%len(notes)]
        env=np.minimum(1,t/.012)*np.exp(-t*(12 if st.kind!='neon' else 7))
        if st.kind=='pixel':
            tone=(np.sign(np.sin(2*np.pi*f*t))*.60+np.sign(np.sin(2*np.pi*f*2*t))*.16)*env
        elif st.kind=='neon':
            tone=(np.sin(2*np.pi*f*t)+.28*np.sin(2*np.pi*(f*.5)*t)+.18*np.sin(2*np.pi*2*f*t))*env
        else:
            tone=(np.sin(2*np.pi*f*t)+.25*np.sin(2*np.pi*2.01*f*t)+.10*np.sin(2*np.pi*3.02*f*t))*env
        add(start,tone,.050,(-.35 if k%2 else .35))
    # A low pulsing accompaniment.
    for start in np.arange(0,DURATION,beat*2):
        t=np.arange(int(sr*.19))/sr
        env=np.exp(-t*22)
        kick=np.sin(2*np.pi*(75*t-90*t*t))*env
        add(start,kick,.075)
    # Phone: two soft electronic ring bursts while the handset is down.
    for start in (.10,.73):
        t=np.arange(int(sr*.32))/sr
        env=np.minimum(1,t/.02)*np.minimum(1,(.32-t)/.03)
        ring=(np.sin(2*np.pi*540*t)+np.sin(2*np.pi*660*t))*.5*env
        add(start,ring,.14,.30)
    # The approaching engine and recognisable two-tone siren.
    start=3.0; dur=3.25
    t=np.arange(int(sr*dur))/sr
    env=np.minimum(1,t/.30)*np.minimum(1,(dur-t)/.45)
    eng=(np.sin(2*np.pi*(68*t+12*t*t))+.28*rng.normal(0,1,len(t)))*env
    add(start,eng,.034,.20)
    f=620+210*np.sin(2*np.pi*1.35*t)
    phase=2*np.pi*np.cumsum(f)/sr
    siren=(np.sin(phase)+.20*np.sin(phase*2))*env
    add(start+.02,siren,.105,.22)
    # Footsteps when the door opens and the officers approach.
    for j,start in enumerate([5.83,6.08,6.34,6.56,6.78,7.0,7.23,7.43]):
        t=np.arange(int(sr*.10))/sr
        env=np.exp(-t*38)
        thud=(np.sin(2*np.pi*108*t)+.18*rng.normal(0,1,len(t)))*env
        add(start,thud,.10,(-.45 if j%2 else .45))
    # Two crisp metal clicks when the cuffs close.
    for start in (8.20,8.41):
        t=np.arange(int(sr*.13))/sr
        env=np.exp(-t*45)
        click=(np.sin(2*np.pi*2400*t)+.5*np.sin(2*np.pi*3310*t)+.3*rng.normal(0,1,len(t)))*env
        add(start,click,.10,-.1)
    # Smooth start/end and safe peak level.
    fade=np.minimum(1,tt/.05)*np.minimum(1,(DURATION-tt)/.08)
    arr=np.column_stack([left*fade,right*fade])
    peak=np.max(np.abs(arr))
    if peak>.85: arr*=.85/peak
    return (arr*32767).astype('<i2'),sr


def make_cache(st,size):
    return [interior(st,size),exterior(st,size,False),exterior(st,size,True)]


def encode(st,index,out,save_samples=False):
    size=(320,180) if st.kind=='pixel' else (W,H)
    cache=make_cache(st,size)
    samples=[0.4,1.5,3.55,4.9,6.3,7.4,8.6,9.8]
    if save_samples:
        dest=ROOT/'animation'/'previews'
        dest.mkdir(parents=True,exist_ok=True)
        for s in samples:
            im=render_frame(st,index,s,cache,size)
            if im.get_size()!=(W,H): im=pygame.transform.scale(im,(W,H))
            pygame.image.save(im,str(dest/f'{st.key}_{s:.2f}.png'))
        print(f'Sample frames: {st.key}',flush=True)
        return
    snd,sr=audio(st)
    with tempfile.TemporaryDirectory(prefix='nurmadog-') as tmp:
        wav=Path(tmp)/'sound.wav'
        with wave.open(str(wav),'wb') as f:
            f.setnchannels(2); f.setsampwidth(2); f.setframerate(sr); f.writeframes(snd.tobytes())
        cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-y',
             '-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
             '-i',str(wav),'-t',str(DURATION),'-c:v','libx264','-preset','veryfast','-crf','20',
             '-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(out)]
        print(f'Rendering {st.title} -> {out.name}',flush=True)
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for i in range(FPS*DURATION):
                surf=render_frame(st,index,i/FPS,cache,size)
                if size!=(W,H): surf=pygame.transform.scale(surf,(W,H))
                p.stdin.write(pygame.image.tobytes(surf,'RGB'))
                if i and i%100==0: print(f'  {i}/{FPS*DURATION}',flush=True)
        finally:
            p.stdin.close()
        if p.wait()!=0: raise RuntimeError(f'ffmpeg failed while encoding {out}')
        print(f'Done: {out.stat().st_size/1_000_000:.1f} MB',flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--style',choices=[s.key for s in STYLES],help='Render only one style')
    ap.add_argument('--samples',action='store_true',help='Write stills for internal animation QA, not final output')
    args=ap.parse_args()
    pygame.init()
    # convert() needs a display surface even when using SDL's dummy video driver.
    pygame.display.set_mode((1,1))
    OUTPUT.mkdir(parents=True,exist_ok=True)
    for i,st in enumerate(STYLES,1):
        if args.style and args.style!=st.key: continue
        encode(st,i,OUTPUT/st.filename,args.samples)
    pygame.quit()

if __name__=='__main__': main()
