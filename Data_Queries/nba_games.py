import requests
import json
import os
from datetime import datetime, timedelta

# ESPN NBA API URL
ESPN_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"

# Define root folder and JSON file path
ROOT_FOLDER = r"C:\Users\NathanTschetter\OneDrive - The Vorea Group\Desktop\Robby_Locks\Game_Dataframe"
JSON_FILE_PATH = os.path.join(ROOT_FOLDER, "nba_games.json")

# Ensure the root folder exists
if not os.path.exists(ROOT_FOLDER):
    os.makedirs(ROOT_FOLDER)
    print(f"✅ Created folder: {ROOT_FOLDER}")

# Generate a list of dates from March 13, 2025, to June 30, 2025
start_date = datetime(2025, 3, 13)
end_date = datetime(2025, 6, 30)
date_list = [(start_date + timedelta(days=i)).strftime("%Y%m%d") for i in range((end_date - start_date).days + 1)]

def get_nba_games(date_str):
    """Fetch NBA games for a specific date from ESPN API, returning dot-notation keys."""
    print(f"🔄 Fetching NBA games for {date_str}...")
    response = requests.get(f"{ESPN_URL}?dates={date_str}")

    if response.status_code != 200:
        print(f"❌ Error fetching data for {date_str}: HTTP {response.status_code}")
        return []

    data = response.json()
    events = data.get("events", [])

    games = []
    for event in events:
        event_id = event["id"]
        event_date = event["date"]
        event_name = event["shortName"]
        competitions = event.get("competitions", [])

        for competition in competitions:
            comp_status = competition.get("status", {})
            display_clock = comp_status.get("displayClock", "N/A")
            period = comp_status.get("period", "N/A")
            competitors = competition.get("competitors", [])

            for competitor in competitors:
                team_info = competitor.get("team", {})
                games.append({
                    "game.id": event_id,
                    "event.date": event_date,
                    "event.name": event_name,
                    "team.id": team_info.get("id"),
                    "team.name": team_info.get("displayName"),
                    "team.abbreviation": team_info.get("abbreviation"),
                    "competitors.score": competitor.get("score", "0"),
                    "status.clock": display_clock,
                    "status.period": period,
                })
    
    print(f"✅ {len(games)} games found for {date_str}")
    return games

def fetch_and_store_nba_games():
    """Fetch NBA games for the full date range and store in JSON."""
    all_games = []
    
    for date_str in date_list:
        games = get_nba_games(date_str)
        if games:
            all_games.extend(games)

    if not all_games:
        print("❌ No games fetched. The JSON file will NOT be created.")
        return

    # Save to JSON file
    try:
        with open(JSON_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(all_games, f, indent=4)
        print(f"✅ NBA Games data saved to {JSON_FILE_PATH}")
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}")

if __name__ == "__main__":
    fetch_and_store_nba_games()
