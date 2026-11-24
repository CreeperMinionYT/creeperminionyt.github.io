#!/usr/bin/env python3
"""Refresh content/latest-videos.json using the CreeperMinion YouTube public feed.

Without an API key:
  - main card tracks the channel's newest published upload (video OR Short)
  - Shorts remain at the manually curated defaults in the JSON file
With YOUTUBE_API_KEY:
  - use the official YouTube videos.list endpoint for durations
  - main card tracks the most recent video > 3 minutes
  - two Shorts cards track the most recent videos <= 3 minutes

Important: YouTube's public Data API does NOT expose an authoritative "isShort" flag.
The 3-minute threshold is a heuristic; if a normal short-duration video is uploaded,
curate the JSON directly or change classification rules in this script.

This script intentionally makes no changes if the feed cannot be fetched.
No external Python packages are required.
"""
import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'content' / 'latest-videos.json'
CHANNEL_ID = 'UCmqJ0S7ETaFqZtKOoJoD1yw'
FEED = f'https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}'
NS = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')


def get(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; CreeperMinionSiteFeed/1.0)', 'Accept': 'application/xml,application/json'})
    with urlopen(req, timeout=25) as response:
        return response.read()


def latest_feed_items():
    tree = ET.fromstring(get(FEED))
    entries = []
    for node in tree.findall('atom:entry', NS):
        video_id = node.findtext('yt:videoId', '', NS)
        title = node.findtext('atom:title', '', NS).strip()
        published = node.findtext('atom:published', '', NS)
        if VIDEO_ID.fullmatch(video_id) and title:
            entries.append({'id': video_id, 'title': title, 'published': published})
    entries.sort(key=lambda e: e['published'], reverse=True)
    if not entries:
        raise ValueError('YouTube feed returned no usable public uploads')
    return entries


def duration_seconds(iso):
    # A basic YouTube ISO 8601 duration parser (PT#H#M#S).
    match = re.fullmatch(r'P(?:\d+D)?T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso or '')
    if not match:
        return None
    hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def classify_with_api(entries, api_key):
    params = urlencode({'part': 'contentDetails', 'id': ','.join(e['id'] for e in entries), 'key': api_key})
    response = json.loads(get('https://www.googleapis.com/youtube/v3/videos?' + params))
    if 'error' in response:
        raise ValueError(f"YouTube API error: {response['error'].get('message', 'unknown')}")
    durations = {item['id']: duration_seconds(item.get('contentDetails', {}).get('duration')) for item in response.get('items', [])}
    long_videos = [e for e in entries if durations.get(e['id']) is not None and durations[e['id']] > 180]
    short_videos = [e for e in entries if durations.get(e['id']) is not None and durations[e['id']] <= 180]
    return long_videos, short_videos


def compact(entry, video_type=None):
    result = {'id': entry['id'], 'title': entry['title']}
    if video_type:
        result['type'] = video_type
    return result


def main():
    previous = json.loads(OUT.read_text(encoding='utf-8'))
    entries = latest_feed_items()
    api_key = os.environ.get('YOUTUBE_API_KEY', '').strip()
    updated = dict(previous)
    updated['channel_id'] = CHANNEL_ID
    if api_key:
        long_videos, short_videos = classify_with_api(entries, api_key)
        if long_videos:
            updated['featured'] = compact(long_videos[0], 'video')
        if short_videos:
            preserved = [s for s in previous.get('shorts', []) if s.get('id') not in {x['id'] for x in short_videos}]
            updated['shorts'] = [compact(s) for s in short_videos[:2]]
            updated['shorts'] = (updated['shorts'] + preserved)[:2]
        updated['source'] = 'youtube-feed+api-duration-heuristic'
    else:
        updated['featured'] = compact(entries[0], 'upload')
        updated['source'] = 'youtube-public-feed; shorts-pinned'

    # Don't commit or redeploy when nothing changed (including the timestamp).
    comparable = ('featured', 'shorts', 'source', 'channel_id')
    if all(updated.get(k) == previous.get(k) for k in comparable):
        print('Video data unchanged; no write needed')
        return
    updated['updated_utc'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    OUT.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Refreshed homepage feed: {updated['featured']['title']}")


if __name__ == '__main__':
    main()
