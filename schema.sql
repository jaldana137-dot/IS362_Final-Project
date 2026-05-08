-- schema.sql
-- relational schema for the streaming-era project
--
-- I started writing this for postgres but switched to sqlite because
-- it's just a file -- way easier for someone else to spin up and grade.
-- the sql here is plain enough that it would also work on postgres
-- with one or two tweaks (mostly the autoincrement syntax).

-- drop tables if they already exist so I can rerun the loader cleanly
DROP TABLE IF EXISTS artist_genres;
DROP TABLE IF EXISTS track_artists;
DROP TABLE IF EXISTS audio_features;
DROP TABLE IF EXISTS billboard_hits;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS artists;
DROP TABLE IF EXISTS genres;

-- I originally planned to have an "albums" table in the proposal, but once
-- I actually looked at tracks.csv it doesn't have any album metadata, only
-- release_date. Splitting "albums" out of release_date alone would be fake
-- normalization, so I dropped that table and put release_date and
-- release_year directly on tracks. Simpler and more honest.

CREATE TABLE artists (
    artist_id   TEXT PRIMARY KEY,    -- spotify's artist id
    name        TEXT NOT NULL,
    followers   INTEGER,
    popularity  INTEGER
);


CREATE TABLE tracks (
    track_id     TEXT PRIMARY KEY,    -- spotify's track id
    title        TEXT NOT NULL,
    release_date TEXT,                -- ISO date string
    release_year INTEGER,             -- denormalized for fast year filtering
    duration_ms  INTEGER,
    explicit     INTEGER,             -- 0 or 1 (sqlite has no real bool)
    popularity   INTEGER
);


-- many-to-many bridge: a track can have multiple artists, an artist has many tracks
CREATE TABLE track_artists (
    track_id   TEXT REFERENCES tracks(track_id),
    artist_id  TEXT REFERENCES artists(artist_id),
    PRIMARY KEY (track_id, artist_id)
);


-- 1-to-1 with tracks. I split this out from the tracks table because the
-- audio features are conceptually a different "thing" -- they describe how
-- the song *sounds*, not what it is.
CREATE TABLE audio_features (
    track_id          TEXT PRIMARY KEY REFERENCES tracks(track_id),
    danceability      REAL,
    energy            REAL,
    key               INTEGER,
    loudness          REAL,
    mode              INTEGER,
    speechiness       REAL,
    acousticness      REAL,
    instrumentalness  REAL,
    liveness          REAL,
    valence           REAL,
    tempo             REAL,
    time_signature    INTEGER
);


CREATE TABLE genres (
    genre_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT UNIQUE NOT NULL
);


CREATE TABLE artist_genres (
    artist_id  TEXT REFERENCES artists(artist_id),
    genre_id   INTEGER REFERENCES genres(genre_id),
    PRIMARY KEY (artist_id, genre_id)
);


-- the second data source -- billboard year-end hot 100 entries.
-- linked to spotify tracks by track_id once I've matched them.
-- track_id is nullable because not every billboard hit will match a
-- spotify track in this dataset.
CREATE TABLE billboard_hits (
    bb_year     INTEGER NOT NULL,
    bb_rank     INTEGER NOT NULL,
    bb_title    TEXT NOT NULL,
    bb_artist   TEXT NOT NULL,
    track_id    TEXT REFERENCES tracks(track_id),
    PRIMARY KEY (bb_year, bb_rank)
);


-- a couple of indexes for the queries the notebook does a lot of
CREATE INDEX idx_tracks_year ON tracks(release_year);
CREATE INDEX idx_tracks_popularity ON tracks(popularity);
CREATE INDEX idx_track_artists_artist ON track_artists(artist_id);
CREATE INDEX idx_billboard_track ON billboard_hits(track_id);
