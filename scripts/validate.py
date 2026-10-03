"""Checks the entries in mods/.

    python3 scripts/validate.py                 offline checks of every entry
    python3 scripts/validate.py --online        + GitHub checks (repo, release, zip, GUID) of every entry
    python3 scripts/validate.py --online --changed changed.txt
                                                + GitHub checks of the files listed in changed.txt only
Writes a Markdown report to $GITHUB_STEP_SUMMARY when it runs on Actions. Exit code 1 = errors.
"""
import argparse
import os
import sys

from index_lib import check_entry, load_entries, online_check


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--changed")
    a = ap.parse_args()

    entries = load_entries()
    only = None
    if a.changed and os.path.exists(a.changed):
        with open(a.changed, encoding="utf-8") as f:
            only = {os.path.basename(l.strip()) for l in f if l.strip()}

    lines, failed = ["| Entry | Result |", "|---|---|"], False
    seen = {}
    for path, e in entries:
        name = os.path.basename(path)
        errs = check_entry(path, e)
        warns = []
        g = e.get("guid") if isinstance(e, dict) else None
        if g in seen:
            errs.append("same guid as %s" % seen[g])
        seen[g] = name
        if not errs and a.online and (only is None or name in only):
            oe, ow, _ = online_check(e)
            errs += oe
            warns += ow
        failed = failed or bool(errs)
        result = "; ".join(["**error:** " + x for x in errs] + ["warning: " + x for x in warns]) or "ok"
        lines.append("| %s | %s |" % (name, result))
        print("%s: %s" % (name, result.replace("**", "")))

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## Apocasetter index entries\n\n" + "\n".join(lines) + "\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
