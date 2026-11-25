# CreeperMinion Statistics — installation and editing notes

Built from the **actual uploaded** `CreeperMinionPhantomForcesStats.xlsx` and the latest publicly committed repository files checked on November 25, 2026. **No upload to GitHub has happened.**

## What is included

### NEW — upload these files into your repository at these exact paths

- `statistics/index.html` — new statistics page
- `statistics/statistics.css` — page styling, purple links, green/red heatmap
- `statistics/statistics.js` — table generation, sorting, filters, notes dialog
- `content/weapon-stats.json` — master data from the 3 original Excel rows
- `armory-database.js` — optional bridge: adds a stats link to armory popups when a weapon exists in the master data
- `scripts/update_weapon_stats.py` — optional CSV importer for your future Google Sheet

### EXISTING — make only the following **small edits**, not whole-file replacements

**A. `sidebar.js` (ONE LINE)**

Find EXACTLY:
```javascript
{ label: 'Statistics', soon: true },
```
Replace it with:
```javascript
{ label: 'Statistics', href: '/statistics/' },
```

**B. Root `index.html` (ONE ELEMENT)**

Find the current HTML block beginning with:
```html
<div class="home-feature-link home-not-ready" aria-label="Statistics library coming soon">
```
and ending at its matching `</div>` (the Statistics tile only).

Replace just that block with:
```html
<a class="home-feature-link" href="/statistics/">
  <span class="home-tile-kicker">EXPLORE</span><strong>STATISTICS</strong>
  <span class="home-tile-description">Browse, sort and inspect weapon statistics.</span><span class="home-tile-arrow">↗</span>
</a>
```

**C. `armory/index.html` (ONE LINE)**

Find:
```html
<script src="sidebar.js" defer></script>
```
Add directly beneath it:
```html
<script src="armory-database.js" defer></script>
```

> `REFERENCE_ONLY/` contains complete updated versions of those three existing files as a fallback. Do **not** upload the `REFERENCE_ONLY` folder or overwrite your personalized files wholesale.

## Starting data

The workbook has **3 weapons: C25, M4A1, and AK-12**, with **14 columns**. All 14 headings are clickable sort controls (the Thumbnail column sorts on its source value if present). No source values were invented or normalized into rankings.

- The original `Thumbnail` column is blank in the file. Until you populate it, website code will reuse matching armory images (C25/M4A1) when available, or show a neutral placeholder.
- The uploaded Excel file has no `Notes` column. In your Google Sheet, add an **O** column headed exactly `Notes`; put text on the corresponding weapon row. The notes dialog uses this field and preserves line breaks. Until populated, it reads "No notes have been added…".
- `Headshot Mult` such as `1.4x` and `Reload Speed` such as `1.93s` display as written; sorting uses numeric values.
- Heatmap defaults to **same Slot + Class** rather than comparing snipers and pistols. It uses all weapons in that class, irrespective of the current search filter. Metrics with fewer than two peers or no variance remain neutral. High generally means favorable, EXCEPT lower Reload Speed is better. This is not an overall weapon-value ranking.
- The new `statistics/` page supports direct notes links like `https://creeperminionyt.github.io/statistics/?weapon=c25`.
- The armory now consults the canonical JSON to link its C25/M4A1 popups to the corresponding statistics record. AK47 and Automag III will get automatic links after you add those weapons to the master sheet.

## How Google Sheets will sync when you're ready

1. Import your `.xlsx` into Google Sheets (or copy this data into your intended master sheet).
2. Add an **O: Notes** column. Optionally add **P: Weapon ID** for stable identifiers even if you rename a weapon.
3. In Google Sheets, use **File → Share → Publish to web**, and choose **only your public weapon-data tab**, in **CSV** format. Publishing makes the selected data public.
4. Save the published CSV URL. You can then import it using:

```bash
python scripts/update_weapon_stats.py --url "PASTE_PUBLISHED_CSV_URL" --sheet-link "YOUR_READ_ONLY_SHEET_URL"
```

5. Commit the changed `content/weapon-stats.json`. In a future iteration, we can add a scheduled GitHub Action to do step 4 automatically once you supply the real URL.

For an exported local CSV instead:

```bash
python scripts/update_weapon_stats.py --csv exported.csv
```

The importer requires the same 14 column headings, trims whitespace (your original header ` Range` works), supports extra `Notes` and `Weapon ID` columns, rejects duplicate identifiers, and never guesses missing statistics. Keep the Sheets tab as your single editable source; generated JSON is the deployed snapshot.

## Quick styling adjustments

Edit `statistics/statistics.css` at the top:

- `--stat-purple`: weapon links and branding accents
- `--stat-row-height`: table compactness
- `--stat-bg`, `--stat-surface`, `--stat-border`: palette
- `--stat-density`: base text size

All 14 table columns are generated from `content/weapon-stats.json`. You don't need to manually write table HTML.

## GitHub Actions publishing

Since you've switched to Pages via GitHub Actions, commit the changed/new files normally and use your existing **Publish CreeperMinion site** workflow if a normal push doesn't deploy immediately. There is no change to your existing Actions settings or video updater in this release.
