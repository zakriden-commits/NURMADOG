"""Regression checks for the episode's story, articulated movement and mix."""
import json
import struct
import unittest

import numpy as np

import episode_01 as episode


class EpisodeChecks(unittest.TestCase):
    def test_vertical_delivery_format(self):
        self.assertEqual((episode.OUTPUT_W, episode.OUTPUT_H), (1080, 1920))
        self.assertEqual((episode.FPS, episode.DURATION), (24, 60))
        image = episode.frame_png(7.0, 270, 480)
        self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II', image[16:24]), (270, 480))

    def test_selected_voices_and_cue_order(self):
        choices = json.loads((episode.HERE / 'voices.json').read_text())['voices']
        self.assertEqual(len({v['voice_id'] for v in choices.values()}), 3)
        for choice in choices.values():
            self.assertTrue((episode.HERE / choice['example']).is_file())
        previous_end = 0
        for name, start, role, _ in episode.VOICES:
            data, sr = episode.voice_data(name)
            self.assertIn(role, ('hero', 'man', 'woman'))
            self.assertEqual(sr, 44100)
            self.assertGreater(len(data), 0)
            self.assertGreaterEqual(start + .01, previous_end)
            previous_end = start + len(data) / sr
            self.assertLess(previous_end, episode.DURATION)

    def test_animation_is_vector_and_changes_in_every_scene(self):
        for t in (1, 7, 9.4, 17, 24.5, 31, 42, 53.8):
            svg = episode.frame_svg(t)
            self.assertNotIn('<image', svg.lower())
            self.assertIn('url(#goldHair)', svg)
        # Pairs within the same scene show changes to joints, facial expressions
        # or the action, not merely a cut to another background.
        for before, after in ((1, 2), (7, 7.5), (9.2, 9.4), (16, 17),
                              (24.2, 25), (30, 31), (41.4, 42), (53.6, 54)):
            self.assertNotEqual(episode.frame_png(before, 135, 240),
                                episode.frame_png(after, 135, 240))

    def test_key_story_beats_and_subtitles(self):
        self.assertNotIn('M439 274 l4 9', episode.frame_svg(9.1))
        self.assertIn('M439 274 l4 9', episode.frame_svg(9.4))  # blow and recoil
        self.assertIn('ВОСПОМИНАНИЕ', episode.frame_svg(24))
        self.assertIn('ЧТО ЗА КРИКИ?', episode.frame_svg(42))
        self.assertNotIn('M36 235 l14', episode.frame_svg(53.6))
        self.assertIn('M36 235 l14', episode.frame_svg(53.9))  # broken door
        self.assertIn('ПРОДОЛЖЕНИЕ СЕРИАЛА', episode.frame_svg(57))
        self.assertIn('«ВМЕШАТЬСЯ»', episode.frame_svg(57))
        self.assertIn('СЛЕДУЕТ', episode.frame_svg(57))
        # Dialogue subtitles occupy the top of the image, not the hero's shoes.
        self.assertIn('y="96"', episode.captions(42))
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(episode.CAPTIONS, episode.CAPTIONS[1:])))

    def test_audio_duration_headroom_and_distinct_cues(self):
        samples, sr = episode.audio_mix()
        self.assertEqual(samples.shape, (episode.DURATION * sr, 2))
        pcm = samples.astype(np.float32) / 32768
        self.assertGreater(np.max(np.abs(pcm)), .4)
        self.assertLess(np.max(np.abs(pcm)), .99)
        def rms(start, end):
            clip = pcm[int(start * sr):int(end * sr)]
            return float(np.sqrt(np.mean(clip * clip)))
        self.assertGreater(rms(9.7, 12.5), .03)  # woman
        self.assertGreater(rms(39.5, 40.5), .05)  # neighbor
        self.assertGreater(rms(41.15, 43.7), .05)  # hero
        self.assertGreater(rms(47.8, 48.2), .02)  # slammed door
        self.assertGreater(rms(53.65, 54.1), .02)  # smashed door
        self.assertGreater(rms(41.15, 43.7), rms(57, 59) * 10)


if __name__ == '__main__':
    unittest.main()
