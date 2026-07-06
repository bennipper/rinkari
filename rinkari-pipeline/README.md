# Rinkari puzzle pipeline

Batch-produce daily cryptic puzzles: mine Link candidates, draft clues with
Claude Code, lint mechanically, ear-test by hand, and publish into Sanity —
the CMS the live site queries at runtime for its self-releasing queue.

## One-time setup
1. Repo layout:
   ```
   rinkari/                <- the live site (queries Sanity at runtime)
   rinkari-pipeline/        <- this folder
   sanity-studio/           <- CMS admin UI (npm run dev to edit puzzles by hand)
   ```
2. Open the repo in Claude Code. It reads `CLAUDE.md` automatically.
3. Create `rinkari-pipeline/.env` (gitignored — never commit it) with:
   ```
   SANITY_PROJECT_ID=uhde7616
   SANITY_DATASET=production
   SANITY_WRITE_TOKEN=<an editor-role token — see below>
   ```
   Create a write token with `npx sanity tokens add "label" --role=editor --yes --json`
   from `sanity-studio/` (requires `npx sanity login` once first). The
   project ID/dataset aren't secret — the write token is; it grants edit
   access to all puzzle content.

## The monthly ritual (~2 hours for ~3 weeks of puzzles)
1. **Mine**: `python3 scripts/mine_links.py --min-partners 5 --used FIRE,LIGHT,SHIP,BOARD`
   Pick the link-sets you like from the ranked list.
2. **Draft**: tell Claude Code: *"Draft puzzles No. 5-24 for dates 2026-07-07
   onward using links X, Y, Z... following CLAUDE.md."* It writes
   `puzzles/YYYY-MM-DD.json` files, lints its own work, and produces a review
   sheet in `review/`.
3. **Ear-test**: read the review sheet, mark keep/swap per clue, have Claude
   Code apply your edits.
4. **Publish**: `python3 scripts/publish_to_sanity.py`
   Validates everything, then `createOrReplace`s each puzzle as a document
   in Sanity. Idempotent — safe to rerun after fixing a single puzzle file.
5. **Deploy**: nothing to upload. The site already queries Sanity's public
   read API directly; `index.html` was uploaded once and never needs to
   change again. Puzzles release themselves at midnight **UK time** (Europe/
   London, so it correctly follows the GMT/BST clock change) because the
   site queries for every puzzle's `{number,date}` and picks the latest date
   ≤ today itself. Gaps are safe: the site holds the latest released puzzle
   rather than breaking.

Quick one-off fixes (a typo in a live puzzle) can be made directly in Sanity
Studio (`cd sanity-studio && npm run dev`, open localhost:3333) without
touching this pipeline at all — but if that puzzle's source `.json` file
still exists here, a later `publish_to_sanity.py` run will overwrite the
Studio-only edit. For anything more than a quick fix, edit the JSON here and
republish, so the pipeline's lint/fairness checks stay authoritative.

The Sanity dataset is **public-read** (no token needed for the site to fetch)
but the full puzzle documents — including ones dated in the future — do sit
in a queryable dataset once published, so a visitor who crafted the right
API query could fetch a future date's answers early. Site navigation only
ever surfaces a date once it's arrived, and a real backend gate (à la how NYT
Wordle now serves by date server-side) would close that residual gap — not
judged worth the extra infrastructure for this project.

## Growing the data
- `data/compounds.txt` — add `LEFT+RIGHT` lines whenever you meet a good
  compound. More pairs = more Link candidates. (Public crossword datasets'
  *answers* columns are fair game to mine; never republish their clues.)
- `data/indicators.json` — add legitimate indicator words as you encounter
  them; the linter warns on unknown ones.

## Scripts
- `mine_links.py` — ranked Link candidates (`--json` for machine output)
- `lint_clues.py puzzles/*.json` — exit 1 on ERROR; WARNs are advisories
- `publish_to_sanity.py [--dry-run] [--only YYYY-MM-DD]` — the real publish
  step: lint, then push into Sanity
- `build_puzzles.py --out <dir> [--dry-run]` — legacy local export (per-day
  JSON + manifest.json to a folder); kept for offline backup, not what the
  live site reads from anymore
