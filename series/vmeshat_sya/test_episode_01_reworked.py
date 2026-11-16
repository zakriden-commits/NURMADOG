"""Regression checks for the re-edited episode (not a substitute for visual QA)."""
import math
import random
import struct
import unittest
import xml.etree.ElementTree as ET

import numpy as np

import episode_01_reworked as episode
import rig_v2 as rig


class RigChecks(unittest.TestCase):
    def test_ik_keeps_unprojected_bones_attached_and_clamps_reach(self):
        random.seed(7)
        for side in (-1,1):
            for _ in range(100):
                shoulder=(random.uniform(-10,10),random.uniform(-10,10))
                target=(random.uniform(-350,350),random.uniform(-350,350))
                elbow,wrist=rig.bone(shoulder,target,107,104,side)
                self.assertAlmostEqual(math.dist(shoulder,elbow),107,places=6)
                self.assertAlmostEqual(math.dist(elbow,wrist),104,places=6)
                self.assertLess(math.dist(shoulder,wrist),211)

    def test_profile_and_poses_are_distinct_drawings_not_stills(self):
        front=rig.person(260,820,.8,view=0,t=1)
        side=rig.person(260,820,.8,view=1,t=1)
        question=rig.person(260,820,.8,view=1,t=1,pose='question',gesture=1)
        self.assertNotEqual(front,side)
        self.assertNotEqual(side,question)
        for value in (front,side,question):
            self.assertNotIn('<image',value.lower())
            self.assertNotIn('nan',value.lower())
            self.assertIn('url(#v2hair)',value)
            self.assertIn('url(#v2pants)',value)
            self.assertIn('url(#v2shoe)',value)

    def test_tread_function_matches_stair_geometry(self):
        self.assertEqual(episode.stair_floor(-15),920)
        self.assertEqual(episode.stair_floor(55),885)
        self.assertEqual(episode.stair_floor(125),850)
        self.assertEqual(episode.stair_floor(195),815)
        self.assertEqual(episode.stair_floor(405),710)


class EpisodeChecks(unittest.TestCase):
    def test_vertical_delivery_and_real_native_render_size(self):
        self.assertEqual((episode.RENDER_W,episode.RENDER_H),(1080,1920))
        self.assertEqual((episode.OUTPUT_W,episode.OUTPUT_H),(1080,1920))
        self.assertEqual((episode.FPS,episode.DURATION),(24,60))
        png=episode.frame_png(42,270,480)
        self.assertEqual(png[:8],b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II',png[16:24]),(270,480))

    def test_every_voice_cue_exists_and_does_not_cover_next_speaker(self):
        previous_end=0
        for path,start,role in episode.VOICES:
            samples,sr=episode.voice(path)
            self.assertEqual(sr,44100)
            self.assertTrue(path.is_file())
            self.assertGreater(len(samples),0)
            self.assertGreaterEqual(start+.02,previous_end)
            previous_end=start+len(samples)/sr
            self.assertLess(previous_end,episode.DURATION)
        self.assertEqual(episode.VOICES[3][0].name,'hero_02_witness.wav')
        self.assertEqual(episode.VOICES[3][0].parent,episode.V1)

    def test_svg_is_valid_and_animates_within_each_scene(self):
        for t in (1,6.8,10.5,12.2,17,23,26.5,32,41.8,53.6,57):
            svg=episode.frame_svg(t)
            ET.fromstring(svg)
            self.assertNotIn('<image',svg.lower())
            self.assertNotIn('nan',svg.lower())
        for before,after in ((1,1.4),(5.8,6.2),(10,10.4),(16,16.5),
                             (23,23.4),(31.5,32),(41.4,42),(53.3,53.7)):
            self.assertNotEqual(episode.frame_png(before,135,240),episode.frame_png(after,135,240))

    def test_story_beats_and_unoccluded_warning_hand(self):
        self.assertIn('ВОСПОМИНАНИЕ',episode.frame_svg(24))
        self.assertIn('Чё надо?',episode.frame_svg(39.4))
        self.assertIn('Что за крики?',episode.frame_svg(41.8))
        self.assertIn('Могу ли я вмешаться?',episode.frame_svg(43))
        self.assertNotIn('clip-path="url(#v2doorclip)"',episode.hallway_scene(45.6))
        self.assertNotIn('M24 389 l20',episode.hallway_scene(53.4))
        self.assertIn('M24 389 l20',episode.hallway_scene(53.8))
        impact=episode.confrontation_scene(12.2)
        self.assertTrue(impact.startswith('<rect width="540" height="960" fill="url(#v2warm)"'))
        self.assertLess(impact.index('fill="url(#v2wom)"'),impact.index('fill="url(#v2shirt)"'))
        self.assertIn('ПРОДОЛЖЕНИЕ СЕРИАЛА',episode.frame_svg(57))
        self.assertTrue(all(a[1]<=b[0] for a,b in zip(episode.CAPTIONS,episode.CAPTIONS[1:])))
        self.assertIn('fill="#efd1ad"',episode.frame_svg(20.65))

    def test_mix_has_headroom_and_key_sounds(self):
        samples,sr=episode.audio_mix()
        self.assertEqual(samples.shape,(episode.DURATION*sr,2))
        pcm=samples.astype(np.float32)/32768
        self.assertGreater(float(np.max(np.abs(pcm))),.4)
        self.assertLess(float(np.max(np.abs(pcm))),.99)
        def rms(a,b):
            v=pcm[int(a*sr):int(b*sr)]
            return float(np.sqrt(np.mean(v*v)))
        self.assertGreater(rms(10.9,13.2),.02)
        self.assertGreater(rms(39,40),.04)
        self.assertGreater(rms(40.4,43.8),.04)
        self.assertGreater(rms(47.7,48.1),.02)
        self.assertGreater(rms(53.52,54.1),.02)
        self.assertGreater(rms(40.4,43.8),rms(57,59)*10)

if __name__=='__main__':
    unittest.main()
