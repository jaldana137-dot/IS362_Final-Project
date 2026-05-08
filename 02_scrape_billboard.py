"""
scrape_billboard.py

Scrapes the Billboard Year-End Hot 100 chart for each year from 1990 to 2020.
Saves the result to billboard_year_end.csv with columns: year, rank, title, artist.

I tried scraping billboard.com directly first but the HTML layout is different
basically every year and they seem to dislike scrapers. Wikipedia has the
same chart data in clean tables that have looked the same for years, so I
switched. Same data, way less pain.


It takes about 30-45 seconds
"""

import csv
import os
import sys
import time
import traceback
import requests
from bs4 import BeautifulSoup


# years to scrape matches the era comparison in my proposal
# (album/radio era 1990-2009 vs. streaming era 2010-2020)
START_YEAR = 1990
END_YEAR = 2020

# save the csv into data/ so the loader (01_load_spotify.py) can find it
# next to tracks.csv and artists.csv
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, "billboard_year_end.csv")

# wikipedia is fine with bots but they want a real user-agent
HEADERS = {
    "User-Agent": "student-final-project-scraper/1.0 (contact: julian)"
}


def fetch_year(year):
    """
    Get the year-end hot 100 for one year off Wikipedia.
    Returns a list of dicts (one per song) or [] if something went wrong.
    """
    url = f"https://en.wikipedia.org/wiki/Billboard_Year-End_Hot_100_singles_of_{year}"

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"  [{year}] request failed: {e}")
        return []

    if r.status_code != 200:
        print(f"  [{year}] got status {r.status_code}, skipping")
        return []

    soup = BeautifulSoup(r.text, "html.parser")

    # the chart is the first wikitable on the page. for some years there
    # might be other wikitables (like a "see also" table), so I just take
    # the first one and check if it looks right.
    table = soup.find("table", class_="wikitable")
    if table is None:
        print(f"  [{year}] no wikitable found, page layout might be different")
        return []

    rows = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        # skip header rows they have all <th> elements
        if all(c.name == "th" for c in cells):
            continue

        # first cell is rank. if it doesn't parse as an int, this isn't
        # a real data row (sometimes wikipedia has merged cells or footnotes)
        rank_text = cells[0].get_text(strip=True)
        try:
            rank = int(rank_text)
        except ValueError:
            continue

        # title is usually wrapped in quotes on wikipedia, strip them
        title = cells[1].get_text(strip=True).strip('"').strip("“").strip("”")
        artist = cells[2].get_text(strip=True)

        # some artist cells have footnote markers like [a] or [1], just strip
        # anything in square brackets

        while "[" in artist and "]" in artist:
            start = artist.index("[")
            end = artist.index("]", start)
            artist = artist[:start] + artist[end + 1:]
        artist = artist.strip()

        rows.append({
            "year": year,
            "rank": rank,
            "title": title,
            "artist": artist,
        })

    return rows


def main():
    all_rows = []
    failed_years = []

    for year in range(START_YEAR, END_YEAR + 1):
        print(f"Fetching {year}...", end=" ")
        rows = fetch_year(year)
        if not rows:
            failed_years.append(year)
            print("(no data)")
        else:
            print(f"got {len(rows)} songs")
            all_rows.extend(rows)
        # be polite, don't hammer wikipedia
        time.sleep(1)

    print()
    print(f"Total rows: {len(all_rows)}")
    if failed_years:
        print(f"Years with no data: {failed_years}")
        print("(if any of these are mid-range, the wikipedia page layout for that")
        print("year might be weird and need a manual look. I had to do this for one year.)")

    # save
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["year", "rank", "title", "artist"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Saved to: {OUTPUT_FILE}")
    print()
    print("First 5 rows as a sanity check:")
    for row in all_rows[:5]:
        print(" ", row)


if __name__ == "__main__":
    # finish in try/except so if anything fails up I actually see the error
    # instead of the window closing in my face (like it happened multiple times)
    try:
        main()
        print()
        print("Done!")
    except Exception:
        print()
        print("Something went wrong:")
        traceback.print_exc()

    # keep the window open so I can read the output, this is the part I forgot
    # the first time around. press enter to close.
    print()
    input("Press Enter to close this window...")
