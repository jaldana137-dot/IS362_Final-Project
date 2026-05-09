Did streaming change what a hit sounds like?

Final project for Data Acquisition and Management. The question I'm trying to
answer: comparing popular tracks from the album-and-radio era (1990 to 2009)
to the streaming era (2010 to 2020), are streaming-era hits measurably
shorter, louder, less acoustic, more danceable, and more often explicit, or
are those claims industry folklore that the data doesn't support?


What's in here


streaming_era_project/
 README.md                  this file
 requirements.txt           python deps
 schema.sql                 sqlite schema (normalized, 7 tables)
 01_load_spotify.py         loads tracks.csv + artists.csv into music.db
 02_scrape_billboard.py     scrapes wikipedia year-end billboard hot 100
 03_match_billboard.py      fuzzy-matches billboard rows to spotify track_ids
 analysis.ipynb             the actual analysis with all the plots and stats
 data/                      put the input CSVs here (see below)
 figures/                   generated plots (auto-created when you run things)

Data sources

Two different types of source:

1. Relational and CSV. The Kaggle Spotify Tracks dataset
   ([yamaerenay/spotify-dataset-19212020-160k-tracks](https://www.kaggle.com/datasets/yamaerenay/spotify-dataset-19212020-600k-tracks)) 
   You need to download `tracks.csv` and `artists.csv` and put them in `data/`. (too big to upload to github)

2. Scraped web page. Billboard year-end Hot 100 charts for 1990 to 2020,
   scraped from Wikipedia. The scraper writes to `data/billboard_year_end.csv`. (it's already in the folder)

I originally tried scraping billboard.com directly but their HTML layout
changes a lot between years and they have anti-scraping stuff. Wikipedia has
the same chart data in clean stable tables. Same data, way less hassle.

## How to run it

Python 3.10 or newer is needed


# 1) install deps
pip install -r requirements.txt

# 2) put the kaggle CSVs in data/
#    - tracks.csv    (~80 MB)
#    - artists.csv   (~13 MB)

# 3) scrape billboard year-end charts (takes ~45 sec)
python 02_scrape_billboard.py

# 4) load everything into sqlite (takes ~1-2 minutes)
python 01_load_spotify.py

# 5) match billboard hits to spotify track_ids (takes ~10 sec)
python 03_match_billboard.py

# 6) run the notebook
jupyter notebook analysis.ipynb



