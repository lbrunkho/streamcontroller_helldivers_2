# AGENTS.md

## Project overview

This is a **StreamController** plugin for **Helldivers 2** on Linux / Steam Deck. Each button fires a stratagem by injecting **Left Ctrl** (open menu) plus **arrow keys** (direction sequence) via `evdev` `UInput`.

- **Maintainer:** Logan Brunkhorst (this fork).
- **Upstream origin:** [jslay88/streamcontroller_helldivers_2](https://github.com/jslay88/streamcontroller_helldivers_2) (early history is GitHub PRs #1–#10).
- **Hosting:** Gitea — `https://gitea.minton.work/loganb/streamcontroller_helldivers_2.git` (not GitHub for day-to-day work).
- **Plugin id (manifest):** `loganb_helldivers_2`
- **Action id prefix (runtime):** `loganb_helldivers_2::…` (aligned with manifest id). Renaming this again breaks saved StreamController pages — leave it stable.

There is **no build system, package manager, linter, or test suite**. Maintenance is almost entirely **data updates** when Arrowhead ships warbonds / stratagems.

### Runtime assumptions (from README)

- Left Control opens the stratagem menu (hold/press).
- Stratagem directions are remapped to **arrow keys** (Up, Down, Left, Right).

### Runtime dependencies

Provided by the StreamController host environment (not vendored here):

- StreamController plugin APIs (`PluginBase`, `ActionBase`, `ActionHolder`, locale manager)
- `evdev`, `loguru`, `PIL`, GTK (`gi.repository`)

---

## Repository layout

```
streamcontroller_helldivers_2/
├── main.py                         # Plugin code (small; change rarely)
├── manifest.json                   # Store metadata; version source of truth
├── attribution.json                # jslay88 (GPL-3.0) + icon attribution
├── LICENSE                         # GPL-3.0
├── README.md                       # End-user notes (see Known debt)
├── AGENTS.md                       # This file — agent/maintainer conventions
├── locales/
│   └── en_US.json                  # Display names; on-button labels empty
├── assets/
│   ├── data/
│   │   └── stratagems.json         # key → [UP|DOWN|LEFT|RIGHT, ...]
│   └── icons/
│       ├── {StratagemKey}.svg      # One SVG per stratagem (filename = key)
│       ├── hero_on.png             # Stratagem Hero toggle only
│       └── hero_off.png
└── store/
    └── thumbnail.png
```

Icon SVGs are sourced from [nvigneux/Helldivers-2-Stratagems-icons-svg](https://github.com/nvigneux/Helldivers-2-Stratagems-icons-svg). A local clone may exist at `~/git/Helldivers-2-Stratagems-icons-svg`.

---

## How this repo is maintained

History shows a consistent pattern:

1. **Data first.** Most commits only touch `stratagems.json`, `assets/icons/*.svg`, `locales/en_US.json`, and `manifest.json`.
2. **Warbond-oriented commits.** Messages name the warbond and list new keys, e.g. `Add Siege Breakers warbond: BastionMKXVI, CQC20, EAT411, GL28`.
3. **Ship on `main`.** Direct commits; no PR workflow required on Gitea.
4. **Icons over text.** On-button labels were deliberately cleared; buttons are identified by SVG icons.
5. **Version every feature drop.** New stratagems bump the middle version component in `manifest.json`.

Prefer small, focused changes that match that style. Do not mass-reformat JSON, rename historical keys, or “clean up” unrelated files unless asked.

---

## Primary workflow: add a stratagem (or whole warbond)

For each new stratagem:

### 1. Choose a stable key

- PascalCase machine id matching existing style: `GuardDogRover`, `ExpendableNapalm`, `EAT411`, `GL-52De-Escalator`.
- Hyphens and alphanumerics appear in legacy keys; stay consistent with similar items.
- Put the **player-facing name** in the locale file, not necessarily in the key.

### 2. `assets/data/stratagems.json`

```json
"KeyName": ["DOWN", "UP", "LEFT", "RIGHT"]
```

- Only `UP`, `DOWN`, `LEFT`, `RIGHT` (uppercase). These map to `KEY_UP` etc. via evdev.
- Place near related stratagems when practical (same category / warbond cluster).
- Keep valid JSON (trailing commas will break load).

### 3. `assets/icons/KeyName.svg`

- Filename **must** equal the stratagem key + `.svg` (`main.py` loads `assets/icons/{key}.svg`).
- Prefer copying from the nvigneux icon repo (or the local clone).
- Recolor only when needed for game accuracy. Eagle/orbital accent red used historically: `#d46052`.
- Hero toggle remains PNG (`hero_on.png` / `hero_off.png`); do not convert those unless redesigning hero mode.

### 4. `locales/en_US.json`

Add all four keys. Leave label strings empty unless re-enabling on-button text on purpose:

```json
"actions.KeyName.name": "Player-Facing Name",
"actions.KeyName.labels.top": "",
"actions.KeyName.labels.center": "",
"actions.KeyName.labels.bottom": ""
```

- `name` is what appears in StreamController’s action picker.
- Quote style in display names often matches the game (`"Guard Dog" Rover`, etc.).

### 5. Bump `manifest.json` version

For new stratagems / features, increment the **middle** component:

```text
2.9.0  →  2.10.0
```

See [Versioning](#versioning).

### 6. Validate before finishing

Run from the repo root:

```bash
python3 - <<'PY'
import json, os
s = json.load(open("assets/data/stratagems.json"))
loc = json.load(open("locales/en_US.json"))
icons = set(os.listdir("assets/icons"))
dirs = {"UP", "DOWN", "LEFT", "RIGHT"}
missing_svg, missing_name, bad_seq = [], [], []
for k, seq in s.items():
    if f"{k}.svg" not in icons:
        missing_svg.append(k)
    if f"actions.{k}.name" not in loc:
        missing_name.append(k)
    if not all(x in dirs for x in seq):
        bad_seq.append((k, seq))
print("stratagems:", len(s))
print("missing .svg:", missing_svg or "ok")
print("missing locale name:", missing_name or "ok")
print("bad sequences:", bad_seq or "ok")
PY
```

### 7. Commit

- Message style: warbond or feature name + list of keys (informal is fine).
- Example: `Add Siege Breakers warbond: BastionMKXVI, CQC20, EAT411, GL28`
- Commit on `main` unless asked to use a branch.
- Do not force-push or rewrite history without explicit request.
- Do not push to the remote unless asked.

---

## Versioning

Convention (set at 2.0.0 and followed since):

```text
[major].[stratagem or feature].[minor or bugfix]
```

| Component | Bump when |
|-----------|-----------|
| **Major** | Substantial code / architecture change (e.g. full PNG→SVG migration was 2.0.0) |
| **Middle** | New stratagem(s) or user-facing feature |
| **Patch** | Bugfixes, typos, small cleanup |

- **Source of truth:** `manifest.json` → `"version"`.
- `main.py` loads `plugin_version` (and `app_version`) from `manifest.json` at register time — bump the manifest only.

---

## Code notes (`main.py`)

Change Python only when necessary. Most maintenance never needs it.

| Topic | Convention |
|-------|------------|
| Input delay | `SLEEP_DELAY = 0.04` — tuned by feel (too low → false inputs; too high → sluggish). Document why if you change it. |
| Stratagem icons | `{key}.svg` via `set_media(media_path=...)` |
| Hero toggle | PNG; toggles `plugin_base.hero_mode` |
| Hero mode behavior | When on, **skip** holding Left Ctrl (sequence only) |
| Concurrency | `plugin_base.executing` prevents overlapping sequences |
| Action construction | `ActionBase.__init__(self, *args, **kwargs)` |
| Registration | Action ids: `loganb_helldivers_2::{key}` and `…::StratagemHeroToggle` (see `action_id_prefix`) |
| Version / repo | Read from `manifest.json`; `github_repo` points at this Gitea fork |
| Logging | `loguru` as `log` |

### High-level flow

1. Load `stratagems.json` and register one `StratagemButton` action per key.
2. On key down: optionally hold Ctrl, then press/release each direction with `SLEEP_DELAY`, then release Ctrl.
3. Hero toggle flips `hero_mode` and refreshes its icon.

---

## Icon and attribution rules

- Prefer upstream SVG from nvigneux; keep visual consistency with existing icons in `assets/icons/`.
- Update `attribution.json` only if the icon source or license story changes.
- GPL-3.0 applies to the plugin (see `LICENSE` / `attribution.json` generic block).

---

## Agent behavior

- **Default task:** add or fix stratagem data, icons, locales, and version bumps.
- **Match existing style** over inventing new structure (key naming, empty labels, JSON layout).
- **Gitea remote** — do not assume GitHub CLI (`gh`) workflows for this repo.
- **No drive-by refactors** or mass renames.
- Ask before destructive git operations (force-push, hard reset, amending published commits).

---

## Breaking change note (2.9.1)

Action ids moved from `net_jslay_helldivers_2::*` to `loganb_helldivers_2::*`. Existing StreamController page bindings that still reference the old prefix need to be reassigned once after upgrading.

---

## Out of scope

- No required unit tests or CI.
- No packaging beyond the folder layout StreamController already loads.
- Do not add on-button text labels by default (icons-only is intentional).
- Do not rewrite icon set wholesale without a dedicated effort.
