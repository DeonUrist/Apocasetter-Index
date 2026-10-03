"""Turns a "Submit a mod" issue into an entry.

    submission.py check     run on opened/edited: checks the form and comments the result
    submission.py approve   run when the owner adds the 'approved' label: writes mods/<guid>.json
                            and rebuilds index.json (the workflow commits and pushes)
    submission.py close     comments that the mod is listed and closes the issue

The issue text is read from the event file, never pasted into a shell.
"""
import json
import os
import re
import sys

from index_lib import API, MODS_DIR, check_entry, http, online_check

MARK = "<!-- apocasetter-index-check -->"
LABELS = {
    "mod name": "name",
    "plugin guid": "guid",
    "github repository": "repo",
    "one-line summary": "summary",
    "author": "author",
    "tags": "tags",
    "requires": "requires",
    "works with": "optional",
    "plugin folder": "pluginFolder",
}


def event():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        return json.load(f)


def parse(body):
    fields, cur, buf = {}, None, []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.*?)\s*$", line)
        if m:
            if cur:
                fields[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1).strip().lower(), []
        else:
            buf.append(line)
    if cur:
        fields[cur] = "\n".join(buf).strip()
    entry = {}
    for label, key in LABELS.items():
        v = fields.get(label, "")
        if v in ("_No response_", "None"):
            v = ""
        if key in ("tags", "requires", "optional"):
            entry[key] = [x.strip() for x in re.split(r"[,\n]", v) if x.strip()]
        elif key == "pluginFolder":
            entry[key] = v or None
        elif key == "repo":
            v = re.sub(r"^https?://github\.com/", "", v.strip()).strip("/")
            entry[key] = re.sub(r"\.git$", "", v)
        else:
            entry[key] = v.strip()
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    entry["trust"] = "official" if entry.get("repo", "").split("/")[0].lower() == owner.lower() else "community"
    entry["blocked"] = False
    return entry


def comment(number, text, update_mark=False):
    repo = os.environ["GITHUB_REPOSITORY"]
    if update_mark:
        for c in http("%s/repos/%s/issues/%d/comments?per_page=100" % (API, repo, number)):
            if MARK in (c.get("body") or ""):
                http("%s/repos/%s/issues/comments/%d" % (API, repo, c["id"]), data={"body": text}, method="PATCH")
                return
    http("%s/repos/%s/issues/%d/comments" % (API, repo, number), data={"body": text}, method="POST")


def ensure_labels(number):
    """Creates the two labels the flow uses (first run only) and tags the issue as a submission."""
    repo = os.environ["GITHUB_REPOSITORY"]
    for name, color, desc in (("submission", "1D76DB", "A mod submitted through the form"),
                              ("approved", "0E8A16", "Maintainer: list the submitted mod")):
        try:
            http("%s/repos/%s/labels" % (API, repo), data={"name": name, "color": color, "description": desc}, method="POST")
        except Exception:
            pass  # already there
    try:
        http("%s/repos/%s/issues/%d/labels" % (API, repo, number), data={"labels": ["submission"]}, method="POST")
    except Exception as x:
        print("could not label the issue: %s" % x)


def run_checks(entry):
    path = os.path.join(MODS_DIR, (entry.get("guid") or "missing") + ".json")
    errs = check_entry(path, entry)
    warns, details = [], None
    if not errs:
        oe, ow, details = online_check(entry)
        errs += oe
        warns += ow
        if os.path.exists(path):
            warns.append("mods/%s.json already exists; approving replaces it" % entry["guid"])
    return path, errs, warns, details


def report(entry, errs, warns, details):
    lines = [MARK, "### Automatic check", ""]
    lines += ["- :x: " + e for e in errs] + ["- :warning: " + w for w in warns]
    if details and details.get("zip"):
        z = details["zip"]
        lines.append("- :white_check_mark: %s %s: %s contains `%s`" % (
            entry["repo"], details["release"].get("tag_name"), details["asset"]["name"], z["guidDll"]))
    if not errs:
        lines += ["", "Looks fine. The maintainer adds the **approved** label to list it."]
    else:
        lines += ["", "Edit the issue to fix these; the check runs again."]
    lines += ["", "<details><summary>Entry that would be written</summary>", "", "```json",
              json.dumps(entry, indent=2, ensure_ascii=False), "```", "</details>"]
    return "\n".join(lines)


def output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("%s=%s\n" % (key, value))


def main(mode):
    ev = event()
    issue = ev["issue"]
    entry = parse(issue.get("body"))
    if mode == "close":
        comment(issue["number"], "Listed as `mods/%s.json`. It shows up in Apocasetter's Mods window the next time "
                "players start the game. Thanks!" % entry["guid"])
        http("%s/repos/%s/issues/%d" % (API, os.environ["GITHUB_REPOSITORY"], issue["number"]),
             data={"state": "closed", "state_reason": "completed"}, method="PATCH")
        return 0
    if mode == "check":
        ensure_labels(issue["number"])
    path, errs, warns, details = run_checks(entry)
    comment(issue["number"], report(entry, errs, warns, details), update_mark=True)
    if mode == "check":
        return 0
    if errs:
        print("not approved: " + "; ".join(errs))
        return 1
    if details and details.get("zip") and not entry.get("pluginFolder"):
        entry["pluginFolder"] = details["zip"].get("topFolder")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(entry, f, indent=2, ensure_ascii=False)
        f.write("\n")
    output("guid", entry["guid"])
    print("wrote " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "check"))
