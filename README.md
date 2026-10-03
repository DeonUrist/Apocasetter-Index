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

## Getting your mod listed

**[Open a "Submit a mod" issue](../../issues/new?template=submit-mod.yml)** and fill in the form. An automatic check comments within a
minute or two. When the maintainer has looked at the mod, the **approved** label lists it, and the issue closes itself.

Or open a pull request that adds `mods/<your GUID>.json` (format below). The same checks run on the pull request.

What your mod needs:

- a **public GitHub repository**;
- a **GitHub release** whose tag is the version (`v1.2.0` or `1.2.0`, compared as numbers);
- a **`.zip` attached to the release** containing your plugin DLL. Any of these layouts works:
  `YourMod.dll` · `YourMod/YourMod.dll` (+ your assets) · `BepInEx/plugins/YourMod/...`. A README at the zip root is ignored;
- the DLL must contain your plugin GUID (it does if it has `[BepInPlugin("your.guid", ...)]`).

After that you only publish releases as usual. The next hourly run picks them up and players are offered the update.

What approval means: the maintainer has looked at the mod and the repository. Later releases are not reviewed by hand, but every one
goes through the automatic checks (zip readable, no paths that escape the plugin folder, DLL with the same GUID) before players are
offered it.

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
    "dlls": ["Apocapatrol/Apocapatrol.dll"], "guidDll": "Apocapatrol/Apocapatrol.dll", "skip": []
  }
},
"error": null
```

`zip` is `null` when the release has no zip (players get a link to the release page instead). Apocasetter checks `sha256` after
downloading, extracts the files minus `stripPrefix` into `BepInEx\<extractTo>\`, skips the files in `skip`, and never deletes files the zip
doesn't contain. `latest` is `null` while a repository has no release.

## For the maintainer

- **List a submission:** add the `approved` label to the issue (only the repository owner's label counts).
- **Block a mod:** set `"blocked": true` and a `blockedReason` in its entry and push. It takes effect at the next index build.
- **Remove a mod:** delete its entry.
- **Run locally:** `python3 scripts/validate.py --online` and `python3 scripts/build_index.py` (Python 3, standard library only;
  set `GITHUB_TOKEN` to avoid the 60-requests-an-hour limit).
- GitHub pauses scheduled workflows in repositories with no activity for 60 days. The index commits keep it active while mods
  release; otherwise re-enable **Build index** under Actions.
