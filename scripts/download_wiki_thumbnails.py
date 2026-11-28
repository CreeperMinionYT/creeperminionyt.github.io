#!/usr/bin/env python3
"""One-run Phantom Forces thumbnail batch importer.

Reads every weapon from content/weapon-stats.json and looks up its main infobox
art via Fandom's MediaWiki API. Does not scrape search-engine images, bypass
access controls, or overwrite your own images.

Usage (from repo root):
  pip install Pillow
  python scripts/download_wiki_thumbnails.py
  python scripts/download_wiki_thumbnails.py --limit 5   # sample
  python scripts/download_wiki_thumbnails.py --replace   # refresh wiki art

Fandom's Terms require permission for automated access. Use only if authorized,
and review image licenses/attributions before republication. If the API blocks
access, the script reports that and stops rather than trying to evade it.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

try:
    from PIL import Image, ImageOps, UnidentifiedImageError
except ImportError:
    sys.exit('Requires Pillow. Install it with: python -m pip install Pillow')

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / 'content' / 'weapon-stats.json'
WIKI_DIR = ROOT / 'assets' / 'thumbnails' / 'wiki'
CUSTOM_DIR = ROOT / 'assets' / 'thumbnails' / 'custom'
REPORT = ROOT / 'assets' / 'thumbnails' / 'wiki-import-report.csv'
API = 'https://roblox-phantom-forces.fandom.com/api.php'
WIKI = 'https://roblox-phantom-forces.fandom.com/wiki/'
USER_AGENT = 'CreeperMinionWikiThumbnailImporter/1.0 (+https://github.com/CreeperMinionYT/creeperminionyt.github.io)'
IMAGE_EXTS = ('.webp', '.png', '.jpg', '.jpeg')
MAX_IMAGE_BYTES = 12_000_000
# Edit this mapping ONLY for wiki article titles that differ from in-game names.
PAGE_ALIASES = {
    'BFG-50': 'BFG 50',
    'BFG 50': 'BFG 50',
}


class AccessBlocked(RuntimeError):
    pass


class WikiAPIError(RuntimeError):
    pass


def normalize(text):
    return re.sub(r'[^a-z0-9]+', '', (text or '').lower())


def fetch(url, *, max_bytes=3_000_000):
    req = Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/json, text/html, image/avif, image/webp, image/png, image/jpeg, */*',
    })
    try:
        with urlopen(req, timeout=30) as response:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise WikiAPIError('Response exceeds size limit')
            return data
    except HTTPError as err:
        if err.code in (401, 403, 429, 451):
            raise AccessBlocked(f'The wiki/image host refused automated access (HTTP {err.code}). Do not bypass its restrictions.') from err
        raise WikiAPIError(f'HTTP {err.code}: {url.split("?")[0]}') from err
    except URLError as err:
        raise WikiAPIError(f'Network error: {err.reason}') from err


def call_api(params):
    query = {'format': 'json', 'formatversion': 2, **params}
    payload = fetch(API + '?' + urlencode(query))
    try:
        data = json.loads(payload)
    except ValueError as err:
        raise WikiAPIError('Wiki returned non-JSON data; MediaWiki API might be unavailable') from err
    if 'error' in data:
        raise WikiAPIError(str(data['error'].get('info', data['error'])))
    return data


class InfoboxParser(HTMLParser):
    """Prefer a weapon's main portable-infobox image over article screenshots."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.possible = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get('class', '').split())
        parent = self.stack[-1] if self.stack else False
        within_infobox = parent or 'portable-infobox' in classes or 'pi-image' in classes
        if tag not in ('img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr'):
            self.stack.append(within_infobox)
        if tag == 'img' and within_infobox:
            src = attrs.get('data-src') or attrs.get('src') or attrs.get('data-image-src')
            if src and not src.startswith('data:'):
                score = 2 if 'pi-image-thumbnail' in classes else 1
                self.possible.append((score, src))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag not in ('img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr') and self.stack:
            self.stack.pop()


def safe_source(url):
    if url.startswith('//'):
        url = 'https:' + url
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        return None
    # The image file CDN domains used for Fandom images.
    domain = parsed.hostname or ''
    approved = domain.endswith('.wikia.nocookie.net') or domain in {
        'static.wikia.nocookie.net', 'vignette.wikia.nocookie.net',
        'images.wikia.com', 'roblox-phantom-forces.fandom.com',
    }
    if not approved:
        return None
    bad = ('no_image', 'noimage', 'placeholder', 'default-image', 'wiki.png', 'site-logo')
    if any(s in url.lower() for s in bad):
        return None
    return url


def get_picture(title):
    """Ask the wiki API for the article's infobox/main image; no browser scraping."""
    try:
        data = call_api({'action': 'parse', 'page': title, 'prop': 'text', 'disableeditsection': 1})
        parsed = data.get('parse') or {}
        markup = parsed.get('text') or ''
        if isinstance(markup, dict):
            markup = markup.get('*', '')
        image_parser = InfoboxParser()
        image_parser.feed(markup)
        for _score, url in sorted(image_parser.possible, key=lambda x: -x[0]):
            img = safe_source(url)
            if img:
                return img, parsed.get('title', title)
    except WikiAPIError:
        pass
    # Some Fandom pages return only page-image metadata instead of a parsed infobox.
    data = call_api({'action': 'query', 'titles': title, 'redirects': 1,
                     'prop': 'pageimages', 'piprop': 'thumbnail|original', 'pithumbsize': 560})
    pages = (data.get('query') or {}).get('pages') or []
    for page in pages:
        if page.get('missing'):
            continue
        for field in ('thumbnail', 'original'):
            img = safe_source((page.get(field) or {}).get('source') or '')
            if img:
                return img, page.get('title', title)
    return None, title


def search_alias(title):
    """Only accept a search result if its normalized name exactly matches."""
    data = call_api({'action': 'query', 'list': 'search', 'srsearch': title, 'srlimit': 8, 'srnamespace': 0})
    hits = (data.get('query') or {}).get('search') or []
    key = normalize(title)
    for hit in hits:
        found = hit.get('title', '')
        if normalize(found) == key:
            return found
    return None


def to_webp(raw):
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            if img.width < 110 or img.height < 28:
                raise ValueError('Image too small; likely an icon/placeholder')
            # Normalize sizes while retaining any alpha channel and aspect ratio.
            img = img.convert('RGBA')
            img.thumbnail((560, 260), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, 'WEBP', quality=86, method=5)
            return buffer.getvalue()
    except (UnidentifiedImageError, OSError) as err:
        raise ValueError(f'Not a usable image: {err}') from err


def existing_custom(ident):
    return any((CUSTOM_DIR / (ident + ext)).is_file() for ext in IMAGE_EXTS)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--limit', type=int, help='Only process the first N weapons (for test runs)')
    parser.add_argument('--replace', action='store_true', help='Replace existing wiki thumbnails (never custom)')
    parser.add_argument('--delay', type=float, default=1.5, help='Seconds between API requests (default: 1.5)')
    args = parser.parse_args()
    if args.delay < 0.75:
        parser.error('--delay must be at least 0.75 seconds')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    if not DATABASE.is_file():
        parser.error(f'Missing {DATABASE}; run the Google Sheets sync first')
    db = json.loads(DATABASE.read_text(encoding='utf-8'))
    weapons = db.get('weapons') or []
    if args.limit:
        weapons = weapons[:args.limit]
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    downloaded = 0
    prev_report = {}
    if REPORT.is_file():
        with REPORT.open(newline='', encoding='utf-8') as file:
            prev_report = {r['id']: r for r in csv.DictReader(file)}
    for i, weapon in enumerate(weapons, 1):
        name = weapon['weapon']
        ident = weapon['id']
        out = WIKI_DIR / (ident + '.webp')
        old = prev_report.get(ident, {})
        if existing_custom(ident):
            rows.append({'id': ident, 'weapon': name, 'status': 'custom override',
                         'wiki_page': old.get('wiki_page', ''), 'image_url': old.get('image_url', '')})
            continue
        if out.exists() and not args.replace:
            rows.append({'id': ident, 'weapon': name, 'status': 'already downloaded',
                         'wiki_page': old.get('wiki_page', ''), 'image_url': old.get('image_url', '')})
            continue
        title = PAGE_ALIASES.get(name, name)
        print(f'[{i}/{len(weapons)}] {name}: ', end='', flush=True)
        source = None
        found_title = title
        try:
            source, found_title = get_picture(title)
            if not source:
                alias = search_alias(title)
                if alias and alias != title:
                    source, found_title = get_picture(alias)
            if not source:
                status = 'no verified main image on wiki'
            else:
                time.sleep(args.delay)
                raw = fetch(source, max_bytes=MAX_IMAGE_BYTES)
                encoded = to_webp(raw)
                temp = out.with_name(out.name + '.tmp')
                temp.write_bytes(encoded)
                temp.replace(out)
                downloaded += 1
                status = 'downloaded'
                print(f'OK ({len(encoded)//1024} KB)', flush=True)
        except AccessBlocked as err:
            print(f'BLOCKED: {err}', file=sys.stderr)
            raise
        except (WikiAPIError, ValueError, OSError) as err:
            status = 'ERROR: ' + str(err)[:130]
        if status != 'downloaded':
            print(status, flush=True)
        page_url = WIKI + found_title.replace(' ', '_') if source else ''
        rows.append({'id': ident, 'weapon': name, 'status': status,
                     'wiki_page': page_url, 'image_url': source or ''})
        time.sleep(args.delay)

    # Preserve prior provenance for weapons excluded by --limit.
    new_ids = {r['id'] for r in rows}
    rows.extend(prev_report[k] for k in prev_report if k not in new_ids)
    with REPORT.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, ['id', 'weapon', 'status', 'wiki_page', 'image_url'])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Finished: {downloaded} new wiki thumbnails, '
          f'{sum(r["status"] == "already downloaded" for r in rows)} already present; '
          f'{sum(r["status"].startswith("ERROR") or r["status"].startswith("no verified") for r in rows)} require review.')
    print(f'Review missing matches and image sources: {REPORT.relative_to(ROOT)}')
    if downloaded == 0 and not any((WIKI_DIR / (w['id'] + '.webp')).exists() for w in weapons):
        raise RuntimeError('No thumbnails found; wiki API may not provide weapon images. Do not publish placeholders.')


if __name__ == '__main__':
    try:
        main()
    except (AccessBlocked, WikiAPIError, RuntimeError, OSError, KeyError, ValueError) as err:
        print(f'Wiki thumbnail import stopped: {err}', file=sys.stderr)
        sys.exit(1)
