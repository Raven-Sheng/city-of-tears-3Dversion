import json
import builtins
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "render"))

from stage06_pipeline import (  # noqa: E402
    bind_identity,
    build_compose_map,
    expected_take_frames,
    light_regions_for_take,
    validate_sequence,
)


class Stage06PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "config" / "shots_v010.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)

    def test_take_plan_covers_4398_handled_frames_and_4272_owned_frames(self):
        plan = expected_take_frames(self.config)
        self.assertEqual(sum(len(frames) for frames in plan.values()), 4398)
        self.assertEqual(plan["S01"][0], 1)
        self.assertEqual(plan["S01"][-1], 753)
        self.assertEqual(plan["S07"][0], 3448)
        self.assertEqual(plan["S07"][-1], 4272)

        compose = build_compose_map(self.config)
        self.assertEqual(len(compose), 4272)
        self.assertEqual([compose[f]["owner"] for f in range(1, 4273)].count("S01"), 744)
        self.assertEqual([compose[f]["owner"] for f in range(1, 4273)].count("S07"), 816)

    def test_planning_module_imports_when_blender_python_has_no_pillow(self):
        module_path = ROOT / "scripts" / "render" / "stage06_pipeline.py"
        spec = importlib.util.spec_from_file_location("stage06_pipeline_without_pillow", module_path)
        module = importlib.util.module_from_spec(spec)
        real_import = builtins.__import__

        def deny_pillow(name, *args, **kwargs):
            if name == "PIL" or name.startswith("PIL."):
                raise ModuleNotFoundError("Blender Python has no PIL")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=deny_pillow):
            spec.loader.exec_module(module)
        self.assertEqual(module.expected_take_frames(self.config)["S01"][0], 1)

    def test_compose_map_uses_declared_dissolve_sources_at_boundaries(self):
        compose = build_compose_map(self.config)
        self.assertEqual(compose[735], {"owner": "S01"})
        self.assertEqual(compose[736]["mix"], ["S01", "S02"])
        self.assertAlmostEqual(compose[736]["weight"], 0.002272, places=6)
        self.assertEqual(compose[753]["mix"], ["S01", "S02"])
        self.assertAlmostEqual(compose[753]["weight"], 0.997728, places=6)
        self.assertEqual(compose[754], {"owner": "S02"})

    def test_identity_rejects_changed_scene_config_renderer_or_settings(self):
        identity = {
            "scene_sha256": "scene-v1",
            "config_sha256": "config-v1",
            "renderer_sha256": "renderer-v1",
            "settings_sha256": "settings-v1",
        }
        bind_identity(self.folder, identity, resume=False)
        (self.folder / "f0001.png").write_bytes(b"kept")
        bind_identity(self.folder, identity, resume=True)
        self.assertEqual((self.folder / "f0001.png").read_bytes(), b"kept")

        for key in identity:
            changed = dict(identity)
            changed[key] = "changed"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "identity changed"):
                bind_identity(self.folder, changed, resume=True)

    def test_sequence_validation_reports_missing_extra_corrupt_and_wrong_size(self):
        Image.new("RGB", (4, 3), "black").save(self.folder / "f0001.png")
        Image.new("RGB", (5, 3), "black").save(self.folder / "f0002.png")
        (self.folder / "f0003.png").write_bytes(b"not a png")
        Image.new("RGB", (4, 3), "black").save(self.folder / "f0005.png")

        report = validate_sequence(self.folder, range(1, 5), (4, 3))
        self.assertEqual(report["missing"], [4])
        self.assertEqual(report["extra"], [5])
        self.assertEqual(report["corrupt"], [3])
        self.assertEqual(report["wrong_size"], [{"frame": 2, "actual": [5, 3]}])
        self.assertFalse(report["pass"])

    def test_take_light_regions_are_derived_from_beats_with_explicit_always_on_regions(self):
        self.assertEqual(
            light_regions_for_take(self.config, "S05", ["<none>", "_World"]),
            [
                "<none>",
                "EastWell",
                "GroundCorridorEast",
                "HouseOfPleasure",
                "LowerBridge",
                "PlazaEastHouse",
                "TowerBlock",
                "_World",
            ],
        )
        self.assertEqual(
            light_regions_for_take(self.config, "S06", ["<none>", "_World"]),
            ["<none>", "HouseOfPleasure", "_World"],
        )

    def test_sequence_validation_rejects_number_aliases_and_unrecognized_frame_names(self):
        for name in ['f0001.png', 'f1.png', 'f_bad.png']:
            Image.new('RGB', (4, 3), 'blue').save(self.folder / name)
        report = validate_sequence(self.folder, [1], (4, 3))
        self.assertFalse(report['pass'])
        self.assertEqual(report['duplicates'], [{'frame': 1, 'files': ['f0001.png', 'f1.png']}])
        self.assertEqual(report['unexpected_names'], ['f_bad.png'])


if __name__ == "__main__":
    unittest.main()
