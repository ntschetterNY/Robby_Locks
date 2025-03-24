import requests
import json
import os
import time  # ✅ Import added here
from datetime import datetime, timedelta

# ESPN NHL API URL
NHL_URL = "http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"

# Path where the JSON output data will be saved
JSON_DATA_PATH = r"C:\Users\ntschetter.DESKTOP-2E1G5OF\Desktop\Robby_Locks\Game_Dataframe\nhl_games.json"

# Date range: from March 13, 2025 to June 30, 2025
start_date = datetime(2025, 3, 13)
end_date = datetime(2025, 6, 30)
date_list = [(start_date + timedelta(days=i)).strftime("%Y%m%d") for i in range((end_date - start_date).days + 1)]

# Headers to prevent request blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

def get_nhl_games(date_str):
    """
    Fetch NHL games for a specific date from ESPN API.
    Uses dot notation in the returned JSON fields.
    """
    print(f"🔄 Fetching NHL games for {date_str}...")
    url = f"{NHL_URL}?dates={date_str}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Raise error for non-200 responses
    except requests.RequestException as e:
        print(f"❌ Error fetching data for {date_str}: {e}")
        return []

    data = response.json()
    events = data.get("events", [])

    if not events:
        print(f"⚠️ No games found for {date_str}")
        return []

    games = []
    for event in events:
        event_id = event.get("id", "N/A")
        event_date = event.get("date", "N/A")
        event_name = event.get("shortName", "N/A")
        competitions = event.get("competitions", [])

        for competition in competitions:
            status = competition.get("status", {})
            display_clock = status.get("displayClock", "N/A")
            period = status.get("period", "N/A")
            competitors = competition.get("competitors", [])

            for competitor in competitors:
                team = competitor.get("team", {})
                games.append({
                    "event.id": event_id,  # ✅ Changed from "game.id" to "event.id"
                    "event.date": event_date,
                    "event.name": event_name,
                    "team.id": team.get("id", "N/A"),
                    "team.name": team.get("displayName", "N/A"),
                    "team.abbreviation": team.get("abbreviation", "N/A"),
                    "competitors.score": competitor.get("score", "0"),
                    "status.clock": display_clock,
                    "status.period": period
                })

    print(f"✅ {len(games)} game entries found for {date_str}")
    return games

def fetch_and_store_nhl_games():
    """
    Fetch NHL games for the entire date range and store the expanded data into a JSON file.
    """
    all_games = []

    for i, date in enumerate(date_list):
        games = get_nhl_games(date)
        if games:
            all_games.extend(games)

        if i % 10 == 0:  # Small delay every 10 requests to prevent rate limits
            time.sleep(0)

    if not all_games:
        print("❌ No games fetched. The JSON file will NOT be created.")
        return

    try:
        with open(JSON_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(all_games, f, indent=4)
        print(f"✅ NHL Games data saved to {JSON_DATA_PATH}")
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}")

if __name__ == "__main__":
    fetch_and_store_nhl_games()
