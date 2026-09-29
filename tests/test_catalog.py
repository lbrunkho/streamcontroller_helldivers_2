"""Catalog contract for stratagem data, icons, locales, and the manifest.

A failure here means a stratagem key is missing its icon or locale entry, a
direction list is empty or illegal, two keys share a code, or manifest id /
version drifted from the plugin's stable identifiers.
"""

import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTIONS = {"UP", "DOWN", "LEFT", "RIGHT"}
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?$")


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stratagems = json.loads((ROOT / "assets" / "data" / "stratagems.json").read_text())
        cls.locale = json.loads((ROOT / "locales" / "en_US.json").read_text())
        cls.manifest = json.loads((ROOT / "manifest.json").read_text())
        cls.icons = ROOT / "assets" / "icons"

    def test_sequences_are_nonempty_directions(self):
        self.assertIsInstance(self.stratagems, dict)
        self.assertTrue(self.stratagems)
        for key, seq in self.stratagems.items():
            with self.subTest(key=key):
                self.assertIsInstance(seq, list)
                self.assertTrue(seq, "sequence is empty")
                self.assertTrue(all(step in DIRECTIONS for step in seq), seq)

    def test_sequences_are_unique(self):
        seen = {}
        for key, seq in self.stratagems.items():
            code = tuple(seq)
            with self.subTest(key=key):
                self.assertNotIn(code, seen, f"same code as {seen.get(code)}")
            seen[code] = key

    def test_each_key_has_a_parsable_svg(self):
        for key in self.stratagems:
            with self.subTest(key=key):
                path = self.icons / f"{key}.svg"
                self.assertTrue(path.is_file(), path)
                self.assertGreater(path.stat().st_size, 0)
                ET.parse(path)

    def test_every_svg_belongs_to_a_stratagem(self):
        orphans = sorted(
            path.stem for path in self.icons.glob("*.svg") if path.stem not in self.stratagems
        )
        self.assertEqual(orphans, [])

    def test_hero_icons_exist(self):
        for name in ("hero_on.png", "hero_off.png"):
            with self.subTest(name=name):
                path = self.icons / name
                self.assertTrue(path.is_file(), path)
                self.assertGreater(path.stat().st_size, 0)

    def test_locale_names_and_labels(self):
        for key in self.stratagems:
            with self.subTest(key=key):
                name = self.locale.get(f"actions.{key}.name")
                self.assertIsInstance(name, str)
                self.assertTrue(name.strip())
                for slot in ("top", "center", "bottom"):
                    label = self.locale.get(f"actions.{key}.labels.{slot}")
                    self.assertIsInstance(label, str)

    def test_plugin_and_hero_locale_entries(self):
        self.assertTrue(str(self.locale.get("plugin.name", "")).strip())
        self.assertTrue(str(self.locale.get("actions.StratagemHeroToggle.name", "")).strip())
        for slot in ("top", "center", "bottom"):
            label = self.locale.get(f"actions.StratagemHeroToggle.labels.{slot}")
            self.assertIsInstance(label, str)

    def test_manifest_identity_and_version(self):
        self.assertEqual(self.manifest["id"], "loganb_helldivers_2")
        self.assertRegex(self.manifest["version"], VERSION_RE)
        self.assertRegex(self.manifest["app-version"], VERSION_RE)


if __name__ == "__main__":
    unittest.main()
