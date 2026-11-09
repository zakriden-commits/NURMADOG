"""Cut the fighters out of the plain-white source images and give them soft alpha edges."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = {
    "khabib": "video/assets/khabib_src.png",
    "bsd": "video/assets/bsd_src.png",
}


def cutout(path, thresh=52, feather=2.2, grow=1):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    # mask: flood fill from the border to catch the connected white background only
    m = Image.new("L", (w, h), 0)
    px = im.load()
    mpx = m.load()
    # build a "whiteness" test image for floodfill (dark = background-like)
    white = Image.new("L", (w, h), 0)
    wp = white.load()
    arr = np.asarray(im).astype(np.int16)
    # distance from white
    dist = 255 - arr.min(axis=2)
    darr = Image.fromarray(dist.astype(np.uint8), "L")
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)]
    mask = darr.point(lambda v: 255 if v < thresh else 0)
    # flood fill background region starting from corners
    flood = mask.copy()
    for s in seeds:
        if flood.getpixel(s) == 255:
            ImageDraw.floodfill(flood, s, 128, thresh=8)
    bg = np.array(flood) == 128
    alpha = np.where(bg, 0, 255).astype(np.uint8)
    a = Image.fromarray(alpha, "L")
    # erode a hair to kill the white halo, then blur for soft edge
    for _ in range(grow):
        a = a.filter(ImageFilter.MinFilter(3))
    a = a.filter(ImageFilter.GaussianBlur(feather))
    a = a.point(lambda v: 0 if v < 24 else v)
    out = im.convert("RGBA")
    out.putalpha(a)
    bbox = out.getbbox()
    out = out.crop(bbox)
    return out


for name, p in SRC.items():
    c = cutout(p)
    c.save(f"video/assets/{name}_cut.png")
    print(name, c.size)
