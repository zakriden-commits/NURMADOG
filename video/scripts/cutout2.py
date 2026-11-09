"""Cut the new photo assets out of their studio backdrops (white / grey gradient)."""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

SRC = {"benua": "/tmp/arena-coding-uploads/image-3.png",
       "khabib": "/tmp/arena-coding-uploads/image-4.png"}


def cutout(path, thresh=34, feather=1.4, erode=1):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w, _ = a.shape
    border = np.concatenate([a[0:6].reshape(-1, 3), a[-6:].reshape(-1, 3),
                             a[:, 0:6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    d = np.abs(a - bg).max(axis=2)

    bg_like = d < thresh
    lab, n = ndi.label(bg_like, structure=np.ones((3, 3)))
    # background = the components of bg_like that touch the frame border
    border_labels = set(lab[0, :]) | set(lab[-1, :]) | set(lab[:, 0]) | set(lab[:, -1])
    border_labels.discard(0)
    bg_mask = np.isin(lab, list(border_labels))

    fg = ~bg_mask
    # keep only the biggest foreground blob, then fill its holes
    flab, fn = ndi.label(fg, structure=np.ones((3, 3)))
    if fn:
        sizes = ndi.sum(fg, flab, range(1, fn + 1))
        keep = int(np.argmax(sizes)) + 1
        fg = ndi.binary_fill_holes(flab == keep)

    alpha = fg.astype(np.uint8) * 255
    al = Image.fromarray(alpha, "L")
    for _ in range(erode):
        al = al.filter(ImageFilter.MinFilter(3))
    al = al.filter(ImageFilter.GaussianBlur(feather))
    al = al.point(lambda v: 0 if v < 60 else int((v - 60) * 255 / 195))

    out = im.convert("RGBA")
    out.putalpha(al)
    bbox = out.getbbox()
    return out.crop(bbox), bg


for name, p in SRC.items():
    c, bg = cutout(p)
    c.save(f"video/assets/{name}_cut.png")
    print(name, "bg", bg.round(1), "->", c.size)
