# Rinkari — ready to share

Everything in this folder is the whole site. To get a link you can send to
friends, you need to put these files somewhere on the web — a browser can't
run `manifest.webmanifest`/service-worker features from a local file, so
please don't just open `index.html` by double-clicking it. Use one of the
options below instead; both are free and take under two minutes.

## Option A — Netlify Drop (fastest, no account needed)

1. Go to **https://app.netlify.com/drop** in your browser.
2. Drag this whole folder onto the page.
3. Netlify gives you a live URL immediately (something like
   `random-name-123.netlify.app`). That's your link — send it to friends.
4. Optional: sign up (free) afterwards if you want to keep the site, rename
   the URL, or update it later by dragging the folder again.

## Option B — GitHub Pages (if you already use GitHub)

1. Create a new repository, e.g. `rinkari`.
2. Upload all the files in this folder to the repository root.
3. In the repo, go to **Settings → Pages**, set the source to the `main`
   branch and `/ (root)`, and save.
4. GitHub gives you a URL like `yourusername.github.io/rinkari` within a
   minute or two.

## What's in the folder

- `index.html` — the whole site (game, archive, solutions, stats, dark mode).
- `manifest.webmanifest` + `sw.js` — let phones "Add to Home Screen" like an app.
- `rinkari_logo.svg` — the logo, used as the home-screen icon too.
- `ads.txt` — placeholder for later; harmless to deploy as-is now.

## Things to tell your friends before they play

- **Streaks and stats only work on the real deployed link**, not in a
  screenshot or a copy of the file — they're stored per-browser, per-device.
- **The grey dashed boxes are ad placeholders**, not a bug — they mark where
  ads will go once AdSense is approved. They only appear after finishing a
  puzzle, in the archive, and on solution pages.
- Best tested on both a phone and a desktop browser — that's the two
  audiences the layout is built for.
- If dark mode, hints, or the Link don't behave as expected, that's exactly
  the kind of feedback worth sending back.

## After playtesting

Once you've got feedback, come back and we can adjust — new puzzles, tuning
the hint economy, tightening the design in Claude Design, or moving toward
the full date-rotating build.
