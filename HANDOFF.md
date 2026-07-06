# Rinkari — Project Handoff

Written 2026-07-05 by the previous Claude Code agent, for whoever picks this
up next (human or agent). Read this top to bottom before touching anything —
especially **Unresolved issues**, which lists everything known-broken or
known-risky that was NOT fixed.

---

## 1. What Rinkari is

A daily cryptic puzzle website. Each day's puzzle is 4 or 5 cryptic
crossword clues whose answers are all connected by one hidden **Link**,
which the solver must also guess. Two link mechanics exist:

- **compound** — the Link combines with every answer to form a real word
  (CAMP/SURE/SPIT/CEASE/CROSS + FIRE). The original house style, 5 clues.
- **category** — the answers are simply members of the category the Link
  names (COT, SEC, SIN, TAN → TRIG). Most of the current queue is this
  type, 4 clues each (see content provenance below).

Scoring: 3 pts/clue (each hint used −1, floor 0), Link worth 5 (wrong
guesses −1). Site has: daily puzzle, archive (past puzzles with Reveal
buttons), solutions (gated until the day after), local-storage stats and
streaks, share button, training puzzle, dark mode, PWA install, AdSense
placeholder slots, privacy page.

## 2. Repo map

```
rinkari/                 The live site. index.html is ~everything; sw.js
                         (service worker), manifest.webmanifest, logo, ads.txt.
rinkari-pipeline/        Puzzle production tooling (Python).
  CLAUDE.md              Agent instructions for puzzle drafting. Read it.
  README.md              Human workflow docs (kept current).
  data/                  compounds.txt, categories.json, indicators.json
  prompts/clue-style-guide.md   REQUIRED reading before drafting clues.
  puzzles/YYYY-MM-DD.json       Source of truth: one puzzle per day.
  puzzles/_drafts_unreviewed/   5 drafted-but-never-reviewed puzzles (see issues).
  scripts/
    mine_links.py        Finds Link candidates from data files.
    lint_clues.py        Fairness linter. Exit 1 on ERROR. THE gatekeeper.
    publish_to_sanity.py THE publish step: lint → createOrReplace into Sanity.
    build_puzzles.py     Legacy local export (per-day JSON + manifest to a
                         folder). Site no longer reads this. Kept as backup.
    import_creator_app.py  One-shot bulk importer used to build the current
                         600-puzzle queue from puzzle-creator-app's database.
  .env                   GITIGNORED. Sanity write credentials (see §6).
sanity-studio/           Sanity Studio (CMS admin UI). npm run dev → :3333.
  schemaTypes/puzzle.ts  The document schema (puzzle/puzzleClue/puzzlePart).
puzzle-creator-app/      GITIGNORED, LOCAL-ONLY. Node app + database of 656
                         candidate puzzles built from NYT Connections answers
                         + ~10k VERBATIM Times/FT cryptic clues (copyrighted —
                         reason it's ignored; do not commit or publish it).
.github/workflows/deploy-pages.yml   Pages deploy (currently blocked, see §8.1).
.claude/launch.json      Preview server configs: "rinkari-site" (py http.server
                         :8080 serving rinkari/) and "sanity-studio" (:3333).
```

## 3. Current architecture (Sanity CMS — third iteration)

The project went through three storage architectures in one day; know the
history so you don't resurrect a dead one:

1. **Baked-in** (original): all puzzles injected into `index.html` between
   `__PUZZLES_START__/__PUZZLES_END__` markers. Dead — markers gone.
2. **Static per-day JSON**: site fetched `puzzles/manifest.json` +
   `puzzles/<date>.json`. Dead — `rinkari/puzzles/` deleted;
   `build_puzzles.py --out` still emits this format as an offline backup.
3. **Sanity CMS** (CURRENT): puzzles are documents in a hosted Sanity
   dataset. The site queries Sanity's public read API directly at runtime.

How the site loads data (all in `rinkari/index.html`):
- `sanityQuery(groq, params)` → GET
  `https://uhde7616.api.sanity.io/v2024-01-01/data/query/production?query=...`
  (no auth needed; dataset is public-read).
- Boot: fetches `*[_type=="puzzle"]{number,date} | order(date asc)` — the
  "manifest". Deliberately number+date only so future answers never reach
  visitors' browsers early.
- "Today" = latest date ≤ today **in Europe/London time** (`londonDateKey()`
  et al. — every date decision goes through these; handles GMT/BST).
- Full puzzle fetched per-date on demand (`fetchPuzzle`), normalized from
  Sanity's `{parts:[{text,role}]}` shape back to the site's `[text,role]`
  arrays by `normalizePuzzle()`.
- Gaps are safe: site holds the latest released puzzle.
- Sanity doc `_id` is deterministic: `puzzle-<date>`. `publish_to_sanity.py`
  uses `createOrReplace`, so republishing is idempotent; pipeline JSON wins
  over any Studio-side edit for the same date.
- The training puzzle (WORK) is still hardcoded in index.html — intentional.
- Service worker (`sw.js`, cache `rinkari-v6`): cache-first for the
  same-origin shell, cross-origin (Sanity) requests are NEVER cached or
  intercepted-with-fallback. Important bug fixed there: the offline fallback
  must only return cached index.html for SAME-origin failures, otherwise a
  failed Sanity call silently returns HTML instead of JSON.

## 4. Content state (what's in the database)

600 puzzles in Sanity, numbers 1–600, consecutive dates
**2026-07-01 → 2028-02-20**, no gaps. Provenance in three tiers:

| Nos. | Dates | Source | Quality |
|---|---|---|---|
| 1–4 | 07-01..07-04 | Hand-drafted compound puzzles (FIRE, LIGHT, SHIP, BOARD), 5 clues each | Fully reasoned clues + parses. Best quality. |
| 5 | 07-05 | TRIG (category, 4 clues) — hand-picked verbatim Times clues from puzzle-creator-app | Real published clues; parses hand-verified. |
| 6–600 | 07-06..2028-02-20 | Bulk import of 595 puzzles via `import_creator_app.py` from puzzle-creator-app's database (NYT-Connections-derived groups + verbatim Times/FT clues), 4 clues each, all `link_type: category` | See quality caveat below — **the biggest content risk in the project**. |

Bulk-import device classification was **mechanical, not real cryptic
analysis**. Final mix across the 2,380 imported clues: Charade 1,810
(the honest catch-all when no device could be verified), Double definition
487 (verified — both halves provably definitions), Hidden 79 / Reversal 2 /
Anagram 2 (only when structurally provable + indicator present). Generic
parse text on the Charade ones. A filter rejects clues whose definition is
literally the category name (would spoil the Link). 60 source puzzles were
skipped ("no valid clue for a member"), 1 as a TRIG duplicate.

Everything lints clean: **0 errors**, 31 advisory WARNs (26× ">2 double
definitions", 5× ">1 hidden", 1 pre-existing SPIT synonym-reversal note).

## 5. Workflows

Prereqs on this machine: Python via `py` launcher (NOT `python3`/`python` —
they're broken Store aliases), Node 24, `gh` CLI at
`C:\Program Files\GitHub CLI\` (add to PATH in Git Bash:
`export PATH="/c/Program Files/GitHub CLI:$PATH"`), authed as `bennipper`.
Sanity CLI login done at user level.

**Publish/edit puzzles (the normal loop):**
```bash
cd rinkari-pipeline
py scripts/lint_clues.py puzzles/*.json     # must be 0 errors
py scripts/publish_to_sanity.py             # all; or --only YYYY-MM-DD; --dry-run
```

**Edit by hand in the CMS UI:** `cd sanity-studio && npm run dev` →
http://localhost:3333 (log in with the user's Sanity account). Remember:
pipeline JSON is source of truth — republish overwrites Studio edits for
that date.

**Draft new puzzles:** follow `rinkari-pipeline/CLAUDE.md` (mine links →
draft per the style guide → lint → review sheet → publish).

**Run the site locally:** preview server config "rinkari-site" (or
`py -m http.server 8080 --directory rinkari`). NOTE: clear service workers
between tests — a stale SW serving old index.html caused two separate
debugging wild-goose chases this session.

## 6. External services & credentials

| Thing | Value / location |
|---|---|
| GitHub repo | `bennipper/rinkari` (public), default branch `main` |
| GitHub auth | `gh` CLI, account `bennipper` (keyring) |
| git identity | bennipper / bennipper@live.com (global) |
| Sanity org | "Rinkari" (id `odfGIBP8q`), created via web dashboard |
| Sanity project | **uhde7616**, dataset **production** (public-read) |
| Sanity write token | `rinkari-pipeline/.env` (gitignored): `SANITY_PROJECT_ID`, `SANITY_DATASET`, `SANITY_WRITE_TOKEN` (editor role, label "Rinkari pipeline publish"). Revoke/rotate: `npx sanity tokens list/delete` from sanity-studio/, or manage.sanity.io. |
| Sanity Studio hosting | NOT deployed — local dev only so far |

Never commit `.env`, never print the token, never commit
`puzzle-creator-app/`. `.gitignore` covers all of these — verified clean at
last push (`git ls-files` shows no secrets).

## 7. Decision log (why things are the way they are)

- **Verbatim Times/FT clues on the live site**: the user was explicitly
  warned this is republishing copyrighted clue text and **chose to accept
  the risk** (their call, on record). Mitigations taken: source attributions
  stripped from public-facing text at user request; raw database gitignored.
  Don't expand the exposure without asking.
- **4-clue puzzles allowed**: user chose to change the schema (linter now
  accepts 4 or 5) rather than pad imported groups to 5.
- **Category-name-reuse allowed** in the queue (e.g. several different DOG
  puzzles with different members) — only identical link+member sets dedupe.
- **Sanity over alternatives**: user explicitly wanted a CMS; Sanity chosen
  (free tier, structured nested docs, hosted, no server to run).
- **Old GitHub repo content force-overwritten**: `bennipper/rinkari` had a
  throwaway manual upload; user approved the overwrite.
- **Unreviewed drafts kept**: 5 compound puzzles (BACK, LINE, EYE, WORK,
  GEMSTONES) in `puzzles/_drafts_unreviewed/` — drafted, never ear-tested,
  never published. Their old date slots are now taken; revival needs
  renumber/redate.

## 8. ⚠️ UNRESOLVED ISSUES — read before doing anything

Ordered by severity.

### 8.1 The site is NOT actually deployed anywhere (blocker)
GitHub Actions is blocked account-wide: *"The job was not started because
your account is locked due to a billing issue."* This is a pre-existing
problem on the user's GitHub account (github.com/settings/billing), NOT
caused by this project — everything used here (public repo, Pages, Actions
on public repos) is free. Current state:
- Pages is configured with `build_type=workflow`; the deploy workflow
  (`.github/workflows/deploy-pages.yml`, deploys the `rinkari/` folder)
  fails instantly at job start.
- Whatever is currently at https://bennipper.github.io/rinkari/ is a stale
  legacy build of the repo root from before the switch — wrong and pre-CMS.
- Options: (a) user fixes billing, then `gh workflow run deploy-pages.yml
  --repo bennipper/rinkari --ref main`; (b) fall back to legacy Pages
  (move/copy site into `/docs`, set Pages source back to branch — no Actions
  needed, works despite the lock); (c) host elsewhere (Netlify Drop etc.).

### 8.2 Bulk-imported clue quality (biggest content risk)
1,810 of 2,380 imported clues are labelled **Charade** as a catch-all. This
matters at the UI level: hint 2 tells the solver "Charade — signal
highlighted" and highlights the entire non-definition text as the
indicator, which will be **wrong** whenever the real device is a container/
deletion/homophone/etc. Parses on those clues are generic ("The definition
is 'X'; the rest builds the answer as wordplay") rather than real
explanations. Hint 1 (definition highlight) IS reliable. None of the 595
imported puzzles has been human ear-tested. If puzzle quality complaints
come in, this is why. Ideas: a review pass over near-term dates; use the
site's per-clue "Was this clue fair?" votes (currently localStorage-only,
never leaves the device — see TODO in `recordFair()`); or reclassify with
real cryptic analysis in batches.

### 8.3 Copyright exposure (accepted, but standing)
Every live clue from No. 5 onward is verbatim from Times/FT crosswords.
User's accepted risk (see §7) — but if a takedown ever arrives, the fix is
to draft replacement clues via the pipeline (that's exactly what it's for).

### 8.4 Future answers are publicly queryable
The Sanity dataset is public-read and contains all 600 puzzles including
future dates. The site never *surfaces* tomorrow early, but anyone who
crafts a GROQ query can read future answers. Accepted residual risk
(documented in pipeline README). Closing it would need a proxy/backend or
Sanity-side access control.

### 8.5 Service-worker staleness trap (operational gotcha)
`sw.js` precaches `index.html` cache-first under cache name `rinkari-v6`.
**Any future edit to index.html must bump the CACHE version string in
sw.js**, or returning visitors keep the old page indefinitely. This bit us
twice during development. When testing locally, unregister SWs + clear
caches between runs.

### 8.6 Final in-browser verification of the Sanity site incomplete
The preview browser sandbox started hard-failing all requests to
`uhde7616.api.sanity.io` (ERR_FAILED) after many repeated test hits, while
the exact same URLs returned 200 via curl throughout, and an earlier
in-browser run had fully worked (600-entry manifest, TRIG rendered, archive
fine). Concluded sandbox egress throttling, not a code bug — but the very
last state of index.html+sw.js was verified by curl/code-reading only.
**First thing after hosting is sorted: load the real site once and play a
puzzle through.**

### 8.7 Possible CORS follow-up when the real domain goes live
Public-dataset queries worked from `localhost:8080` without any CORS
config. If the production domain gets CORS errors against the Sanity API,
add the origin at manage.sanity.io → project → API → CORS origins (no
credentials needed).

### 8.8 Stale copy in the site
- The boot-failure error message still says "puzzles/manifest.json or
  today's puzzle file may not be uploaded yet" — pre-CMS wording, now
  misleading. (Search `boot()` in index.html.)
- Header tagline and how-to modal say **"Five cryptic clues"** but 596 of
  600 puzzles have four. The in-game headings/scorebar are already dynamic;
  the marketing copy isn't.

### 8.9 Smaller content/tooling loose ends
- 60 source puzzles skipped by the importer ("no valid clue for a member")
  — recoverable with smarter clue-building heuristics in
  `import_creator_app.py` if more queue depth is ever needed (source DB has
  them under `puzzle-creator-app/puzzle_matches_final.json`).
- 31 lint WARNs outstanding (advisory): device-mix warnings on imported
  puzzles; the SPIT synonym-reversal note on puzzle 1 is fine as-is.
- `_drafts_unreviewed/` puzzles unused (see §7).
- Sanity Studio is local-only; `npx sanity deploy` from `sanity-studio/`
  would give the user a hosted admin URL — probably worth doing so they can
  edit puzzles without running npm locally.
- `recordFair()` feedback votes still localStorage-only (TODO in code:
  POST somewhere so fairness data accumulates).
- Ads are placeholder divs; AdSense activation steps are commented in
  index.html `<head>`.

### 8.10 Windows environment quirks (will save you an hour)
- Use `py`, not `python3`/`python` (broken Microsoft Store aliases).
- In PowerShell, `npx` fails under execution policy — use `npx.cmd`.
  The Bash tool (Git Bash) doesn't have this problem.
- `sanity init` silently no-ops with a RELATIVE `--output-path`; absolute
  Windows path worked.
- Passing 600 file paths as subprocess args exceeds Windows' command-line
  length limit — that's why `build_puzzles.py`/`publish_to_sanity.py`
  import `lint_clues` as a module instead of shelling out. Keep doing that.
- Console output of UTF-8 (’, ·, —) often *displays* as mojibake in this
  terminal while the underlying bytes/data are fine — verify encoding by
  codepoint (`[hex(ord(c)) for c in s]`), not by eyeballing echo output.

## 9. Suggested first moves for the next agent

1. Ask the user about GitHub billing (§8.1) and get the site actually live;
   then do the §8.6 end-to-end check on the real URL.
2. Fix the two stale-copy items (§8.8) — five-minute wins; remember the SW
   cache-bump rule (§8.5).
3. Propose a quality plan for §8.2 (even just hand-reviewing the next 30
   days of puzzles buys a month of runway).
4. Consider `npx sanity deploy` so the user can edit content from anywhere
   (that was the point of wanting a CMS).
