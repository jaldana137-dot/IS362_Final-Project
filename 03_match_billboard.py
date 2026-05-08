"""
03_match_billboard.py

Tries to match each row in billboard_hits to a spotify track_id by
comparing normalized song title and artist name.

This is the ugliest part of the project and I rewrote it like 4 times.
Matching by exact strings doesn't work because the Billboard and Spotify
formats disagree all the time:
    Billboard:  "I Will Always Love You"  by  "Whitney Houston"
    Spotify:    "I Will Always Love You - Film Version" by "Whitney Houston"

A bunch of billboard hits won't match, I just want a
reasonably-sized matched set to analyze. The match rate is printed
at the end...

"""

import os
import re
import sqlite3
import ast
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "music.db")



# normalization helpers
# ----------------------------------

# things in titles that I want to strip out before comparing.
# things like "- 2014 Remaster" or "(feat. Drake)" -- spotify adds these
# and billboard does not.
TITLE_NOISE_PATTERNS = [
    r"-\s*\d{4}\s*remaster.*$",      # "- 2014 Remaster"
    r"-\s*remaster(?:ed)?.*$",        # "- Remastered"
    r"-\s*single\s*version.*$",       # "- Single Version"
    r"-\s*radio\s*edit.*$",
    r"-\s*album\s*version.*$",
    r"-\s*film\s*version.*$",
    r"-\s*from.*$",                   # "- From the Movie"
    r"\(feat\..*?\)",                 # "(feat. ...)"
    r"\(featuring.*?\)",
    r"\[feat\..*?\]",
    r"-\s*feat\..*$",
]


def normalize_title(s):
    """Lowercase, strip noise patterns, strip non-alphanumeric, collapse spaces."""
    if not isinstance(s, str):
        return ""
    s = s.lower()
    for pat in TITLE_NOISE_PATTERNS:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)
    # remove anything that isn't a letter, digit, or space
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# things in artist names I want to chop off before comparing.
# the "billboard wikipedia" scrape ends up with stuff like
# "Linda RonstadtfeaturingAaron Neville" with no spaces, so I have to
# handle the "featuring" word and split on it before normalizing.
ARTIST_FEAT_SPLITTERS = [
    "featuring",
    "feat.",
    "feat ",
    " ft. ",
    " ft ",
    " with ",
    " & ",
    " and ",
    " x ",
    ",",
]


def primary_artist(s):
    """Take a possibly-comma-or-feat-separated artist string and return
    the first artist only, normalized."""
    if not isinstance(s, str):
        return ""
    s_lower = s.lower()
    for splitter in ARTIST_FEAT_SPLITTERS:
        if splitter in s_lower:
            # find the position in the original-cased string and cut there
            idx = s_lower.index(splitter)
            s = s[:idx]
            s_lower = s.lower()
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s



# main matching logic
# ----------------------------------------------------------------------

def build_spotify_lookup(conn):
    """
    Build a dict that maps (normalized_title, normalized_primary_artist)
    to a list of (track_id, release_year) candidates.
    """
    print("Loading spotify tracks for matching...")
    # join tracks to artists to get the primary artist name for each track.
    # I'm doing this in SQL because it's way faster than pulling everything
    # into python and looping.
    sql = """
        SELECT t.track_id, t.title, t.release_year, a.name AS artist_name
        FROM tracks t
        JOIN track_artists ta ON ta.track_id = t.track_id
        JOIN artists a       ON a.artist_id = ta.artist_id
    """
    rows = conn.execute(sql).fetchall()
    print(f"  {len(rows):,} (track, artist) rows to scan")

    lookup = defaultdict(list)
    for track_id, title, year, artist_name in rows:
        nt = normalize_title(title)
        na = primary_artist(artist_name)
        if nt and na:
            lookup[(nt, na)].append((track_id, year))

    print(f"  {len(lookup):,} unique (title, primary_artist) keys")
    return lookup


def match_billboard(conn, lookup):
    """For each billboard_hits row, pick the best matching track_id and
    write it back to the billboard_hits table."""
    print("Matching billboard rows...")
    bb_rows = conn.execute(
        "SELECT bb_year, bb_rank, bb_title, bb_artist FROM billboard_hits"
    ).fetchall()

    matched = 0
    updates = []
    for year, rank, title, artist in bb_rows:
        nt = normalize_title(title)
        na = primary_artist(artist)
        candidates = lookup.get((nt, na), [])

        if not candidates:
            continue

        # pick the candidate whose release year is closest to the
        # billboard chart year (handles re-releases)
        best = min(candidates, key=lambda c: abs((c[1] or 0) - year))
        updates.append((best[0], year, rank))
        matched += 1

    # write back
    conn.executemany(
        "UPDATE billboard_hits SET track_id = ? WHERE bb_year = ? AND bb_rank = ?",
        updates,
    )
    conn.commit()

    total = len(bb_rows)
    pct = 100.0 * matched / total if total else 0
    print(f"  matched {matched:,} / {total:,}  ({pct:.1f}%)")


def main():
    conn = sqlite3.connect(DB_PATH)
    lookup = build_spotify_lookup(conn)
    match_billboard(conn, lookup)

    # quick sanity check
    n_with_id = conn.execute(
        "SELECT COUNT(*) FROM billboard_hits WHERE track_id IS NOT NULL"
    ).fetchone()[0]
    print(f"\nbillboard_hits rows now linked to a spotify track_id: {n_with_id:,}")

    conn.close()


if __name__ == "__main__":
    main()
