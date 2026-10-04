"""Builds index.json: every listed mod plus its latest GitHub release and a checked zip.

Apocasetter downloads only this one file, so players never hit GitHub's API limits.
Zips are downloaded once per release asset; later runs reuse the stored checksum.
index.json is only rewritten when something other than the timestamp changed.
"""
import datetime
import json
import sys
import urllib.error

from index_lib import (INDEX_PATH, analyze_zip, check_entry, http, latest_release,
                       load_entries, normalized, pick_zip, MAX_ZIP)


def previous():
    try:
        with open(INDEX_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {m["guid"]: m for m in data.get("mods", [])}
    except (OSError, ValueError):
        return {}


def zip_info(entry, asset, prev_latest):
    old = (prev_latest or {}).get("zip") or {}
    # "icon" missing = indexed before icons were read from zips: download once more
    if old.get("assetId") == asset["id"] and old.get("updated") == asset.get("updated_at") and old.get("sha256") and "icon" in old:
        return old, None
    if asset.get("size", 0) > MAX_ZIP:
        return None, "%s is larger than 200 MB" % asset["name"]
    data = http(asset["browser_download_url"], raw=True, accept="application/octet-stream")
    z = analyze_zip(data, entry["guid"])
    if z["unsafe"]:
        return None, "zip contains unsafe paths"
    return {
        "name": asset["name"],
        "url": asset["browser_download_url"],
        "size": asset.get("size"),
        "assetId": asset["id"],
        "updated": asset.get("updated_at"),
        "sha256": z["sha256"],
        "extractTo": z["extractTo"],
        "stripPrefix": z["stripPrefix"],
        "topFolder": z["topFolder"],
        "dlls": z["dlls"],
        "guidDll": z["guidDll"],
        "skip": z["skip"],
        "icon": z["icon"],
    }, (None if z["guidDll"] else "no DLL in the zip contains the plugin GUID")


def build():
    prev = previous()
    mods, problems = [], 0
    for path, raw in load_entries():
        errs = check_entry(path, raw)
        if errs:
            problems += 1
            print("SKIP %s: %s" % (path, "; ".join(errs)))
            continue
        e = normalized(raw)
        item = dict(e)
        item["latest"], item["error"] = None, None
        try:
            rel = latest_release(e["repo"])
            if rel:
                asset = pick_zip(rel, e["repo"])
                zinfo, zerr = (zip_info(e, asset, prev.get(e["guid"], {}).get("latest")) if asset else (None, None))
                item["latest"] = {
                    "version": (rel.get("tag_name") or "").lstrip("vV"),
                    "tag": rel.get("tag_name"),
                    "title": rel.get("name") or rel.get("tag_name"),
                    "published": rel.get("published_at"),
                    "page": rel.get("html_url"),
                    "notes": (rel.get("body") or "")[:4000],
                    "zip": zinfo if not zerr else None,
                }
                item["error"] = zerr
            else:
                item["error"] = "no release"
        except urllib.error.URLError as x:
            # keep what we knew last time rather than dropping the mod
            old = prev.get(e["guid"])
            print("WARN %s: GitHub request failed (%s), keeping the last known release" % (e["guid"], x))
            item["latest"] = old.get("latest") if old else None
            item["error"] = old.get("error") if old else "not checked yet"
        status = item["latest"]["version"] if item["latest"] else "-"
        print("%-40s %-10s %s" % (e["guid"], status, item["error"] or "ok"))
        mods.append(item)
    mods.sort(key=lambda m: m["name"].lower())

    old_mods = [prev[g] for g in sorted(prev)] if prev else None
    new_sorted = sorted(mods, key=lambda m: m["guid"])
    if old_mods is not None and json.dumps(old_mods, sort_keys=True) == json.dumps(new_sorted, sort_keys=True):
        print("index.json unchanged")
        return problems
    out = {
        "schemaVersion": 1,
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "https://github.com/DeonUrist/Apocasetter-Index",
        "mods": mods,
    }
    with open(INDEX_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("index.json written: %d mods" % len(mods))
    return problems


if __name__ == "__main__":
    sys.exit(1 if build() else 0)
