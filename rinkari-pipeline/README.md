# Rinkari puzzle pipeline

Batch-produce daily cryptic puzzles: mine Link candidates, draft clues with
Claude Code, lint mechanically, ear-test by hand, and publish a self-releasing
queue that the site fetches at runtime.

## One-time setup
1. Put this folder and your site's `index.html` in one repo:
   ```
   rinkari/
     index.html          <- the live site (fetches puzzles/ at runtime)
     puzzles/             <- published per-day JSON + manifest.json (generated, don't hand-edit)
   rinkari-pipeline/       <- this folder
   ```
2. Open the repo in Claude Code. It reads `CLAUDE.md` automatically.

## The monthly ritual (~2 hours for ~3 weeks of puzzles)
1. **Mine**: `python3 scripts/mine_links.py --min-partners 5 --used FIRE,LIGHT,SHIP,BOARD`
   Pick the link-sets you like from the ranked list.
2. **Draft**: tell Claude Code: *"Draft puzzles No. 5-24 for dates 2026-07-07
   onward using links X, Y, Z... following CLAUDE.md."* It writes
   `puzzles/YYYY-MM-DD.json` files, lints its own work, and produces a review
   sheet in `review/`.
3. **Ear-test**: read the review sheet, mark keep/swap per clue, have Claude
   Code apply your edits.
4. **Publish**: `python3 scripts/build_puzzles.py --out ../rinkari/puzzles`
   Validates everything, then writes one `<date>.json` per puzzle plus a
   lightweight `manifest.json` (just `{number,date}` — no answers) into the
   site's `puzzles/` folder. `index.html` itself is never touched.
5. **Deploy**: upload whatever changed under `rinkari/puzzles/` (new dates +
   the refreshed `manifest.json`). The first time, upload `index.html` too —
   after that you never need to touch it again. Puzzles release themselves
   at midnight **UK time** (Europe/London, so it correctly follows the
   GMT/BST clock change) because the site fetches `puzzles/manifest.json` and
   picks the latest date ≤ today itself. Gaps are safe: the site holds the
   latest released puzzle rather than breaking.

Note this is a fully static setup (no backend): the per-day JSON files for
queued future dates do already sit on the host once uploaded, so a visitor
who somehow guessed a future date's URL could fetch it early. The manifest
itself never reveals answers, and the UI never links to a date before it
arrives — a real backend (à la how NYT Wordle now gates by date server-side)
would close that residual gap, but wasn't judged worth the extra
infrastructure for this project.

## Growing the data
- `data/compounds.txt` — add `LEFT+RIGHT` lines whenever you meet a good
  compound. More pairs = more Link candidates. (Public crossword datasets'
  *answers* columns are fair game to mine; never republish their clues.)
- `data/indicators.json` — add legitimate indicator words as you encounter
  them; the linter warns on unknown ones.

## Scripts
- `mine_links.py` — ranked Link candidates (`--json` for machine output)
- `lint_clues.py puzzles/*.json` — exit 1 on ERROR; WARNs are advisories
- `build_puzzles.py --out <dir> [--dry-run]` — validate + publish per-day
  JSON + manifest.json into `<dir>` (e.g. `../rinkari/puzzles`)
