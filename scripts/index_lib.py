"""Shared helpers for the Apocasetter index: entry checks, GitHub calls, zip inspection.

Standard library only, so it runs the same on GitHub Actions and on a player's PC.
"""
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.request
import zipfile

API = "https://api.github.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODS_DIR = os.path.join(ROOT, "mods")
INDEX_PATH = os.path.join(ROOT, "index.json")

GUID_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,100}$")
REPO_RE = re.compile(r"^[A-Za-z0-9\-]{1,39}/[A-Za-z0-9._\-]{1,100}$")
FOLDER_RE = re.compile(r"^[A-Za-z0-9_.\- ]{1,64}$")
TRUST = ("official", "community")
MAX_ZIP = 200 * 1024 * 1024

# field -> (types, default)
FIELDS = {
    "guid": ((str,), None),
    "name": ((str,), None),
    "author": ((str,), None),
    "repo": ((str,), None),
    "summary": ((str,), None),
    "tags": ((list,), []),
    "requires": ((list,), []),
    "optional": ((list,), []),
    "pluginFolder": ((str, type(None)), None),
    "trust": ((str,), "community"),
    "blocked": ((bool,), False),
    "blockedReason": ((str,), ""),
    "deprecated": ((bool,), False),
    "deprecatedReason": ((str,), ""),
    "replacedBy": ((list,), []),
}
REQUIRED = ("guid", "name", "author", "repo", "summary")


def token():
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def http(url, raw=False, data=None, method=None, accept="application/vnd.github+json"):
    headers = {"User-Agent": "Apocasetter-Index", "Accept": accept}
    t = token()
    if t and url.startswith(API):
        headers["Authorization"] = "Bearer " + t
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=body, method=method)
    with urllib.request.urlopen(req, timeout=180) as r:
        payload = r.read()
    if raw:
        return payload
    return json.loads(payload.decode("utf-8")) if payload else None


def load_entries(directory=MODS_DIR):
    out = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        with open(path, encoding="utf-8") as f:
            out.append((path, json.load(f)))
    return out


def normalized(entry):
    """Entry with every known field present (defaults filled in)."""
    out = {}
    for k, (_, default) in FIELDS.items():
        v = entry.get(k, default)
        out[k] = list(v) if isinstance(v, list) else v
    return out


def check_entry(path, e):
    """Offline checks. Returns a list of problems (empty = fine)."""
    errs = []
    if not isinstance(e, dict):
        return ["the file must hold a JSON object"]
    for k in e:
        if k not in FIELDS:
            errs.append("unknown field '%s'" % k)
    for k in REQUIRED:
        v = e.get(k)
        if not isinstance(v, str) or not v.strip():
            errs.append("'%s' is required" % k)
    for k, (types, _) in FIELDS.items():
        if k in e and not isinstance(e[k], types):
            errs.append("'%s' has the wrong type" % k)
    if errs:
        return errs
    guid = e["guid"]
    if not GUID_RE.match(guid):
        errs.append("guid may only contain letters, digits, '.', '_' and '-' (3-100 characters)")
    if path and os.path.basename(path) != guid + ".json":
        errs.append("the file must be named mods/%s.json" % guid)
    if not REPO_RE.match(e["repo"]):
        errs.append("repo must look like owner/name")
    if len(e["name"]) > 60:
        errs.append("name is longer than 60 characters")
    if len(e["summary"]) > 200:
        errs.append("summary is longer than 200 characters")
    tags = e.get("tags", [])
    if len(tags) > 6 or any(not isinstance(t, str) or not t or len(t) > 24 for t in tags):
        errs.append("tags: at most 6, each a word of up to 24 characters")
    for k in ("requires", "optional"):
        for g in e.get(k, []):
            if not isinstance(g, str) or not GUID_RE.match(g):
                errs.append("%s: '%s' is not a plugin GUID" % (k, g))
    rb = e.get("replacedBy", [])
    if len(rb) > 4:
        errs.append("replacedBy: at most 4 mods")
    for g in rb:
        if not isinstance(g, str) or not GUID_RE.match(g):
            errs.append("replacedBy: '%s' is not a plugin GUID" % g)
        elif g == guid:
            errs.append("replacedBy can't list the mod itself")
    if rb and not e.get("deprecated", False):
        errs.append("replacedBy is only used together with \"deprecated\": true")
    if len(e.get("deprecatedReason", "")) > 300:
        errs.append("deprecatedReason is longer than 300 characters")
    pf = e.get("pluginFolder")
    if pf is not None and (not FOLDER_RE.match(pf) or pf.strip(".") == ""):
        errs.append("pluginFolder must be a plain folder name (no slashes)")
    if e.get("trust", "community") not in TRUST:
        errs.append("trust must be 'official' or 'community'")
    return errs


def latest_release(repo):
    try:
        return http("%s/repos/%s/releases/latest" % (API, repo))
    except urllib.error.HTTPError as x:
        if x.code == 404:
            return None
        raise


def pick_zip(release, repo=None):
    zips = [a for a in (release or {}).get("assets", []) if a.get("name", "").lower().endswith(".zip")]
    if not zips:
        return None
    if repo:
        short = repo.split("/")[1].lower()
        for a in zips:
            if a["name"].lower().startswith(short):
                return a
    return zips[0]


def analyze_zip(data, guid):
    """Where the zip's files go, which DLL carries the plugin GUID, and anything unsafe."""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = [n.replace("\\", "/") for n in z.namelist() if not n.endswith("/")]
    unsafe = [n for n in names if n.startswith("/") or re.match(r"^[A-Za-z]:", n) or ".." in n.split("/")]
    # readme/licence files at the zip root are not installed
    docs = [n for n in names if "/" not in n and n.lower().rsplit(".", 1)[-1] in ("md", "txt", "pdf", "url")]
    names = [n for n in names if n not in docs]
    extract_to, strip = "plugins", ""
    low = [n.lower() for n in names]
    if names and all(n.startswith("bepinex/plugins/") for n in low):
        strip = names[0][:len("BepInEx/plugins/")]
    elif names and all(n.startswith("plugins/") for n in low):
        strip = names[0][:len("plugins/")]
    elif names and all(n.startswith("bepinex/") for n in low):
        extract_to, strip = "BepInEx", names[0][:len("BepInEx/")]
    rel = [n[len(strip):] for n in names]
    dlls = [n for n in rel if n.lower().endswith(".dll")]
    tops = {d.split("/")[0] for d in dlls if "/" in d}
    loose = [d for d in dlls if "/" not in d]
    top = tops.pop() if (extract_to == "plugins" and len(tops) == 1 and not loose) else None
    guid_dll = None
    needle = guid.encode("utf-8")
    orig = {n.replace("\\", "/"): n for n in z.namelist()}
    for n in names:
        if n.lower().endswith(".dll") and n not in unsafe and needle in z.read(orig[n]):
            guid_dll = n[len(strip):]
            break
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "fileCount": len(names),
        "extractTo": extract_to,
        "stripPrefix": strip,
        "topFolder": top,
        "dlls": dlls,
        "guidDll": guid_dll,
        "skip": docs,
        "unsafe": unsafe,
    }


def online_check(e):
    """Checks against GitHub: repo, latest release, zip contents. -> (errors, warnings, details)."""
    errs, warns = [], []
    try:
        repo = http("%s/repos/%s" % (API, e["repo"]))
    except urllib.error.HTTPError as x:
        why = "not found" if x.code == 404 else "could not be read"
        return ["repository %s %s (HTTP %d)" % (e["repo"], why, x.code)], [], None
    if repo.get("private"):
        errs.append("repository is private")
    if repo.get("archived"):
        warns.append("repository is archived")
    rel = latest_release(e["repo"])
    if not rel:
        warns.append("no published release yet, so nothing can be offered for install")
        return errs, warns, None
    asset = pick_zip(rel, e["repo"])
    details = {"release": rel, "asset": asset, "zip": None}
    if not asset:
        warns.append("release %s has no .zip attached, so Apocasetter can only link to it" % rel.get("tag_name"))
        return errs, warns, details
    if asset.get("size", 0) > MAX_ZIP:
        errs.append("%s is larger than 200 MB" % asset["name"])
        return errs, warns, details
    try:
        data = http(asset["browser_download_url"], raw=True, accept="application/octet-stream")
        info = analyze_zip(data, e["guid"])
    except zipfile.BadZipFile:
        errs.append("%s is not a valid zip" % asset["name"])
        return errs, warns, details
    details["zip"] = info
    if info["unsafe"]:
        errs.append("zip contains unsafe paths: " + ", ".join(info["unsafe"][:5]))
    if not info["dlls"]:
        errs.append("zip contains no .dll")
    elif not info["guidDll"]:
        errs.append("no DLL in %s contains the plugin GUID %s" % (asset["name"], e["guid"]))
    pf = e.get("pluginFolder")
    if info["guidDll"] and info["extractTo"] == "plugins":
        if pf and info["topFolder"] and info["topFolder"] != pf:
            warns.append("zip puts the DLL in '%s\\', the entry says pluginFolder '%s'" % (info["topFolder"], pf))
    return errs, warns, details
