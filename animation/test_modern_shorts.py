"""Checks for the portrait animation and its moving rigs."""
import io
import unittest

import numpy as np
import pygame
import modern_shorts as modern


class ModernShortChecks(unittest.TestCase):
    def test_shorts_delivery_format(self):
        self.assertEqual((modern.OUTPUT_W, modern.OUTPUT_H), (1080, 1920))
        self.assertEqual((modern.FPS, modern.DURATION), (30, 10))
        data = modern.frame_png(1.4, 270, 480)
        image = pygame.image.load(io.BytesIO(data), 'frame.png')
        self.assertEqual(image.get_size(), (270, 480))

    def test_keyframed_joints_and_expression(self):
        _, _, start_hand = modern.actor(0, 0, 1, phone=0, has_phone=True)
        _, _, raised_hand = modern.actor(0, 0, 1, phone=1, has_phone=True)
        self.assertGreater(abs(start_hand[1] - raised_hand[1]), 150)
        self.assertNotEqual(modern.head('hero', emotion=0), modern.head('hero', emotion=1))
        self.assertNotEqual(modern.head('hero', blink=0), modern.head('hero', blink=1))
        self.assertNotEqual(modern.porch_background(.1, 6), modern.porch_background(.8, 6))

    def test_motion_in_each_scene(self):
        def pixels(t):
            im = pygame.image.load(io.BytesIO(modern.frame_png(t, 270, 480)), 'frame.png')
            return pygame.surfarray.array3d(im).astype(np.int16)
        def delta(a, b, x1, y1, x2, y2):
            return float(np.mean(np.abs(a[x1:x2, y1:y2] - b[x1:x2, y1:y2])))
        phone_a, phone_b = pixels(.3), pixels(1.4)
        self.assertGreater(delta(phone_a, phone_b, 130, 130, 265, 410), 4)
        car_a, car_b = pixels(3.7), pixels(4.9)
        self.assertGreater(delta(car_a, car_b, 0, 300, 270, 410), 4)
        walk_a, walk_b = pixels(6.3), pixels(7.3)
        self.assertGreater(delta(walk_a, walk_b, 0, 120, 270, 390), 4)
        hand_a, hand_b = pixels(7.5), pixels(8.5)
        self.assertGreater(delta(hand_a, hand_b, 40, 190, 150, 300), 3)

    def test_audio_is_ten_seconds_and_normalized(self):
        samples, sr = modern.soundtrack()
        self.assertEqual(samples.shape, (sr * modern.DURATION, 2))
        peak = np.max(np.abs(samples.astype(np.int32)))
        self.assertGreater(peak, 20000)
        self.assertLessEqual(peak, 32767)


if __name__ == '__main__':
    unittest.main()
