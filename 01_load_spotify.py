"""
01_load_spotify.py

Loads tracks.csv and artists.csv (downloaded from the Kaggle Spotify dataset)
into a local SQLite database called music.db, normalized into the tables
defined in schema.sql.

"""

import os
import sqlite3
import ast
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
DB_PATH = os.path.join(HERE, "music.db")
SCHEMA_PATH = os.path.join(HERE, "schema.sql")

TRACKS_CSV = os.path.join(DATA_DIR, "tracks.csv")
ARTISTS_CSV = os.path.join(DATA_DIR, "artists.csv")


def parse_list_string(s):
    """
    The artists/genres columns in the kaggle CSV are stored as stringified
    python lists like "['Uli', 'Other Person']". ast.literal_eval safely
    parses them into real lists. If parsing fails, returns empty list.

    """
    if pd.isna(s) or s == "":
        return []
    try:
        result = ast.literal_eval(s)
        if isinstance(result, list):
            return result
        return []
    except (ValueError, SyntaxError):
        return []


def create_schema(conn):
    """Run schema.sql to create all the tables fresh."""
    print("Creating schema...")
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()


def load_artists(conn):
    """Load artists.csv -> artists, genres, artist_genres tables."""
    print("Reading artists.csv...")
    df = pd.read_csv(ARTISTS_CSV)
    print(f"  {len(df):,} artists in csv")

    # a handful of rows have a NaN name drop those, the schema requires a name
    nulls = df["name"].isna().sum()
    if nulls > 0:
        print(f"  dropping {nulls} artist rows with no name")
        df = df[df["name"].notna()].copy()

    # the followers column is float in the CSV (because of NaNs).
    # cast to int but keep NaN -> None.
    df["followers"] = df["followers"].apply(
        lambda x: int(x) if pd.notna(x) else None
    )

    # parse the genres column from "['rock', 'pop']" -> real list
    df["genres_list"] = df["genres"].apply(parse_list_string)

    # write the simple artists rows first
    print("Inserting artists...")
    artist_rows = list(zip(
        df["id"],
        df["name"],
        df["followers"],
        df["popularity"],
    ))
    conn.executemany(
        "INSERT INTO artists (artist_id, name, followers, popularity) "
        "VALUES (?, ?, ?, ?)",
        artist_rows,
    )

    # build a unique set of all genres to give them ids
    print("Inserting genres + artist_genres...")
    all_genres = set()
    for g_list in df["genres_list"]:
        for g in g_list:
            all_genres.add(g)
    print(f"  {len(all_genres):,} unique genres")

    # insert genres and remember the auto-incremented ids
    genre_id_map = {}
    for g in sorted(all_genres):
        cur = conn.execute(
            "INSERT INTO genres (name) VALUES (?)", (g,)
        )
        genre_id_map[g] = cur.lastrowid

    # build the bridge rows
    bridge_rows = []
    for artist_id, g_list in zip(df["id"], df["genres_list"]):
        for g in g_list:
            bridge_rows.append((artist_id, genre_id_map[g]))

    # there can be duplicate (artist, genre) pairs in the csv apparently,
    # so I use insert or ignore so the primary key complaint doesn't blow
    # things up
    conn.executemany(
        "INSERT OR IGNORE INTO artist_genres (artist_id, genre_id) VALUES (?, ?)",
        bridge_rows,
    )

    conn.commit()


def load_tracks(conn):
    """Load tracks.csv -> tracks, audio_features, track_artists tables."""
    print("Reading tracks.csv...")
    df = pd.read_csv(TRACKS_CSV)
    print(f"  {len(df):,} tracks in csv")

    # parse out release_year from release_date
    # release_date can be "1990-01-15" OR just "1990"  so I take first 4 chars
    df["release_year"] = df["release_date"].astype(str).str[:4]
    df["release_year"] = pd.to_numeric(df["release_year"], errors="coerce")

    # drop tracks where the year couldn't be parsed (a few weird rows)
    bad = df["release_year"].isna().sum()
    if bad > 0:
        print(f"  dropping {bad} rows with un-parseable release_date")
    df = df[df["release_year"].notna()].copy()
    df["release_year"] = df["release_year"].astype(int)

    # tracks table
    print("Inserting tracks...")
    track_rows = list(zip(
        df["id"],
        df["name"],
        df["release_date"],
        df["release_year"],
        df["duration_ms"],
        df["explicit"],
        df["popularity"],
    ))
    conn.executemany(
        "INSERT OR IGNORE INTO tracks "
        "(track_id, title, release_date, release_year, duration_ms, explicit, popularity) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        track_rows,
    )

    # audio_features table, 1 to 1 with tracks
    print("Inserting audio_features...")
    af_rows = list(zip(
        df["id"],
        df["danceability"],
        df["energy"],
        df["key"],
        df["loudness"],
        df["mode"],
        df["speechiness"],
        df["acousticness"],
        df["instrumentalness"],
        df["liveness"],
        df["valence"],
        df["tempo"],
        df["time_signature"],
    ))
    conn.executemany(
        "INSERT OR IGNORE INTO audio_features "
        "(track_id, danceability, energy, key, loudness, mode, speechiness, "
        "acousticness, instrumentalness, liveness, valence, tempo, time_signature) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        af_rows,
    )

    # track_artists bridge this is the slow part
    print("Building track_artists bridge (this is the slow one)...")
    df["id_artists_list"] = df["id_artists"].apply(parse_list_string)

    bridge_rows = []
    for tid, aid_list in zip(df["id"], df["id_artists_list"]):
        for aid in aid_list:
            bridge_rows.append((tid, aid))
    print(f"  {len(bridge_rows):,} track-artist links")


    conn.executemany(
        "INSERT OR IGNORE INTO track_artists (track_id, artist_id) VALUES (?, ?)",
        bridge_rows,
    )

    conn.commit()


def load_billboard(conn):
    """Load billboard_year_end.csv -> billboard_hits table.
    Note: track_id is left NULL here -- the matching script (03) fills it in."""
    bb_path = os.path.join(DATA_DIR, "billboard_year_end.csv")
    print("Reading billboard_year_end.csv...")
    df = pd.read_csv(bb_path)
    print(f"  {len(df):,} billboard rows")

    bb_rows = list(zip(
        df["year"],
        df["rank"],
        df["title"],
        df["artist"],
    ))
    conn.executemany(
        "INSERT INTO billboard_hits (bb_year, bb_rank, bb_title, bb_artist) "
        "VALUES (?, ?, ?, ?)",
        bb_rows,
    )
    conn.commit()


def print_counts(conn):
    """Sanity-check by printing how many rows ended up in each table."""
    print()
    print("Final row counts:")
    tables = ["artists", "tracks", "audio_features", "track_artists",
              "genres", "artist_genres", "billboard_hits"]
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:20s} {n:>12,}")


def main():
    # delete an old db file if there is one. easier than trying to
    # diff what changed.
    if os.path.exists(DB_PATH):
        print(f"Removing existing {DB_PATH}")
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    # this makes sqlite a bit faster on big bulk inserts
    conn.execute("PRAGMA journal_mode = OFF")
    conn.execute("PRAGMA synchronous = OFF")

    create_schema(conn)
    load_artists(conn)
    load_tracks(conn)
    load_billboard(conn)
    print_counts(conn)

    conn.close()
    print()
    print(f"Done. Database written to {DB_PATH}")


if __name__ == "__main__":
    main()
