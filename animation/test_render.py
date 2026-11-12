"""Basic checks for the generated animation, motion and sound."""
import os
import unittest

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import numpy as np
import pygame
import render


class AnimationChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_five_unique_named_styles(self):
        self.assertEqual(len(render.STYLES), 5)
        self.assertEqual(len({s.title for s in render.STYLES}), 5)
        self.assertEqual(len({s.filename for s in render.STYLES}), 5)

    def test_articulated_motion_at_each_story_beat(self):
        style = render.STYLES[0]
        size = (render.W, render.H)
        cache = render.make_cache(style, size)
        def crop(t, x1, y1, x2, y2):
            frame = render.render_frame(style, 1, t, cache, size)
            return pygame.surfarray.array3d(frame)[x1:x2, y1:y2].astype(np.int16)
        def difference(a, b):
            return np.mean(np.abs(a-b))
        # Phone/arm are keyframed from waist to ear, not just a title changing.
        self.assertGreater(difference(crop(.4,430,150,720,610),
                                      crop(1.5,430,150,720,610)), 2)
        # The police car drives into frame.
        self.assertGreater(difference(crop(3.55,740,390,1250,640),
                                      crop(4.90,740,390,1250,640)), 3)
        # Officers and hero move across the porch.
        self.assertGreater(difference(crop(6.3,350,200,1180,630),
                                      crop(7.4,350,200,1180,630)), 3)
        # Arms and handcuffs visibly change in the arrest shot.
        self.assertGreater(difference(crop(7.4,520,390,680,485),
                                      crop(8.6,520,390,680,485)), 2)

    def test_every_style_has_audible_bounded_ten_second_stereo_audio(self):
        for style in render.STYLES:
            with self.subTest(style=style.key):
                samples, sr = render.audio(style)
                self.assertEqual(samples.shape, (sr * 10, 2))
                self.assertGreater(np.max(np.abs(samples.astype(np.int32))), 1000)
                self.assertLessEqual(np.max(np.abs(samples.astype(np.int32))), 32767)

    def test_all_pixel_captions_have_bitmap_glyphs(self):
        text = 'ПИКСЕЛЬНОЕ ПРИКЛЮЧЕНИЕ ВХОДЯЩИЙ ЗВОНОК: ПОЛИЦИЯ ПРИЕЗЖАЕТ К ДОМУ ГЕРОЯ ЗАДЕРЖИВАЮТ НА СВЯЗИ 05'
        self.assertFalse(set(text) - set(render.PIXEL_GLYPHS))

if __name__ == '__main__':
    unittest.main()
