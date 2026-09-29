"""Import stubs so playback tests can load main.py without StreamController.

The plugin imports its host, evdev, loguru, and PIL at module level. Those
packages are not vendored here. This module installs stand-ins, then imports
the real plugin so tests exercise on_key_down and registration unchanged.
"""

import json
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocaleManager:
    def __init__(self, record=False):
        self.data = json.loads((ROOT / "locales" / "en_US.json").read_text())
        self.calls = []
        self.record = record

    def set_to_os_default(self):
        return None

    def get(self, key, default=None):
        if self.record:
            self.calls.append(key)
        if key in self.data:
            return self.data[key]
        return default


class ActionBase:
    def __init__(self, *args, **kwargs):
        self.action_id = kwargs.get("action_id")
        self.plugin_base = kwargs.get("plugin_base")
        self.labels = {}
        self.media = None

    def set_top_label(self, text):
        self.labels["top"] = text

    def set_center_label(self, text):
        self.labels["center"] = text

    def set_bottom_label(self, text):
        self.labels["bottom"] = text

    def set_media(self, media_path, size=None, valign=None):
        self.media = {"media_path": media_path, "size": size, "valign": valign}


class ActionHolder:
    def __init__(self, plugin_base=None, action_base=None, action_id=None, action_name=None):
        self.plugin_base = plugin_base
        self.action_base = action_base
        self.action_id = action_id
        self.action_name = action_name


class PluginBase:
    def __init__(self):
        self.PATH = str(ROOT)
        self.locale_manager = LocaleManager()
        self.holders = []
        self.registered = None

    def add_action_holder(self, holder):
        self.holders.append(holder)

    def register(self, **kwargs):
        self.registered = kwargs


class FakeUInput:
    def __init__(self, events=None, name=None):
        self.events = events
        self.name = name
        self.log = []
        self.fail_code = None
        self._failed = False

    def write(self, ev_type, code, value):
        if self.fail_code is not None and code == self.fail_code and not self._failed:
            self._failed = True
            raise RuntimeError("injected write failure")
        self.log.append(("write", ev_type, code, value))

    def syn(self):
        self.log.append(("syn",))


class Log:
    def __init__(self):
        self.debugs = []
        self.errors = []

    def debug(self, *args, **kwargs):
        self.debugs.append(args)

    def error(self, *args, **kwargs):
        self.errors.append(args)


def _package(name):
    module = types.ModuleType(name)
    module.__path__ = []
    module.__package__ = name
    sys.modules[name] = module
    return module


def _install_stubs():
    for name in ("src", "src.backend", "src.backend.DeckManagement", "src.backend.PageManagement", "src.backend.PluginManager"):
        _package(name)

    deck = types.ModuleType("src.backend.DeckManagement.DeckController")
    deck.DeckController = type("DeckController", (), {})
    sys.modules[deck.__name__] = deck

    page = types.ModuleType("src.backend.PageManagement.Page")
    page.Page = type("Page", (), {})
    sys.modules[page.__name__] = page

    action_base = types.ModuleType("src.backend.PluginManager.ActionBase")
    action_base.ActionBase = ActionBase
    sys.modules[action_base.__name__] = action_base

    action_holder = types.ModuleType("src.backend.PluginManager.ActionHolder")
    action_holder.ActionHolder = ActionHolder
    sys.modules[action_holder.__name__] = action_holder

    plugin_base = types.ModuleType("src.backend.PluginManager.PluginBase")
    plugin_base.PluginBase = PluginBase
    sys.modules[plugin_base.__name__] = plugin_base

    ecodes = types.SimpleNamespace(
        EV_KEY=1,
        EV_REL=2,
        REL_X=0,
        REL_Y=1,
        KEY_LEFTCTRL=29,
        KEY_UP=103,
        KEY_DOWN=108,
        KEY_LEFT=105,
        KEY_RIGHT=106,
    )
    ecodes.ecodes = {
        "KEY_UP": ecodes.KEY_UP,
        "KEY_DOWN": ecodes.KEY_DOWN,
        "KEY_LEFT": ecodes.KEY_LEFT,
        "KEY_RIGHT": ecodes.KEY_RIGHT,
    }
    evdev = types.ModuleType("evdev")
    evdev.ecodes = ecodes
    evdev.UInput = FakeUInput
    sys.modules["evdev"] = evdev

    loguru = types.ModuleType("loguru")
    loguru.logger = Log()
    sys.modules["loguru"] = loguru

    pil = types.ModuleType("PIL")
    pil.Image = type("Image", (), {})
    sys.modules["PIL"] = pil

    # gi.repository.Gtk imports successfully on this machine but warns unless a
    # version is required first. The plugin never uses Gtk, so a stand-in keeps
    # the test run quiet without touching main.py.
    gtk = types.ModuleType("gi.repository.Gtk")
    sys.modules["gi.repository.Gtk"] = gtk


def load_main():
    """Return the plugin module, importing it once with stubs installed."""
    if "main" in sys.modules and getattr(sys.modules["main"], "StratagemButton", None):
        return sys.modules["main"]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    _install_stubs()
    import main
    return main


def make_base(record_locale=False):
    """A plugin stand-in with the real stratagem list and a fake input device."""
    base = PluginBase()
    base.locale_manager = LocaleManager(record=record_locale)
    base.lm = base.locale_manager
    base.stratagems = json.loads((ROOT / "assets" / "data" / "stratagems.json").read_text())
    base.hero_mode = False
    base.executing = False
    base.ui = FakeUInput()
    return base
