#!/usr/bin/env python3
"""Fairness linter for Rinkari puzzle JSON files.

Usage: python3 scripts/lint_clues.py puzzles/*.json
Exit code 1 if any ERROR. WARNs are advisory (justify or fix).
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDICATORS = json.load(open(os.path.join(HERE, "..", "data", "indicators.json"), encoding="utf-8"))
COMPOUND_LINES = [
    l.strip().upper() for l in open(os.path.join(HERE, "..", "data", "compounds.txt"), encoding="utf-8")
    if l.strip() and not l.startswith("#") and "+" in l
]
COMPOUNDS = {tuple(l.split("+", 1)) for l in COMPOUND_LINES}
CATEGORIES_PATH = os.path.join(HERE, "..", "data", "categories.json")
CATEGORIES = json.load(open(CATEGORIES_PATH, encoding="utf-8")) if os.path.exists(CATEGORIES_PATH) else {}
CATEGORIES = {k.upper(): {m.upper() for m in v} for k, v in CATEGORIES.items()}

KNOWN_DEVICES = {"Hidden word", "Anagram", "Reversal", "Charade", "Container", "Double definition"}
ONLY_LETTERS = re.compile(r"[^A-Z]")


def letters(s):
    return ONLY_LETTERS.sub("", s.upper())


def surface_of(parts):
    return "".join(t for t, _ in parts)


def lint_clue(pnum, ci, clue, link, link_type, problems):
    where = f"puzzle {pnum} clue {ci+1} ({clue.get('answer','?')})"
    answer = clue.get("answer", "").upper()
    device = clue.get("device", "")
    parts = clue.get("parts", [])
    surface = surface_of(parts)

    # schema basics
    if not answer or not answer.isalpha():
        problems.append(("ERROR", f"{where}: missing/invalid answer")); return
    if device not in KNOWN_DEVICES:
        problems.append(("ERROR", f"{where}: unknown device '{device}'"))
    roles = [r for _, r in parts]
    if "def" not in roles:
        problems.append(("ERROR", f"{where}: no part marked 'def'"))

    # enumeration
    m = re.search(r"\((\d+(?:[,-]\d+)*)\)\s*$", surface)
    if not m:
        problems.append(("ERROR", f"{where}: no enumeration at end of clue"))
    else:
        total = sum(int(x) for x in re.split(r"[,-]", m.group(1)))
        if total != len(answer):
            problems.append(("ERROR", f"{where}: enumeration ({m.group(1)}) != answer length {len(answer)}"))

    # definition at an edge (ignoring the enumeration part and whitespace-only parts)
    content = [(t, r) for t, r in parts if letters(t)]
    if content:
        first_role, last_role = content[0][1], content[-1][1]
        if "def" in roles and first_role != "def" and last_role != "def":
            # double definitions store the second def as 'ind'; def must still touch an edge
            problems.append(("ERROR", f"{where}: definition is not at the start or end of the clue"))

    # answer must not appear in the surface (outside a hidden-word span check below)
    surf_letters = letters(surface)
    surface_words = [letters(w) for w in re.split(r"\s+", surface) if letters(w)]
    if device != "Hidden word" and answer in surface_words:
        problems.append(("ERROR", f"{where}: answer appears verbatim in the surface"))

    # device-specific mechanics
    ind_text = " ".join(t for t, r in parts if r == "ind").strip().lower()
    bank = [w.lower() for w in INDICATORS.get(device, [])]
    if device == "Hidden word":
        if answer not in surf_letters:
            problems.append(("ERROR", f"{where}: hidden answer not findable in surface letters"))
        elif answer in surface_words:
            problems.append(("ERROR", f"{where}: 'hidden' answer is just a whole word in the surface"))
        if bank and ind_text and not any(w in ind_text for w in bank):
            problems.append(("WARN", f"{where}: hidden indicator '{ind_text}' not in bank"))
    elif device == "Anagram":
        fodder = [w for w in surface_words if w != answer and sorted(w) == sorted(answer)]
        if not fodder:
            problems.append(("ERROR", f"{where}: no anagram fodder in surface matching answer letters"))
        if bank and ind_text and not any(w in ind_text for w in bank):
            problems.append(("WARN", f"{where}: anagram indicator '{ind_text}' not in bank"))
    elif device == "Reversal":
        rev = answer[::-1]
        if rev not in surface_words and rev not in surf_letters:
            problems.append(("WARN", f"{where}: reversed answer '{rev}' not visible in surface (synonym reversal? verify parse)"))
        if bank and ind_text and not any(w in ind_text for w in bank):
            problems.append(("WARN", f"{where}: reversal indicator '{ind_text}' not in bank"))
    elif device == "Container":
        if bank and ind_text and not any(w in ind_text for w in bank):
            problems.append(("WARN", f"{where}: container indicator '{ind_text}' not in bank"))

    # link check — mechanism depends on link_type
    if link_type == "category":
        members = CATEGORIES.get(link)
        if members is None:
            problems.append(("WARN", f"{where}: category '{link}' not in data/categories.json (add it, or confirm it's a valid new category)"))
        elif answer not in members:
            problems.append(("WARN", f"{where}: {answer} not listed under category '{link}' in data/categories.json (add it if it genuinely belongs)"))
    else:
        if (answer, link) not in COMPOUNDS and (link, answer) not in COMPOUNDS:
            problems.append(("WARN", f"{where}: {answer}+{link} / {link}+{answer} not in data/compounds.txt (add it if valid)"))

    # parse present
    if not clue.get("parse"):
        problems.append(("ERROR", f"{where}: missing parse explanation"))


def lint_puzzle(path, problems):
    p = json.load(open(path, encoding="utf-8"))
    fname_date = os.path.splitext(os.path.basename(path))[0]
    for field in ("number", "date", "link", "compounds", "note", "clues"):
        if field not in p:
            problems.append(("ERROR", f"{path}: missing field '{field}'")); return p
    if p["date"] != fname_date:
        problems.append(("ERROR", f"{path}: date field {p['date']} != filename date {fname_date}"))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", p["date"]):
        problems.append(("ERROR", f"{path}: bad date format"))
    if len(p["clues"]) not in (4, 5):
        problems.append(("ERROR", f"{path}: expected 4 or 5 clues, got {len(p['clues'])}"))
    devices = [c.get("device") for c in p["clues"]]
    if devices.count("Hidden word") > 1:
        problems.append(("WARN", f"{path}: more than one hidden-word clue"))
    if devices.count("Double definition") > 2:
        problems.append(("WARN", f"{path}: more than two double definitions"))
    link = p["link"].upper()
    link_type = p.get("link_type", "compound")
    if link_type not in ("compound", "category"):
        problems.append(("ERROR", f"{path}: link_type must be 'compound' or 'category', got '{link_type}'"))
    for ci, clue in enumerate(p["clues"]):
        lint_clue(p["number"], ci, clue, link, link_type, problems)
    return p


def main():
    paths = sys.argv[1:]
    if not paths:
        print("usage: lint_clues.py puzzles/*.json"); sys.exit(2)
    problems = []
    for path in sorted(paths):
        lint_puzzle(path, problems)
    errs = [m for lvl, m in problems if lvl == "ERROR"]
    warns = [m for lvl, m in problems if lvl == "WARN"]
    for m in errs:
        print("ERROR:", m)
    for m in warns:
        print("WARN: ", m)
    print(f"\n{len(paths)} file(s): {len(errs)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
