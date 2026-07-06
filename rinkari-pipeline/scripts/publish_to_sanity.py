#!/usr/bin/env python3
"""Publish puzzles/*.json into the Sanity dataset (the CMS backing the site).

Usage:
  python3 scripts/publish_to_sanity.py [--dry-run] [--only YYYY-MM-DD]

Reads SANITY_PROJECT_ID / SANITY_DATASET / SANITY_WRITE_TOKEN from .env in
this directory (gitignored — never commit that file). Lints everything
first and aborts on any ERROR. Each puzzle is createOrReplace'd with a
deterministic _id ("puzzle-<date>"), so rerunning after editing a single
puzzle file is safe and idempotent.
"""
import argparse, glob, json, os, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
PUZZLE_DIR = os.path.join(ROOT, "puzzles")
sys.path.insert(0, HERE)
import lint_clues as L

CHUNK = 100


def load_env():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        print(f"ERROR: {path} not found. See CLAUDE.md for how to create the Sanity write token.")
        sys.exit(1)
    env = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    for required in ("SANITY_PROJECT_ID", "SANITY_DATASET", "SANITY_WRITE_TOKEN"):
        if required not in env:
            print(f"ERROR: {required} missing from .env")
            sys.exit(1)
    return env


def to_sanity_doc(p):
    clues = []
    for i, c in enumerate(p["clues"]):
        parts = [
            {"_type": "puzzlePart", "_key": f"p{j}", "text": t, "role": r}
            for j, (t, r) in enumerate(c["parts"])
        ]
        clues.append({
            "_type": "puzzleClue",
            "_key": f"c{i}",
            "answer": c["answer"],
            "device": c["device"],
            "parts": parts,
            "parse": c["parse"],
        })
    return {
        "_id": "puzzle-" + p["date"],
        "_type": "puzzle",
        "number": p["number"],
        "date": p["date"],
        "link": p["link"],
        "linkType": p.get("link_type", "compound"),
        "compounds": p["compounds"],
        "note": p.get("note", ""),
        "clues": clues,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="only publish the puzzle for this date (YYYY-MM-DD)")
    args = ap.parse_args()

    env = load_env()
    paths = sorted(glob.glob(os.path.join(PUZZLE_DIR, "*.json")))
    if args.only:
        paths = [p for p in paths if os.path.basename(p) == args.only + ".json"]
        if not paths:
            print(f"No puzzle file found for {args.only}")
            sys.exit(1)

    problems = []
    for path in paths:
        L.lint_puzzle(path, problems)
    errs = [m for lvl, m in problems if lvl == "ERROR"]
    if errs:
        for m in errs:
            print("ERROR:", m)
        print("\nAborted: fix lint errors first.")
        sys.exit(1)

    puzzles = [json.load(open(p, encoding="utf-8")) for p in paths]
    mutations = [{"createOrReplace": to_sanity_doc(p)} for p in puzzles]

    print(f"{len(mutations)} puzzle(s) ready for Sanity project {env['SANITY_PROJECT_ID']} / {env['SANITY_DATASET']}")
    if args.dry_run:
        print("(dry run — nothing sent)")
        return

    url = f"https://{env['SANITY_PROJECT_ID']}.api.sanity.io/v2024-01-01/data/mutate/{env['SANITY_DATASET']}"
    for i in range(0, len(mutations), CHUNK):
        chunk = mutations[i:i + CHUNK]
        body = json.dumps({"mutations": chunk}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {env['SANITY_WRITE_TOKEN']}",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            print(f"ERROR: Sanity API returned {e.code}: {e.read().decode('utf-8', 'replace')}")
            sys.exit(1)
        print(f"  published {min(i + CHUNK, len(mutations))}/{len(mutations)}")

    print(f"\nPublished {len(mutations)} puzzle(s) to Sanity.")


if __name__ == "__main__":
    main()
