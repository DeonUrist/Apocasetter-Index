# Apocasetter Index

The list of Apocalypter mods that [Apocasetter](https://github.com/DeonUrist/Apocasetter) shows in its in-game **Mods** window,
with the latest release of each. Players see when a mod they have is out of date, and can install, update or remove listed mods
without leaving the game.

Apocasetter downloads a single file:

```
https://raw.githubusercontent.com/DeonUrist/Apocasetter-Index/main/index.json
```

so players never run into GitHub's API limits. A GitHub Action rebuilds `index.json` every hour from the listed repositories' releases.

## Listed mods

| Mod | What it does |
|---|---|
| [ApocaHUD43](https://github.com/DeonUrist/ApocaHUD43) | Keeps the HUD on the screen edges at any aspect ratio |
| [ApocaLanguage](https://github.com/DeonUrist/ApocaLanguage) | Translates every text the game shows |
| [Apocapatrol](https://github.com/DeonUrist/Apocapatrol) | Raider gangs in cars, trucks and bikes roam the wasteland |
| [Apocapocket](https://github.com/DeonUrist/Apocapocket) | Item slots: weapon slots hold items, backpacks add slots 4-6 |
| [Apocaraider](https://github.com/DeonUrist/Apocaraider) | Real gunfights, smarter raiders, female raiders |
| [Apocasaver](https://github.com/DeonUrist/Apocasaver) | Autosave and named saves |
| [Apocasetter](https://github.com/DeonUrist/Apocasetter) | The in-game Mods menu itself |
| [Apocaspawner](https://github.com/DeonUrist/Apocaspawner) | Item, vehicle and trailer spawner |
| [Apocatremors](https://github.com/DeonUrist/Apocatremors) | Desert ambushes while you drive |
| [Apocaunloader](https://github.com/DeonUrist/Apocaunloader) | Hold R to unload your gun |

## For mod makers: getting your mod listed

1. **Public GitHub repository** for your mod.
2. **Every release**: tag = version (`v1.2.0`), the same version in your `[BepInPlugin]`, and a **`.zip` attached** that unpacks into
   `BepInEx\plugins` (`YourMod.dll`, or a `YourMod\` folder with the DLL and its files; a README at the zip root is ignored).
3. **Icon** (optional, recommended): a square PNG, 64×64, light lines on a transparent background. Ship it in the zip as
   `YourMod\icon.png` (mod in its own folder) or `YourMod.png` next to a single `YourMod.dll`. Without one, players see your initials.
   The index copies it out of the zip (PNG, up to 256×256 and 48 KB), so players see it in the list before they install the mod.
4. **Settings in the Mods window** (optional): bind `Config.Bind("General", "Apocasetter", true, "Show this mod in the Apocasetter Mods menu");`
   and give every config entry a clear description.
5. **Submit once**: **[open a "Submit a mod" issue](../../issues/new?template=submit-mod.yml)** and fill in the form, or open a pull request
   that adds `mods/<your GUID>.json` (format below). An automatic check comments within a minute or two; the maintainer lists the mod by
   adding the **approved** label.

After that you only publish releases as usual: the hourly index build picks them up, and players get an update badge and a one-click
install in the Mods window.

What approval means: the maintainer has looked at the mod and the repository. Later releases are not reviewed by hand, but every one
goes through the automatic checks (zip readable, no paths outside the plugin folder, a DLL with the same GUID) before players are offered it.

## Entry format (`mods/<guid>.json`)

```json
{
  "guid": "com.denis.apocalypter.apocapatrol",
  "name": "Apocapatrol",
  "author": "DeonUrist",
  "repo": "DeonUrist/Apocapatrol",
  "summary": "Raider gangs in scrap-built cars, trucks and bikes roam the wasteland ...",
  "tags": ["raiders", "vehicles", "combat"],
  "requires": [],
  "optional": ["com.denis.apocalypter.apocatremors"],
  "pluginFolder": "Apocapatrol",
  "trust": "official",
  "blocked": false
}
```

| Field | Meaning |
|---|---|
| `guid` | BepInEx plugin GUID. The file name must be `<guid>.json`. |
| `name`, `author`, `summary` | Shown in the Mods window. Summary up to 200 characters. |
| `repo` | `owner/name` on GitHub. Releases are read from here. |
| `tags` | Up to 6 short words. |
| `requires` | GUIDs the mod can't run without. Apocasetter offers to install them too. |
| `optional` | GUIDs the mod has extra features for. |
| `pluginFolder` | Folder under `BepInEx\plugins\` the mod lives in; `null` for a single DLL directly in `plugins`. |
| `trust` | `official` (the maintainer's own mods) or `community`. |
| `blocked`, `blockedReason` | Set by the maintainer. A blocked mod is never offered for install or update, and players who have it get a warning with the reason. |
| `replaces` | GUIDs of mods this one takes over (features that must not run twice). Installing it from the Mods window also disables those mods, and a player who has both gets a warning with a DISABLE button. |
| `deprecated`, `deprecatedReason`, `replacedBy` | Set by the maintainer. A deprecated mod is no longer offered for install; players who have it see a DEPRECATED badge and the reason, plus buttons for up to 4 mods in `replacedBy` (GUIDs) that take over. Updates are still offered. |

## index.json

Built by `scripts/build_index.py`; don't edit it by hand. Each entry is the entry above plus:

```json
"latest": {
  "version": "1.20.3", "tag": "v1.20.3", "title": "...", "published": "2026-10-02T20:04:08Z",
  "page": "https://github.com/DeonUrist/Apocapatrol/releases/tag/v1.20.3",
  "notes": "release text, first 4000 characters",
  "zip": {
    "name": "Apocapatrol-1.20.3.zip", "url": "...", "size": 26629152, "sha256": "...",
    "extractTo": "plugins", "stripPrefix": "", "topFolder": "Apocapatrol",
    "dlls": ["Apocapatrol/Apocapatrol.dll"], "guidDll": "Apocapatrol/Apocapatrol.dll", "skip": [],
    "icon": { "path": "Apocapatrol/icon.png", "size": [64, 64], "sha256": "...", "png": "<base64>" }
  }
},
"error": null
```

`zip` is `null` when the release has no zip (players get a link to the release page instead). Apocasetter checks `sha256` after
downloading, extracts the files minus `stripPrefix` into `BepInEx\<extractTo>\`, skips the files in `skip`, and never deletes files the zip
doesn't contain. `latest` is `null` while a repository has no release. `icon` is `null` when the zip has no icon.png (Apocasetter 2.0.8+
shows it for mods that aren't installed yet).

## For the maintainer

- **List a submission:** add the `approved` label to the issue (only the repository owner's label counts).
- **Block a mod:** set `"blocked": true` and a `blockedReason` in its entry and push. It takes effect at the next index build.
- **Deprecate a mod** (it still works, but you no longer develop it): add to its entry
  `"deprecated": true, "deprecatedReason": "One or two sentences for players.", "replacedBy": ["guid.one", "guid.two"]` (up to 4 GUIDs) and push.
  It disappears from the mods players can install; players who have it see the reason and buttons that open the replacements' pages.
  Needs Apocasetter 2.0.7 or newer; older versions ignore these fields.
- **Remove a mod:** delete `mods/<guid>.json` and push; the next index build drops it. Players who have it keep it, but it shows
  "no update source" and is no longer offered for install. Prefer deprecating: removing gives players no explanation.
- **Run locally:** `python3 scripts/validate.py --online` and `python3 scripts/build_index.py` (Python 3, standard library only;
  set `GITHUB_TOKEN` to avoid the 60-requests-an-hour limit).
- GitHub pauses scheduled workflows in repositories with no activity for 60 days. The index commits keep it active while mods
  release; otherwise re-enable **Build index** under Actions.
