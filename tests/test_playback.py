"""Key-injection behavior for StratagemButton and plugin registration.

These tests stub StreamController and evdev, then call the real on_key_down
path. A failure means Ctrl or arrow events are missing, out of order, or still
emitted when another stratagem is already playing.
"""

import json
import os
import unittest

import plugin_loader


main = plugin_loader.load_main()
ROOT = plugin_loader.ROOT
REINFORCE = ["UP", "DOWN", "RIGHT", "LEFT", "UP"]


def _writes(ui):
    return [(event[2], event[3]) for event in ui.log if event[0] == "write"]


def _direction_pairs(sequence):
    pairs = []
    for step in sequence:
        code = main.ecodes.ecodes[f"KEY_{step}"]
        pairs.append((code, 1))
        pairs.append((code, 0))
    return pairs


class PlaybackTest(unittest.TestCase):
    def setUp(self):
        self.sleeps = []
        self._sleep = main.sleep
        main.sleep = self.sleeps.append

    def tearDown(self):
        main.sleep = self._sleep

    def _button(self, hero_mode=False, executing=False):
        base = plugin_loader.make_base()
        base.hero_mode = hero_mode
        base.executing = executing
        button = main.StratagemButton(
            action_id="loganb_helldivers_2::Reinforce",
            plugin_base=base,
        )
        return button, base

    def test_sleep_delay_is_the_tuned_value(self):
        self.assertEqual(main.SLEEP_DELAY, 0.04)

    def test_normal_mode_holds_ctrl_around_the_sequence(self):
        button, base = self._button()
        button.on_key_down()

        ctrl = main.ecodes.KEY_LEFTCTRL
        expected = [(ctrl, 1), *_direction_pairs(REINFORCE), (ctrl, 0)]
        self.assertEqual(_writes(base.ui), expected)
        self.assertEqual(button.stratagem, REINFORCE)
        self.assertFalse(base.executing)
        self.assertEqual(self.sleeps, [0.04] * len(expected))
        for index, event in enumerate(base.ui.log):
            if event[0] == "write":
                self.assertEqual(base.ui.log[index + 1][0], "syn")

    def test_hero_mode_skips_ctrl_down_and_still_releases_ctrl(self):
        button, base = self._button(hero_mode=True)
        button.on_key_down()

        ctrl = main.ecodes.KEY_LEFTCTRL
        writes = _writes(base.ui)
        self.assertNotIn((ctrl, 1), writes)
        self.assertEqual(writes, [*_direction_pairs(REINFORCE), (ctrl, 0)])
        self.assertEqual(self.sleeps, [0.04] * len(writes))
        self.assertFalse(base.executing)

    def test_overlapping_execution_writes_nothing(self):
        button, base = self._button(executing=True)
        button.on_key_down()
        self.assertEqual(base.ui.log, [])
        self.assertEqual(self.sleeps, [])
        self.assertTrue(base.executing)

    def test_direction_write_failure_still_releases_ctrl(self):
        button, base = self._button()
        base.ui.fail_code = main.ecodes.KEY_UP
        with self.assertRaises(RuntimeError):
            button.on_key_down()
        writes = _writes(base.ui)
        self.assertEqual(writes[0], (main.ecodes.KEY_LEFTCTRL, 1))
        self.assertEqual(writes[-1], (main.ecodes.KEY_LEFTCTRL, 0))
        self.assertFalse(base.executing)

    def test_hero_toggle_flips_mode_and_icon(self):
        base = plugin_loader.make_base(record_locale=True)
        button = main.StratagemHeroButton(plugin_base=base)

        button.on_key_down()
        self.assertTrue(base.hero_mode)
        self.assertTrue(button.media["media_path"].endswith(os.path.join("assets", "icons", "hero_on.png")))

        button.on_key_down()
        self.assertFalse(base.hero_mode)
        self.assertTrue(button.media["media_path"].endswith(os.path.join("assets", "icons", "hero_off.png")))

        for slot in ("top", "center", "bottom"):
            key = f"actions.StratagemHeroToggle.labels.{slot}"
            self.assertIn(key, base.lm.calls)
            self.assertEqual(button.labels[slot], base.lm.data[key])

    def test_stratagem_show_uses_key_svg(self):
        button, base = self._button()
        button.show()
        self.assertEqual(
            button.media["media_path"],
            os.path.join(base.PATH, "assets", "icons", "Reinforce.svg"),
        )

    def test_plugin_registers_every_stratagem_and_the_hero_toggle(self):
        plugin = main.HellDiversPlugin()
        locale = json.loads((ROOT / "locales" / "en_US.json").read_text())
        manifest = json.loads((ROOT / "manifest.json").read_text())

        ids = [holder.action_id for holder in plugin.holders]
        self.assertEqual(len(ids), len(plugin.stratagems) + 1)
        self.assertEqual(len(ids), len(set(ids)))
        for key in plugin.stratagems:
            self.assertIn(f"loganb_helldivers_2::{key}", ids)
        self.assertIn("loganb_helldivers_2::StratagemHeroToggle", ids)
        self.assertEqual(plugin.action_id_prefix, "loganb_helldivers_2")

        for holder in plugin.holders:
            key = holder.action_id.split("::", 1)[1]
            self.assertEqual(holder.action_name, locale[f"actions.{key}.name"])
            expected_action = main.StratagemHeroButton if key == "StratagemHeroToggle" else main.StratagemButton
            self.assertIs(holder.action_base, expected_action)

        self.assertEqual(plugin.registered["plugin_name"], locale["plugin.name"])
        self.assertEqual(plugin.registered["plugin_version"], manifest["version"])
        self.assertEqual(plugin.registered["app_version"], manifest["app-version"])
        self.assertEqual(
            plugin.registered["github_repo"],
            "https://github.com/lbrunkho/streamcontroller_helldivers_2",
        )

    def test_uinput_failure_is_logged_and_leaves_ui_none(self):
        class Boom:
            def __init__(self, *args, **kwargs):
                raise OSError("no permission")

        original = main.UInput
        main.UInput = Boom
        main.log.errors.clear()
        try:
            plugin = main.HellDiversPlugin.__new__(main.HellDiversPlugin)
            plugin.init_input()
        finally:
            main.UInput = original

        self.assertIsNone(plugin.ui)
        self.assertTrue(any(isinstance(args[0], OSError) for args in main.log.errors))


if __name__ == "__main__":
    unittest.main()
