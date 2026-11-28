#!/usr/bin/env python3
"""Bulk-import authorized images by weapon name into CreeperMinion's local thumbnail folders.

Examples (run from repo root):
  python scripts/import_thumbnails.py my_approved_images.zip --kind wiki
  python scripts/import_thumbnails.py "my high quality AK-12.png" --kind custom --weapon ak12
  python scripts/import_thumbnails.py my_own_images/ --kind custom

The source must contain images you have rights to reuse. This script deliberately
DOES NOT crawl or scrape Fandom; its Terms prohibit automated scraping without
permission. User's own images override wiki images at import time via the existing
Google-Sheets-to-JSON updater.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'content' / 'weapon-stats.json'
IMAGE_EXTS = {'.webp', '.png', '.jpg', '.jpeg'}
MAX_BYTES = 12 * 1024 * 1024


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', text.lower())


def valid_image(data: bytes, ext: str) -> bool:
    if ext == '.png':
        return data.startswith(b'\x89PNG\r\n\x1a\n')
    if ext in ('.jpg', '.jpeg'):
        return data.startswith(b'\xff\xd8\xff')
    if ext == '.webp':
        return data.startswith(b'RIFF') and data[8:12] == b'WEBP'
    return False


def inputs(path: Path):
    if path.is_dir():
        for file in sorted(path.rglob('*')):
            if file.is_file() and file.suffix.lower() in IMAGE_EXTS:
                if file.stat().st_size > MAX_BYTES:
                    yield (file.name, None, 'too large (>12 MB)')
                else:
                    yield (file.name, file.read_bytes(), '')
    elif path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as archive:
            for member in sorted(archive.infolist(), key=lambda x: x.filename):
                if member.is_dir() or Path(member.filename).suffix.lower() not in IMAGE_EXTS:
                    continue
                if member.file_size > MAX_BYTES:
                    yield (Path(member.filename).name, None, 'too large (>12 MB)')
                    continue
                with archive.open(member) as stream:
                    data = stream.read(MAX_BYTES + 1)
                if len(data) > MAX_BYTES:
                    yield (Path(member.filename).name, None, 'too large (>12 MB)')
                    continue
                yield (Path(member.filename).name, data, '')
    elif path.is_file() and path.suffix.lower() in IMAGE_EXTS:
        if path.stat().st_size > MAX_BYTES:
            yield (path.name, None, 'too large (>12 MB)')
        else:
            yield (path.name, path.read_bytes(), '')
    else:
        raise ValueError('Pass an image file, folder containing images, or ZIP of images.')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', type=Path, help='Folder, .zip, or individual image with reuse rights')
    parser.add_argument('--kind', choices=('wiki', 'custom'), default='wiki',
                        help='wiki = collection, custom = your higher-quality replacements')
    parser.add_argument('--weapon', help='Assign a single image to this weapon ID/name (e.g. ak12)')
    parser.add_argument('--replace', action='store_true',
                        help='Replace existing wiki images. Custom files replace automatically.')
    args = parser.parse_args()

    if not DB.is_file():
        parser.error(f'First generate the stats database: {DB}')
    data = json.loads(DB.read_text(encoding='utf-8'))
    weapons = {w['id']: w['weapon'] for w in data['weapons']}
    candidates = {slug(w['weapon']): w['id'] for w in data['weapons']}
    candidates.update({slug(weapon_id): weapon_id for weapon_id in weapons})
    if args.weapon and slug(args.weapon) not in candidates:
        parser.error(f'Unknown weapon: {args.weapon!r}')
    if args.weapon and not args.source.is_file():
        parser.error('--weapon is for importing one image at a time')

    destination = ROOT / 'assets' / 'thumbnails' / args.kind
    destination.mkdir(parents=True, exist_ok=True)
    imported = skipped = 0
    problems = []
    seen = set()
    for name, raw, reason in inputs(args.source):
        ext = Path(name).suffix.lower()
        ident = candidates.get(slug(args.weapon or Path(name).stem))
        if not ident:
            problems.append(f'{name}: no exact weapon match (rename to an ID such as ak12.png)')
            continue
        if ident in seen:
            problems.append(f'{name}: second image for {weapons[ident]}, skipped')
            continue
        if raw is None or not valid_image(raw, ext):
            problems.append(f'{name}: {reason or "invalid image content for file extension"}')
            continue
        seen.add(ident)
        existing = [destination / f'{ident}{suffix}' for suffix in sorted(IMAGE_EXTS)
                    if (destination / f'{ident}{suffix}').is_file()]
        if existing and args.kind == 'wiki' and not args.replace:
            skipped += 1
            continue
        target = destination / f'{ident}{ext}'
        temp = target.with_name(f'{target.name}.tmp')
        temp.write_bytes(raw)
        temp.replace(target)
        # No stale extension can silently override a new custom upload.
        for old in existing:
            if old != target:
                old.unlink()
        print(f'  {weapons[ident]} -> {target.relative_to(ROOT).as_posix()}')
        imported += 1
    print(f'Imported {imported}; preserved {skipped} existing wiki images; unmatched/rejected {len(problems)}.')
    for problem in problems:
        print('  REVIEW:', problem)
    print('Commit assets/thumbnails/ to GitHub, then run Actions > Sync weapon statistics.')
    if problems:
        print('Unmatched images were NOT assigned to the wrong weapon. Fix filenames and rerun.')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as error:
        print(f'Import failed: {error}', file=sys.stderr)
        sys.exit(1)
