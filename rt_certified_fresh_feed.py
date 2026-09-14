#!/usr/bin/env python3
"""
rt_certified_fresh_feed.py

Scrapes Rotten Tomatoes' "Certified Fresh, Newest" theatrical browse page
and writes an RSS feed in the flat "Title (Year)" format that Radarr's
'RSS List' import-list type expects:

    <rss><channel>
      <item>
        <title><![CDATA[ Movie Name (2026) ]]></title>
        <guid isPermaLink="false">Movie Name (2026)</guid>
      </item>
    </channel></rss>

Only new theatrical openings are included ("Opens"/"Opened"); re-releases
("Re-released"/"Re-releasing") are skipped.

Usage:
    python3 rt_certified_fresh_feed.py [output_path]

Requires: requests, beautifulsoup4
    pip install requests beautifulsoup4
"""
import re
import sys
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup

SOURCE_URL = (
    "https://www.rottentomatoes.com/browse/movies_in_theaters/"
    "critics:certified_fresh~sort:newest"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Each movie tile is an <a class="js-tile-link" href="/m/...">, containing a
# title element and a separate start-date element:
#   <rt-text data-qa="discovery-media-list-item-title">Bad Apples</rt-text>
#   <rt-text data-qa="discovery-media-list-item-start-date">Opens Sep 18, 2026</rt-text>
TITLE_SELECTOR = '[data-qa="discovery-media-list-item-title"]'
DATE_SELECTOR = '[data-qa="discovery-media-list-item-start-date"]'


def fetch_movies():
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    movies = []
    seen = set()
    for a in soup.select("a.js-tile-link"):
        title_el = a.select_one(TITLE_SELECTOR)
        date_el = a.select_one(DATE_SELECTOR)
        if not title_el or not date_el:
            continue

        title = title_el.get_text(strip=True)
        date_text = date_el.get_text(strip=True)

        # Only keep new theatrical openings; skip "Re-released"/"Re-releasing"
        if not (date_text.startswith("Opens") or date_text.startswith("Opened")):
            continue

        year_match = re.search(r"(\d{4})$", date_text)
        if not year_match:
            continue
        year = year_match.group(1)

        link = a.get("href", "")
        if not link.startswith("http"):
            link = "https://www.rottentomatoes.com" + link

        key = (title, year)
        if key in seen:
            continue
        seen.add(key)
        movies.append({"title": title, "year": year, "link": link})

    return movies


def build_rss(movies):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    items = []
    for m in movies:
        full_title = f"{m['title']} ({m['year']})"
        items.append(
            "  <item>\n"
            f"    <title><![CDATA[ {full_title} ]]></title>\n"
            f"    <link>{escape(m['link'])}</link>\n"
            f'    <guid isPermaLink="false">{escape(full_title)}</guid>\n'
            "  </item>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<rss version=\"2.0\">\n"
        "<channel>\n"
        "  <title>RT Certified Fresh - Newest In Theaters</title>\n"
        "  <description></description>\n"
        f"  <link>{escape(SOURCE_URL)}</link>\n"
        f"  <lastBuildDate>{now}</lastBuildDate>\n"
        + "\n".join(items)
        + "\n</channel>\n</rss>\n"
    )


if __name__ == "__main__":
    movies = fetch_movies()
    rss = build_rss(movies)
    out_path = sys.argv[1] if len(sys.argv) > 1 else "rss.xml"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"Wrote {len(movies)} movies to {out_path}", file=sys.stderr)
