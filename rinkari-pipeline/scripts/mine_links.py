#!/usr/bin/env python3
"""Mine Link candidates from data/compounds.txt (compound-type links) and
data/categories.json (category-type links).

Rinkari's Link mechanic has two forms:
  - COMPOUND: every answer combines with the Link word to form a real
    compound (CAMP+FIRE, SURE+FIRE, ...). Chips resolve to ANSWER+LINK.
  - CATEGORY: every answer is simply a member of a category the Link names
    (BIRDS: ROBIN, WREN, CROW, HAWK, OWL). No combining; the answers ARE
    the category members.

Usage:
  python3 scripts/mine_links.py --mode compound  [--min-partners 5] [--top 40] [--used FIRE,LIGHT]
  python3 scripts/mine_links.py --mode category  [--min-members 5]  [--used BIRDS,COLOURS]
  python3 scripts/mine_links.py --mode both      (default; runs both, tagged)
"""
import argparse, json, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOUNDS = os.path.join(HERE, "..", "data", "compounds.txt")
CATEGORIES = os.path.join(HERE, "..", "data", "categories.json")


def load_pairs(path):
    pairs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().upper()
            if not line or line.startswith("#") or "+" not in line:
                continue
            left, right = line.split("+", 1)
            if left and right:
                pairs.append((left, right))
    return pairs


def mine_compound(pairs):
    partners = defaultdict(list)  # link -> [(partner, mode)] mode: 'suffix' means PARTNER+LINK
    for left, right in pairs:
        partners[right].append((left, "suffix"))   # left attaches before right => right is link used as suffix
        partners[left].append((right, "prefix"))   # right attaches after left => left is link used as prefix
    return partners


def score_compound(link, plist):
    n = len(plist)
    modes = {m for _, m in plist}
    mode_bonus = 2 if len(modes) == 2 else 0
    lengths = {len(p) for p, _ in plist}
    variety = min(len(lengths), 4)
    short = sum(1 for p, _ in plist if len(p) <= 5)
    return n * 3 + mode_bonus + variety + short * 0.5


def run_compound(args, used, rows):
    pairs = load_pairs(COMPOUNDS)
    partners = mine_compound(pairs)
    for link, plist in partners.items():
        if link in used:
            continue
        uniq = sorted(set(plist))
        if len(uniq) < args.min_partners:
            continue
        rows.append({
            "type": "compound",
            "link": link,
            "count": len(uniq),
            "score": round(score_compound(link, uniq), 1),
            "partners": [{"word": p, "mode": m} for p, m in uniq],
        })


def run_category(args, used, rows):
    if not os.path.exists(CATEGORIES):
        return
    categories = json.load(open(CATEGORIES, encoding="utf-8"))
    for name, members in categories.items():
        if name.upper() in used:
            continue
        uniq = sorted({m.upper() for m in members})
        if len(uniq) < args.min_members:
            continue
        lengths = {len(m.replace(" ", "")) for m in uniq}
        variety = min(len(lengths), 4)
        score = len(uniq) * 3 + variety
        rows.append({
            "type": "category",
            "link": name.upper(),
            "count": len(uniq),
            "score": round(score, 1),
            "members": uniq,
        })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["compound", "category", "both"], default="both")
    ap.add_argument("--min-partners", type=int, default=5, help="compound mode: min compound partners")
    ap.add_argument("--min-members", type=int, default=5, help="category mode: min category members")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--used", default="", help="comma-separated links already used, to exclude (either type)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args()

    used = {w.strip().upper() for w in args.used.split(",") if w.strip()}
    rows = []
    if args.mode in ("compound", "both"):
        run_compound(args, used, rows)
    if args.mode in ("category", "both"):
        run_category(args, used, rows)

    rows.sort(key=lambda r: -r["score"])
    rows = rows[: args.top]

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print(f"{len(rows)} link candidates (mode={args.mode})\n")
    for r in rows:
        if r["type"] == "compound":
            ps = ", ".join(
                (f"{p['word']}+{r['link']}" if p["mode"] == "suffix" else f"{r['link']}+{p['word']}")
                for p in r["partners"]
            )
            print(f"  [compound] {r['link']:<14} score {r['score']:>6}  ({r['count']} partners): {ps}")
        else:
            print(f"  [category] {r['link']:<14} score {r['score']:>6}  ({r['count']} members): {', '.join(r['members'])}")


if __name__ == "__main__":
    main()
