# CLAUDE.md — Rinkari puzzle pipeline

You are helping produce daily cryptic puzzles for Rinkari (four or five cryptic
clues whose answers are all connected by one hidden Link — see "Two kinds of
Link" below). Five is the default for pipeline-drafted puzzles; four is used
for puzzles sourced from `puzzle-creator-app/` (real published clues picked
via that tool — see its README for the copyright caveat before publishing).

## Two kinds of Link
Rinkari's Link has two valid mechanics — always check which one fits before
mining or drafting:
- **compound** (the original, still the default and usually the stronger
  puzzle): the Link is a word that combines with every answer to form a real
  compound — CAMP+FIRE, SURE+FIRE, SPIT+FIRE. Mine these from
  `data/compounds.txt` via `mine_links.py --mode compound`.
- **category**: the Link is a category name, and the five answers are simply
  members of it — BIRDS: ROBIN, WREN, CROW, HAWK, OWL. No compounding at all.
  Mine these from `data/categories.json` via `mine_links.py --mode category`.
  Use category links for variety (not every day — compound links are the
  house style) and when a great category surfaces that compound-mining can't
  reach (colours, chess pieces, car brands, gemstones, etc).
Never mix the two within one puzzle. Every clue in a puzzle serves the same
link mechanic.

## Repo layout
- `data/compounds.txt` — compound word pairs, one per line, format `LEFT+RIGHT` (e.g. `CAMP+FIRE`)
- `data/categories.json` — category name -> list of members, for category-type links
- `data/indicators.json` — known fair indicator words per cryptic device
- `scripts/mine_links.py` — finds Link candidates, both types (`--mode compound|category|both`)
- `scripts/lint_clues.py` — mechanical fairness checks on a puzzle JSON
- `scripts/build_puzzles.py` — validates all puzzles and publishes per-day
  JSON + manifest.json into the site's `puzzles/` folder (the site fetches
  these at runtime; `index.html` is never touched by this script)
- `puzzles/YYYY-MM-DD.json` — one puzzle per file, filename is the release date
- `prompts/clue-style-guide.md` — REQUIRED READING before drafting any clue
- `review/` — generated review sheets for the human ear-test

## The batch workflow you will be asked to run
1. `python3 scripts/mine_links.py --mode both` -> ranked Link candidates of
   both types. Human picks N link-sets (mostly compound, some category for
   variety). For category picks, if the category isn't yet in
   `data/categories.json`, add it there (with a fuller member list than just
   the 5 you'll use — future batches can then reuse it).
2. For each link-set: choose 5 answers with varied lengths (compound: also
   vary prefix/suffix attachment).
3. Read `prompts/clue-style-guide.md`. Draft TWO candidate clues per answer with a
   device mix per puzzle of: 1 hidden, 1 anagram OR reversal, 1 charade OR container,
   2 double definitions (max). Never two hiddens in one puzzle.
4. Write each puzzle as `puzzles/YYYY-MM-DD.json` (schema below), consecutive dates,
   consecutive numbers. Set `"link_type"` explicitly ("compound" or "category").
5. Run `python3 scripts/lint_clues.py puzzles/*.json`. Fix every ERROR yourself.
   Leave WARNs with a one-line justification in the review sheet.
6. Generate `review/batch-<date>.md`: one line per clue with both candidates, the
   parse, and lint status, for the human to mark keep/swap.
7. After human edits land, run `python3 scripts/build_puzzles.py --out ../rinkari/puzzles`
   to validate the full set and publish it. This writes one `<date>.json` per
   puzzle plus `manifest.json` into the site's `puzzles/` folder — the site
   fetches these at runtime (anchored to Europe/London for the daily
   rollover), so `index.html` itself never needs to be re-uploaded again
   after its first deploy. Never hand-edit anything under the site's
   `puzzles/` folder — it's generated output.

## Puzzle JSON schema (must match exactly)
{
  "number": 4,
  "date": "2026-07-06",
  "link": "BOARD",
  "link_type": "compound",
  "compounds": "KEYBOARD · CARDBOARD · SURFBOARD · DASHBOARD · CHALKBOARD",
  "note": "Setter's note for the solution page.",
  "clues": [
    {
      "answer": "KEY",
      "device": "Double definition",
      "parts": [["Essential","def"], [" ",""], ["island","ind"], [" (3)",""]],
      "parse": "Double definition: essential, and a low island."
    }
  ]
}
`link_type` is `"compound"` (default if omitted, for back-compat with older
puzzles) or `"category"`. For category puzzles, `compounds` still holds the
display string — just list the members instead of compound words, e.g.
`"ROBIN · WREN · CROW · HAWK · OWL"`.
`parts` renders the clue: each element is [text, role] where role is "def"
(definition, highlighted by hint 1), "ind" (wordplay indicator or second
definition, highlighted by hint 2), or "" (plain text). The enumeration "(N)"
is always the final part.

## Hard rules (the linter enforces most of these)
- Definition must sit at the start or end of the clue, never the middle.
- Enumeration must equal answer length.
- The answer must never appear in the clue surface.
- Hidden answers must actually be findable in the surface letters.
- Anagram fodder must be present in the surface and be a real letter-match.
- Devices must use indicators from data/indicators.json, or justify the exception.
- Compound links: every answer+link (or link+answer) must appear in data/compounds.txt.
- Category links: every answer must be listed under that category in data/categories.json.
- Surface reading must tell a tiny coherent story. If it reads like word salad,
  rewrite it. This is the one rule only taste can enforce.
