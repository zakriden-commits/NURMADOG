"""Shared edit decision list: timings, scenes, beats. Used by both the renderer and the sound design."""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(HERE, "audio", "timeline.json")))
TOTAL = TL["total"]
L = TL["lines"]
FPS = 30

# ------------------------------------------------------------------ scene list
SCENES = [
    ("hook", 0.00, 4.95),
    ("bsd", 4.95, 10.76),
    ("style", 10.76, 16.55),
    ("hate", 16.55, 21.55),
    ("vs", 21.55, 26.02),
    ("cta", 26.02, TOTAL),
]

CUTS = [s[1] for s in SCENES[1:]]

# ------------------------------------------------------------------ beats
# kind: punch | bass | whoosh | riser | glitch | blip | stamp | strobe
BEATS = [
    (0.05, "riser", 1.0),
    (0.50, "punch", 0.7),
    (0.50, "bass", 1.0),
    (0.86, "punch", 1.0),
    (1.50, "stamp", 0.9),
    (4.95, "whoosh", 1.0),
    (4.98, "punch", 0.8),
    (5.35, "blip", 0.5),
    (5.78, "blip", 0.6),
    (6.62, "punch", 0.45),
    (8.02, "stamp", 1.0),
    (8.04, "punch", 0.9),
    (9.32, "blip", 0.45),
    (9.95, "blip", 0.45),
    (10.76, "whoosh", 1.0),
    (11.00, "punch", 0.8),
    (12.10, "punch", 0.75),
    (13.40, "punch", 0.9),
    (14.62, "bass", 0.9),
    (14.62, "glitch", 0.7),
    (16.55, "whoosh", 1.0),
    (16.80, "punch", 0.7),
    (17.50, "glitch", 1.0),
    (17.52, "punch", 0.85),
    (19.02, "stamp", 1.0),
    (19.04, "glitch", 0.8),
    (20.40, "blip", 0.4),
    (21.55, "riser", 0.7),
    (21.62, "bass", 1.0),
    (21.62, "punch", 1.0),
    (22.40, "blip", 0.5),
    (22.90, "punch", 0.6),
    (23.30, "punch", 0.7),
    (23.72, "punch", 0.9),
    (24.62, "stamp", 1.0),
    (26.02, "whoosh", 1.0),
    (26.20, "punch", 0.7),
    (26.72, "punch", 0.85),
    (27.40, "blip", 0.6),
    (27.46, "blip", 0.7),
    (28.60, "blip", 0.6),
    (29.90, "riser", 0.5),
]
