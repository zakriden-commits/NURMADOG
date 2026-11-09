"""EDL for the v2 cut: no music (user adds their own), soft cinematic SFX only."""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(HERE, "audio", "timeline.json")))
TOTAL = TL["total"]
L = TL["lines"]
FPS = 30

SCENES = [
    ("hook", 0.00, 4.75),
    ("bsd", 4.75, 11.05),
    ("style", 11.05, 17.30),
    ("hate", 17.30, 22.45),
    ("vs", 22.45, 26.10),
    ("cta", 26.10, TOTAL),
]
CUTS = [s[1] for s in SCENES[1:]]
XFADE = 0.42          # smooth dissolve between scenes

# kind: air | impact | tick | swell | riser | shimmer | soft
BEATS = [
    (0.02, "air", 0.9),
    (0.30, "impact", 0.55),
    (0.62, "tick", 0.5),
    (1.00, "impact", 0.45),
    (2.30, "tick", 0.55),
    (2.62, "tick", 0.55),
    (3.05, "swell", 0.5),
    (4.60, "air", 0.9),
    (4.80, "impact", 0.5),
    (5.05, "tick", 0.45),
    (5.42, "tick", 0.5),
    (5.78, "tick", 0.5),
    (7.55, "impact", 0.45),
    (9.40, "tick", 0.4),
    (10.05, "tick", 0.4),
    (10.90, "air", 0.85),
    (11.09, "impact", 0.45),
    (11.35, "tick", 0.5),
    (12.50, "tick", 0.5),
    (13.70, "tick", 0.55),
    (15.45, "swell", 0.55),
    (17.15, "air", 0.85),
    (17.36, "impact", 0.5),
    (17.62, "tick", 0.45),
    (18.05, "impact", 0.4),
    (19.55, "impact", 0.5),
    (21.60, "tick", 0.4),
    (22.30, "riser", 0.55),
    (22.50, "impact", 0.7),
    (23.10, "tick", 0.45),
    (23.55, "tick", 0.45),
    (24.55, "impact", 0.5),
    (25.90, "air", 0.85),
    (26.16, "impact", 0.5),
    (26.95, "tick", 0.45),
    (27.55, "tick", 0.55),
    (28.20, "tick", 0.45),
    (29.30, "shimmer", 0.55),
    (30.20, "riser", 0.35),
]
