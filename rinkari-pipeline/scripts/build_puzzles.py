#!/usr/bin/env python3
"""Validate all puzzles and publish them as per-day JSON files (plus a
lightweight manifest) that the site fetches at runtime.

Usage:
  python3 scripts/build_puzzles.py --out ../rinkari/puzzles [--dry-run]

Reads every puzzles/*.json, runs the linter, checks numbering/date
continuity, then writes into --out:
  <date>.json    - one file per puzzle (full clue data)
  manifest.json  - [{number, date}, ...] for every puzzle, sorted by date.
                   Deliberately excludes link/clues/answers so a future
                   (unreleased) puzzle isn't spoiled by the manifest fetch —
                   only number+date, which the site needs to work out what
                   "today" is and what's queued next.

index.html is never touched by this script. Publish a new day by dropping
its puzzles/YYYY-MM-DD.json into this pipeline, rerunning this script, and
uploading whatever changed under --out (the new date's file + the refreshed
manifest.json).
"""
import argparse, glob, json, os, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
PUZZLE_DIR = os.path.join(HERE, "..", "puzzles")
sys.path.insert(0, HERE)
import lint_clues as L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="directory to publish per-day JSON + manifest.json into (e.g. ../rinkari/puzzles)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(PUZZLE_DIR, "*.json")))
    if not paths:
        print("No puzzle files found in puzzles/"); sys.exit(1)

    # 1. Lint everything first. Call the linter as a library rather than a
    # subprocess — at hundreds of puzzle files, passing every path as a
    # command-line argument can exceed Windows' command-line length limit.
    problems = []
    for path in paths:
        L.lint_puzzle(path, problems)
    errs = [m for lvl, m in problems if lvl == "ERROR"]
    warns = [m for lvl, m in problems if lvl == "WARN"]
    for m in errs:
        print("ERROR:", m)
    for m in warns:
        print("WARN: ", m)
    print(f"\n{len(paths)} file(s): {len(errs)} error(s), {len(warns)} warning(s)")
    if errs:
        print("\nBuild aborted: fix lint errors first."); sys.exit(1)

    puzzles = [json.load(open(p, encoding="utf-8")) for p in paths]
    puzzles.sort(key=lambda p: p["date"])

    # 2. Continuity checks
    nums = [p["number"] for p in puzzles]
    if len(set(nums)) != len(nums):
        print("ERROR: duplicate puzzle numbers"); sys.exit(1)
    if nums != sorted(nums):
        print("ERROR: puzzle numbers not increasing with dates"); sys.exit(1)
    dates = [p["date"] for p in puzzles]
    if len(set(dates)) != len(dates):
        print("ERROR: duplicate dates"); sys.exit(1)
    gaps = []
    for a, b in zip(puzzles, puzzles[1:]):
        d1 = date.fromisoformat(a["date"]); d2 = date.fromisoformat(b["date"])
        if (d2 - d1).days != 1:
            gaps.append(f"  gap: {a['date']} -> {b['date']}")
    if gaps:
        print("WARN: non-consecutive dates (site will hold the latest puzzle over gaps):")
        print("\n".join(gaps))

    manifest = [{"number": p["number"], "date": p["date"]} for p in puzzles]

    today = date.today().isoformat()
    live = [p for p in puzzles if p["date"] <= today]
    queued = [p for p in puzzles if p["date"] > today]
    print(f"\n{len(puzzles)} puzzles validated. Live/past: {len(live)}, queued: {len(queued)}")
    if queued:
        print(f"Queue runs until {queued[-1]['date']} (No. {queued[-1]['number']})")

    if args.dry_run:
        print("(dry run - nothing written)")
        return

    os.makedirs(args.out, exist_ok=True)
    for p in puzzles:
        published = dict(p)
        published["linkType"] = published.pop("link_type", "compound")
        with open(os.path.join(args.out, p["date"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(published, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Published {len(puzzles)} puzzle file(s) + manifest.json to {args.out}")
    print("Upload the new/changed files under that folder — index.html itself never needs to change again.")


if __name__ == "__main__":
    main()
