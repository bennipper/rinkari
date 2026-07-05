#!/usr/bin/env python3
"""Bulk-import puzzles from puzzle-creator-app/puzzle_matches_final.json.

Each source entry is a connection word + 4 members + up to 5 real published
clue options per member. This script picks ONE clue per member and
classifies its device MECHANICALLY, not by genuine cryptic-solving judgment
— there is no attempt to reverse-engineer the true wordplay of 2,600+ real
clues by hand. The classification is honest about what it doesn't know:

  - If the dataset's own "definition" field is "X/Y" and the clue text is
    just X <link word(s)> Y, that's a real, verifiable Double definition —
    both halves of the surface ARE genuine definitions of the answer.
  - Otherwise the definition must sit at an edge (hard rule). The remaining
    wordplay is checked for a positively-identifiable Hidden/Anagram/Reversal
    pattern (present indicator word + a structural match, exactly what
    lint_clues.py itself checks). If none is found, it's labelled Charade —
    the honest catch-all — with a parse that states only what's actually
    known (the definition), not a fabricated letter-by-letter breakdown.

Every candidate clue is run through the real lint_clue() validator before
being accepted, so nothing gets published that a lint pass wouldn't also
pass on ERRORs (WARNs, e.g. "not in categories.json yet", are expected and
resolved by this script writing categories.json itself).

A whole puzzle (all 4 members) is only kept if every member has at least one
usable clue; otherwise the whole puzzle is skipped. Members with multi-word
or non-alphabetic answers are skipped (the site's per-letter input cells
can't accept a space).

Usage:
  python3 scripts/import_creator_app.py [--limit N] [--dry-run]
"""
import argparse, glob, json, os, re, sys
from collections import Counter
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lint_clues as L

ROOT = os.path.join(HERE, "..")
PUZZLE_DIR = os.path.join(ROOT, "puzzles")
CATEGORIES_PATH = os.path.join(ROOT, "data", "categories.json")
SOURCE_JSON = os.path.join(ROOT, "..", "puzzle-creator-app", "puzzle_matches_final.json")

ENUM_RE = re.compile(r"\s*\((\d+(?:[-,]\d+)*)\)\s*$")
TRAIL_PUNCT_MAX = 2  # tolerate up to 2 stray trailing chars (?, !, etc.) after the definition


def strip_enum(clue):
    m = ENUM_RE.search(clue)
    if not m:
        return None, None
    return clue[: m.start()].rstrip(), m.group(1)


def letters(s):
    return re.sub(r"[^A-Za-z]", "", s).upper()


def bank_hit(text_upper, device):
    bank = [w.upper() for w in L.INDICATORS.get(device, [])]
    return any(w in text_upper for w in bank)


def reveals_link(text, link):
    """True if a definition snippet is just the category name itself (e.g.
    def='Dog' when link='DOG') — that would give the whole category away
    before the solver finishes the first clue, defeating the category
    mechanic's discovery. Synonyms (e.g. 'canine') are fine and expected;
    only the literal name (plus trivial plural/singular) is rejected."""
    t = re.sub(r"[^A-Za-z]", "", text).upper()
    l = re.sub(r"[^A-Za-z]", "", link).upper()
    if not t or not l:
        return False
    variants = {l, l + "S", l + "ES"}
    if l.endswith("S"):
        variants.add(l[:-1])
    if l.endswith("ES"):
        variants.add(l[:-2])
    return t in variants


def validate(answer, device, parts, parse, link):
    """Run the real linter's per-clue check; True only if zero ERRORs."""
    clue_obj = {"answer": answer, "device": device, "parts": parts, "parse": parse}
    problems = []
    L.lint_clue(0, 0, clue_obj, link, "category", problems)
    if any(lvl == "ERROR" for lvl, _ in problems):
        return None
    return clue_obj


def find_end_split(surface, defn):
    """Return the index where def_part begins if defn matches the (possibly
    punctuation-trailed) end of surface, else None."""
    dl = defn.lower().strip()
    for trail in range(0, TRAIL_PUNCT_MAX + 1):
        core = surface[: len(surface) - trail] if trail else surface
        if core.lower().endswith(dl):
            return len(core) - len(dl)
    return None


def try_build_clue(member, cand, link):
    answer = member.strip().upper()
    if not answer.isalpha():
        return None
    if cand.get("answer", "").strip().upper() != answer:
        return None
    defn = (cand.get("definition") or "").strip()
    if not defn:
        return None
    if not ("/" in defn) and reveals_link(defn, link):
        return None
    clue_text = (cand.get("clue") or "").strip()
    surface, enum = strip_enum(clue_text)
    if surface is None:
        return None
    total = sum(int(x) for x in re.split(r"[-,]", enum))
    if total != len(answer):
        return None

    sl = surface.lower()

    # 1) Double-definition: dataset marks the def as "X/Y" and the surface is
    #    just those two definitions back to back (a real, verifiable DD).
    if "/" in defn:
        d1, d2 = [x.strip() for x in defn.split("/", 1)]
        if d1 and d2 and not reveals_link(d1, link) and not reveals_link(d2, link):
            end_split = find_end_split(surface, d2)
            if sl.startswith(d1.lower()) and end_split is not None and end_split >= len(d1):
                def1 = surface[: len(d1)]
                def2_full = surface[end_split:]
                mid = surface[len(d1) : end_split]
                parts = [[def1, "def"], [mid, ""], [def2_full, "ind"], [f" ({enum})", ""]]
                c = validate(answer, "Double definition", parts,
                             f"Double definition: {d1.lower()}, and {d2.lower()}.", link)
                if c:
                    return c

    # 2) Single definition: must sit at an edge.
    def_part = rest = None
    if sl.startswith(defn.lower()):
        def_part = surface[: len(defn)]
        rest = surface[len(defn):]
        at_start = True
    else:
        split = find_end_split(surface, defn)
        if split is not None:
            def_part = surface[split:]
            rest = surface[:split]
            at_start = False
    if def_part is None or not rest.strip():
        return None

    rest_upper = rest.upper()
    rest_letters = letters(rest)
    rest_words = [letters(w) for w in rest.split() if letters(w)]
    parts = [[def_part, "def"], [rest, "ind"], [f" ({enum})", ""]] if at_start else \
            [[rest, "ind"], [def_part, "def"], [f" ({enum})", ""]]

    # Hidden word: answer sits in the wordplay letters, not as a whole word,
    # and a real hidden-word indicator is present.
    if answer in rest_letters and answer not in rest_words and bank_hit(rest_upper, "Hidden word"):
        c = validate(answer, "Hidden word", parts,
                     f"Hidden word — the definition is '{defn}'; the answer is concealed in the surrounding wordplay.", link)
        if c:
            return c

    # Anagram: a real word in the wordplay is a letter-for-letter match, with
    # a genuine anagram indicator present.
    fodder = [w for w in rest_words if w != answer and sorted(w) == sorted(answer)]
    if fodder and bank_hit(rest_upper, "Anagram"):
        c = validate(answer, "Anagram", parts,
                     f"Anagram — the definition is '{defn}'; a word in the wordplay rearranges to the answer.", link)
        if c:
            return c

    # Reversal: the reversed answer appears in the wordplay, with a genuine
    # reversal indicator present.
    rev = answer[::-1]
    if (rev in rest_words or rev in rest_letters) and bank_hit(rest_upper, "Reversal"):
        c = validate(answer, "Reversal", parts,
                     f"Reversal — the definition is '{defn}'; the wordplay reversed gives the answer.", link)
        if c:
            return c

    # Charade: the honest catch-all when no mechanism above can be verified.
    # The parse states only what's actually known — the definition — rather
    # than inventing a letter-by-letter breakdown that hasn't been checked.
    c = validate(answer, "Charade", parts,
                 f"The definition is '{defn}'; the rest of the clue builds the answer as wordplay.", link)
    return c


def load_existing_puzzles():
    # Only published puzzles count for numbering/dating continuity — unreviewed
    # drafts sitting in _drafts_unreviewed/ haven't been approved or published
    # and shouldn't reserve dates the live queue could otherwise use.
    paths = sorted(glob.glob(os.path.join(PUZZLE_DIR, "*.json")))
    used_combos, max_number, max_date = set(), 0, None
    for p in paths:
        d = json.load(open(p, encoding="utf-8"))
        link = d["link"].strip().upper()
        if d.get("link_type", "compound") == "category":
            members = frozenset(m.strip().upper() for m in d["compounds"].split("·"))
            used_combos.add((link, members))
        max_number = max(max_number, d["number"])
        dt = date.fromisoformat(d["date"])
        max_date = dt if max_date is None else max(max_date, dt)
    return used_combos, max_number, max_date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process the first N source entries (for testing)")
    ap.add_argument("--dry-run", action="store_true", help="report stats but write nothing")
    args = ap.parse_args()

    used_combos, max_number, max_date = load_existing_puzzles()
    source = json.load(open(SOURCE_JSON, encoding="utf-8"))
    if args.limit:
        source = source[: args.limit]
    categories = json.load(open(CATEGORIES_PATH, encoding="utf-8")) if os.path.exists(CATEGORIES_PATH) else {}

    accepted = []
    skipped = Counter()
    seen_combos = set()

    for entry in source:
        link = entry["connectionWord"].strip().upper()
        members = [m.strip().upper() for m in entry.get("members", [])]
        if len(members) != 4:
            skipped["not 4 members"] += 1
            continue
        if any(not m.isalpha() for m in members):
            skipped["multi-word or non-alphabetic member"] += 1
            continue
        if len(set(members)) != 4:
            skipped["duplicate member within puzzle"] += 1
            continue
        combo = (link, frozenset(members))
        if combo in used_combos or combo in seen_combos:
            skipped["identical link+members already used"] += 1
            continue

        clues, ok = [], True
        for m in members:
            built = None
            for cand in entry.get("cluesPerMember", {}).get(m, []):
                built = try_build_clue(m, cand, link)
                if built:
                    break
            if not built:
                ok = False
                break
            clues.append(built)
        if not ok:
            skipped["no valid clue for a member"] += 1
            continue

        seen_combos.add(combo)
        accepted.append({"link": link, "members": members, "clues": clues, "context": entry.get("context", "")})

    start_number = max_number + 1
    start_date = (max_date + timedelta(days=1)) if max_date else date.today()

    device_counts = Counter(c["device"] for a in accepted for c in a["clues"])
    print(f"Source entries: {len(source)}")
    print(f"Accepted: {len(accepted)}")
    print("Skipped:")
    for reason, cnt in skipped.most_common():
        print(f"  {reason}: {cnt}")
    print("Device mix across accepted clues:")
    for dev, cnt in device_counts.most_common():
        print(f"  {dev}: {cnt}")
    if accepted:
        end_date = start_date + timedelta(days=len(accepted) - 1)
        print(f"Would number {start_number}..{start_number + len(accepted) - 1}, "
              f"dated {start_date.isoformat()}..{end_date.isoformat()}")

    if args.dry_run or not accepted:
        return

    for i, acc in enumerate(accepted):
        num = start_number + i
        d = start_date + timedelta(days=i)
        puzzle = {
            "number": num,
            "date": d.isoformat(),
            "link": acc["link"],
            "link_type": "category",
            "compounds": " · ".join(acc["members"]),
            "note": acc["context"] or f"A category day — {', '.join(acc['members'])} are all {acc['link']}.",
            "clues": acc["clues"],
        }
        with open(os.path.join(PUZZLE_DIR, d.isoformat() + ".json"), "w", encoding="utf-8") as f:
            json.dump(puzzle, f, ensure_ascii=False, indent=2)

        existing = categories.get(acc["link"])
        if existing is None:
            categories[acc["link"]] = acc["members"]
        else:
            categories[acc["link"]] = sorted(set(m.upper() for m in existing) | set(acc["members"]))

    with open(CATEGORIES_PATH, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {len(accepted)} puzzle file(s) and updated {CATEGORIES_PATH}")


if __name__ == "__main__":
    main()
