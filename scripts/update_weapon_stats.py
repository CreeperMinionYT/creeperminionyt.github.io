#!/usr/bin/env python3
"""CreeperMinion — import a published Google Sheets CSV into the site's canonical JSON.

Usage after publishing just the weapon-data tab of Google Sheets to the web:
    python scripts/update_weapon_stats.py --url "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"

Or import an exported CSV locally:
    python scripts/update_weapon_stats.py --csv exported.csv

All 14 required columns are retained. Optional extra columns: Rating (F,D,C,B,A,S), Notes, Weapon ID.
Never overwrite data with inferred Phantom Forces values.
"""
from __future__ import annotations
import argparse, csv, io, json, re
from pathlib import Path
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'content' / 'weapon-stats.json'
FIELDS = [
    ('Thumbnail', 'thumbnail', 'image', False),
    ('Weapon', 'weapon', 'text', False),
    ('Rating', 'rating', 'tier', False),  # OPTIONAL: subjective F/D/C/B/A/S grade
    ('Unlock Rank', 'unlock_rank', 'number', False),
    ('Slot', 'slot', 'text', False),
    ('Class', 'class', 'text', False),
    ('Max Damage', 'max_damage', 'number', True),
    ('Min Damage', 'min_damage', 'number', True),
    ('Headshot Mult', 'headshot_mult', 'number', True),
    ('Range', 'range', 'number', True),
    ('Fire Rate', 'fire_rate', 'number', True),
    ('Muzzle Velocity', 'muzzle_velocity', 'number', True),
    ('Magazine Size', 'magazine_size', 'number', True),
    ('Reload Speed', 'reload_speed', 'number', True),
    ('Walk Speed', 'walk_speed', 'number', True),
]
# Lower reload times are generally advantageous; rank is acquisition, not performance.
LOWER_BETTER = {'reload_speed'}
OPTIONAL_FIELDS = {'Rating'}  # Keep sync working before the Rating column is added.
HEADER_ALIASES = {'headshot mult': 'Headshot Mult', 'range': 'Range',
                  'thumbnail': 'Thumbnail', 'weapon id': 'Weapon ID'}

def slug(name):
    return re.sub(r'[^a-z0-9]+', '', name.lower())

def read_csv(text):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not reader.fieldnames:
        raise ValueError('No header row found')
    cols = {name.strip().lower(): name for name in reader.fieldnames if name}
    missing = [header for header, _, _, _ in FIELDS if header not in OPTIONAL_FIELDS and header.lower() not in cols]
    if missing:
        raise ValueError('Missing required columns: ' + ', '.join(missing))
    output = []
    seen = set()
    for row in reader:
        name = (row.get(cols['weapon']) or '').strip()
        if not name: continue
        explicit = (row.get(cols.get('weapon id', ''), '') or '').strip() if 'weapon id' in cols else ''
        id_ = slug(explicit or name)
        if id_ in seen: raise ValueError(f'Duplicate weapon ID {id_!r} (row: {name})')
        seen.add(id_)
        item = {'id': id_}
        for header, key, kind, _ in FIELDS:
            source_column = cols.get(header.lower())  # Rating may be absent initially.
            val = (row.get(source_column) or '').strip() if source_column else ''
            if key == 'rating':
                # Grade values use a six-level tier system, not the old 1-3 stars.
                grade = val.upper()
                if grade and grade not in {'F', 'D', 'C', 'B', 'A', 'S'}:
                    raise ValueError(f'Invalid Rating {val!r} for {name}. Use F, D, C, B, A or S (or leave blank).')
                item[key] = grade or None
            elif not val:
                item[key] = None
            elif kind == 'number':
                clean = val.replace(',', '')
                # Preserve exact source display text for suffixes such as "1.4x" / "1.93s".
                if re.fullmatch(r'[-+]?\d+(?:\.\d+)?', clean):
                    f = float(clean)
                    item[key] = int(f) if f.is_integer() else f
                else:
                    item[key] = val
            else: item[key] = val
        item['notes'] = (row.get(cols.get('notes', ''), '') or '').strip() if 'notes' in cols else ''
        output.append(item)
    if not output: raise ValueError('No weapon rows found')
    return output

def main():
    p = argparse.ArgumentParser()
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--url', help='Published public CSV URL from Google Sheets')
    source.add_argument('--csv', help='Path to local CSV export')
    p.add_argument('--sheet-link', help='Optional public view URL of your Google Sheet')
    args = p.parse_args()
    if args.url:
        if not args.url.startswith('https://'):
            p.error('Only HTTPS sources accepted')
        request = Request(args.url, headers={'User-Agent': 'CreeperMinionStatsImporter/1.0'})
        with urlopen(request, timeout=25) as resp:
            csv_text = resp.read().decode('utf-8-sig')
    else: csv_text = Path(args.csv).read_text(encoding='utf-8-sig')
    records = read_csv(csv_text)
    # Reuse the existing public Sheet link unless explicitly overridden.
    previous_link = ''
    if OUTPUT.exists():
        try: previous_link = json.loads(OUTPUT.read_text(encoding='utf-8')).get('sheet_url', '')
        except (OSError, ValueError): pass
    config = {
        'schema_version': 1,
        'description': 'CreeperMinion Phantom Forces — canonical weapon statistics',
        'source': 'Published Google Sheet' if args.url else 'Exported spreadsheet CSV',
        'sheet_url': args.sheet_link or previous_link,
        'columns': [
            {'key': key, 'label': ('Unlock' if key == 'unlock_rank' else 'Tier' if key == 'rating' else header), 'type': kind,
             'heatmap': heatmap, 'better': ('lower' if key in LOWER_BETTER else 'higher')}
            for header, key, kind, heatmap in FIELDS
        ],
        'weapons': records
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(config, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Updated {OUTPUT} with {len(records)} weapons')

if __name__ == '__main__': main()
