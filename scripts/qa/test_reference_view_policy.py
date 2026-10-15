import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'render'))
from reference_view_policy import section_rain_depth


class SectionRainDepthTests(unittest.TestCase):
    def test_front_cut_suppresses_rain_between_camera_and_removed_wall(self):
        self.assertAlmostEqual(section_rain_depth(-10, 1, [10, 11], ['FRONT']), 21.3)
        self.assertAlmostEqual(section_rain_depth(-10, .5, [11], ['FRONT']), 42.6)

    def test_unsectioned_or_nonforward_views_do_not_change_rain(self):
        self.assertEqual(section_rain_depth(-10, 1, [11], []), 0)
        self.assertEqual(section_rain_depth(-10, .2, [11], ['FRONT']), 0)
        self.assertEqual(section_rain_depth(-10, 1, [], ['FRONT']), 0)

    def test_section_behind_camera_never_produces_negative_clip_depth(self):
        self.assertEqual(section_rain_depth(20, 1, [11], ['FRONT']), 0)


if __name__ == '__main__':
    unittest.main()
