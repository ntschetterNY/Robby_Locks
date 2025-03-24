import requests
import json
import os
from datetime import datetime, timedelta

# Base ESPN MLB API URL (expects date in YYYYMMDD format)
MLB_URL = "http://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates="

# Define the output file path for the JSON data
OUTPUT_FILE = r"C:\Users\ntschetter.DESKTOP-2E1G5OF\Desktop\Robby_Locks\Game_Dataframe\mlb_games.json"

# 1) Generate a list of dates from March 13, 2025 to June 30, 2025 (YYYYMMDD format)
start_date = datetime(2025, 3, 13)
end_date = datetime(2025, 6, 30)
date_list = [(start_date + timedelta(days=i)).strftime("%Y%m%d") for i in range((end_date - start_date).days + 1)]

def get_mlb_games_for_date(date_str):
    """
    Fetch MLB games for a specific date from the ESPN API and return a list of simplified rows.
    For each event, this function extracts:
      - Top-level event fields: id, date, shortName.
      - From each competition: status (displayClock, period).
      - From each competitor: score and team info (id, displayName, abbreviation).
    """
    print(f"🔄 Fetching MLB games for {date_str}...")
    url = MLB_URL + date_str
    try:
        response = requests.get(url)
    except Exception as e:
        print(f"❌ Exception fetching data for {date_str}: {e}")
        return []
    
    if response.status_code != 200:
        print(f"❌ Error fetching data for {date_str}: HTTP {response.status_code}")
        return []
    
    data = response.json()
    events = data.get("events", [])
    rows = []
    
    for event in events:
        # Expand top-level event fields
        event_id = event.get("id")
        event_date = event.get("date")
        event_shortName = event.get("shortName")
        
        # Each event has one or more competitions
        competitions = event.get("competitions", [])
        for competition in competitions:
            # Expand the competition status fields
            comp_status = competition.get("status", {})
            display_clock = comp_status.get("displayClock")
            period = comp_status.get("period")
            
            # Expand the competitors (teams)
            competitors = competition.get("competitors", [])
            for competitor in competitors:
                competitor_score = competitor.get("score", "0")
                team = competitor.get("team", {})
                team_id = team.get("id")
                team_displayName = team.get("displayName")
                team_abbreviation = team.get("abbreviation")
                
                # Build the flattened row
                row = {
                    "event.id": event_id,
                    "event.date": event_date,
                    "event.shortName": event_shortName,
                    "comp.status.displayClock": display_clock,
                    "comp.status.period": period,
                    "comp.competitors.score": competitor_score,
                    "team.id": team_id,
                    "team.displayName": team_displayName,
                    "team.abbreviation": team_abbreviation
                }
                rows.append(row)
    
    print(f"✅ Extracted {len(rows)} rows for {date_str}.")
    return rows

def fetch_and_store_mlb_games():
    """ Fetch MLB games for the full date range and save the simplified data as JSON. """
    all_rows = []
    for date_str in date_list:
        rows = get_mlb_games_for_date(date_str)
        if rows:
            all_rows.extend(rows)
    
    if not all_rows:
        print("❌ No games fetched. JSON file will not be created.")
        return
    
    # Ensure the output directory exists
    output_dir = os.path.dirname(OUTPUT_FILE)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✅ Created folder: {output_dir}")
    
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, indent=4)
        print(f"✅ MLB games data saved to {OUTPUT_FILE}")
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}")

if __name__ == "__main__":
    fetch_and_store_mlb_games()
