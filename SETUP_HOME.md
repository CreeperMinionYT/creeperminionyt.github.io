# CreeperMinion — new homepage + existing armory

## Upload / replacement summary

IMPORTANT: Use the contents of this ZIP at repository ROOT while preserving the folder paths. Do not put the whole ZIP inside a `creeperminion_home_update` folder.

**Replace current root file:**
- `index.html` (the new homepage)
- `sidebar.js` (ONLY route changes: Home `/`, Armory `/armory/`)

**Add these new files:**
- `home.css`
- `home.js`
- `armory/index.html` (your existing room markup with `<base href="/">`)
- `content/latest-videos.json`
- `scripts/update_youtube.py`
- `.github/workflows/refresh-videos.yml`

**DO NOT REPLACE:** `style.css`, `script.js`, `weapons.json`, `sidebar.css`, `assets/`, weapon images, backgrounds, effects, profile image.

## IMPORTANT: your existing sidebar.css needs a one-character fix

Your current committed CSS has a missing `}` after the `background` declaration of `.cm-nav-logo`. Find:

```css
  background: url("assets/resources/ProfilePic2026.png")
              center / contain no-repeat;

.cm-nav-logo:hover {
```

and insert a closing brace, so it becomes:

```css
  background: url("assets/resources/ProfilePic2026.png")
              center / contain no-repeat;
}

.cm-nav-logo:hover {
```

This preserves every personal CSS change and makes the hover/focus styles valid.

## Preserve existing armory deep links

Old links like `https://creeperminionyt.github.io/?weapon=ak47` automatically redirect to `https://creeperminionyt.github.io/armory/?weapon=ak47`. The existing `weapons.json` images and `script.js` fetch still work because `armory/index.html` uses `<base href="/">`.

## Automatic video content

The homepage loads `content/latest-videos.json`, which starts with real already-linked videos as a safe fallback. After the Action runs, it updates from the public YouTube feed for channel `UCmqJ0S7ETaFqZtKOoJoD1yw`.

**Without any API key:** newest *upload* updates automatically, but may be a Short, and the two Short cards remain manually selected in JSON. This is intentional because the public feed does not identify Shorts reliably.

**For better categorization (OPTIONAL):** create a YouTube Data API v3 key in Google Cloud and save it in GitHub repository Settings > Secrets and variables > Actions > New repository secret as `YOUTUBE_API_KEY`. The action then selects the latest upload **over 180 seconds** for the large card and the two latest uploads **180 seconds or less** for the Short cards. That duration threshold is a heuristic, not a guaranteed YouTube Shorts flag. Some rare videos will need manual classification. The API key is never included in site files.

**IMPORTANT DEPLOYMENT SETTING:** The workflow deploys Pages directly so bot commits publish correctly. After uploading it, go to **Settings > Pages > Build and deployment > Source > GitHub Actions**. This replaces the old "Deploy from a branch" mode. GitHub Pages will then deploy on each regular push and on scheduled checks.

**To run immediately:** Repository > Actions > **Publish CreeperMinion site** > Run workflow. If GitHub asks, enable Actions. Give the default `GITHUB_TOKEN` read/write permission under Settings > Actions > General > Workflow permissions if the refresh commit is denied. The workflow also requests `contents: write`, `pages: write` and `id-token: write`.

**To change videos manually:** edit the 11-character `id` and `title` in `content/latest-videos.json`. The automatic workflow will update its chosen sections again on the next successful run, so manual preferences require disabling the workflow or adjusting `scripts/update_youtube.py`.

**To change layout/colors:** edit only `home.css` (see quick controls at its top). Do not copy armory CSS into it.

## Navigation changes if editing existing sidebar.js by hand

Find the `const items = [` block. Change ONLY these two entries:

```js
{ label: 'Home', href: '/' },
{ label: 'Armory', href: '/armory/' },
```

Leave the existing logo, YouTube link, sidebar design and behavior alone.

## Why the entire armory moved

`index.html` at the root is always the main GitHub Pages entry. A new homepage needs that filename; the existing interactive room therefore becomes `armory/index.html`. All existing root CSS, JS and images remain where they were, so you won't have duplicate code or assets.
