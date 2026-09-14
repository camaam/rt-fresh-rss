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

# Matches text like: "Runner Opened Sep 11, 2026" or
# "Marketa Lazarová Re-released Sep 04, 2026" (after the score % is stripped)
ITEM_RE = re.compile(r"^(?P<title>.+?)\s+(?:Opened|Re-released)\s+.*?(?P<year>\d{4})$")


def fetch_movies():
    resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    movies = []
    seen = set()
    for a in soup.select('a[href*="/m/"]'):
        text = " ".join(a.get_text(" ", strip=True).split())
        if "Opened" not in text and "Re-released" not in text:
            continue  # skip sidebar/promo links that aren't grid items

        # strip leading Tomatometer/Popcornmeter score(s), e.g. "91% 89% "
        text = re.sub(r"^(?:\d{1,3}%\s*){1,2}", "", text)

        m = ITEM_RE.match(text)
        if not m:
            continue

        title = m.group("title").strip()
        year = m.group("year")
        link = a["href"]
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
