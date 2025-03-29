import requests
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

# The script is in Data_Queries, so we go one level up to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Construct the relative path for the JSON output file located in Game_Dataframe
OUTPUT_FILE = PROJECT_ROOT / "Game_Dataframe" / "march_madness_games.json"

# Define the date range: from March 13, 2025 to June 30, 2025
start_date = datetime(2025, 3, 13)
end_date = datetime(2025, 6, 30)
date_list = [(start_date + timedelta(days=i)).strftime("%Y%m%d") for i in range((end_date - start_date).days + 1)]

def fetch_simplified_march_madness():
    all_simplified_rows = []
    
    # Loop over each date in the range and fetch data
    for date in date_list:
        url = (
            "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
            f"?dates={date}&groups=50&limit=500"
        )
        print(f"🔄 Fetching March Madness data for {date}...")
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ Error fetching data for {date}: HTTP {response.status_code}")
            continue
        
        data = response.json()
        events = data.get("events", [])
        
        # Process each event (game)
        for event in events:
            # Extract simplified event-level fields
            event_id = event.get("id")
            event_uid = event.get("uid")
            event_date = event.get("date")
            event_name = event.get("name")
            event_shortName = event.get("shortName")
            
            # Process each competition in the event
            competitions = event.get("competitions", [])
            for competition in competitions:
                comp_id = competition.get("id")
                comp_uid = competition.get("uid")
                comp_date = competition.get("date")
                
                # Process each competitor (team) in the competition
                competitors = competition.get("competitors", [])
                for competitor in competitors:
                    competitor_homeAway = competitor.get("homeAway")
                    competitor_score = competitor.get("score")
                    
                    # Expand the team record for key details
                    team = competitor.get("team", {})
                    team_id = team.get("id")
                    team_location = team.get("location")
                    team_name = team.get("name")
                    team_abbreviation = team.get("abbreviation")
                    team_displayName = team.get("displayName")
                    team_shortDisplayName = team.get("shortDisplayName")
                    team_color = team.get("color")
                    team_alternateColor = team.get("alternateColor")
                    team_logo = team.get("logo")
                    
                    # Build a simplified row with only the desired fields
                    row = {
                        "event.id": event_id,
                        "event.uid": event_uid,
                        "event.date": event_date,
                        "event.name": event_name,
                        "event.shortName": event_shortName,
                        "comp.id": comp_id,
                        "comp.uid": comp_uid,
                        "comp.date": comp_date,
                        "comp.competitors.homeAway": competitor_homeAway,
                        "comp.competitors.score": competitor_score,
                        "team.id": team_id,
                        "team.location": team_location,
                        "team.name": team_name,
                        "team.abbreviation": team_abbreviation,
                        "team.displayName": team_displayName,
                        "team.shortDisplayName": team_shortDisplayName,
                        "team.color": team_color,
                        "team.alternateColor": team_alternateColor,
                        "team.logo": team_logo
                    }
                    all_simplified_rows.append(row)
                    
    print(f"✅ Expanded {len(all_simplified_rows)} simplified rows from March Madness data.")
    return all_simplified_rows

def save_data(data, output_path):
    # Ensure the output directory exists
    directory = os.path.dirname(output_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"✅ Created folder: {directory}")
    
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Simplified March Madness data saved to {output_path}")
    except Exception as e:
        print(f"❌ Error writing JSON file: {e}")

def filter_out_tbd_events(data):
    """
    Filters out events where all team.displayName values are "TBD".
    Only events with at least one team with a displayName other than "TBD" are kept.
    """
    grouped_events = defaultdict(list)
    for row in data:
        grouped_events[row["event.id"]].append(row)
    
    filtered_data = []
    for event_id, rows in grouped_events.items():
        if all(row.get("team.displayName") == "TBD" for row in rows):
            print(f"🚫 Excluding event {event_id} because all team.displayName are 'TBD'")
            continue
        filtered_data.extend(rows)
    return filtered_data

if __name__ == "__main__":
    simplified_data = fetch_simplified_march_madness()
    if simplified_data:
        # Filter out events where every team.displayName is "TBD"
        filtered_data = filter_out_tbd_events(simplified_data)
        save_data(filtered_data, OUTPUT_FILE)
