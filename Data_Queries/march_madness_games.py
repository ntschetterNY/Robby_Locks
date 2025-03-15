import requests
import json
import os

# 1) Define the API URL with specified parameters
API_URL = ("https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
           "?dates=20250313-20250323&groups=50&limit=500")

# 2) Define the output file path for the simplified JSON data
OUTPUT_FILE = r"C:\Users\NathanTschetter\OneDrive - The Vorea Group\Desktop\Robby_Locks\Game_Dataframe\march_madness.json"

def fetch_simplified_march_madness():
    print("🔄 Fetching March Madness data from ESPN...")
    response = requests.get(API_URL)
    if response.status_code != 200:
        print(f"❌ Error fetching data: HTTP {response.status_code}")
        return []
    
    data = response.json()
    events = data.get("events", [])
    simplified_rows = []
    
    # 3) Process each event (game)
    for event in events:
        # Extract simplified event-level fields
        event_id = event.get("id")
        event_uid = event.get("uid")
        event_date = event.get("date")
        event_name = event.get("name")
        event_shortName = event.get("shortName")
        
        # 4) Process each competition in the event
        competitions = event.get("competitions", [])
        for competition in competitions:
            comp_id = competition.get("id")
            comp_uid = competition.get("uid")
            comp_date = competition.get("date")
            
            # 5) Process each competitor (team) in the competition
            competitors = competition.get("competitors", [])
            for competitor in competitors:
                # Get competitor simplified fields
                competitor_homeAway = competitor.get("homeAway")
                competitor_score = competitor.get("score")
                
                # 6) Expand the team record for key details
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
                simplified_rows.append(row)
    
    print(f"✅ Expanded {len(simplified_rows)} simplified rows from March Madness data.")
    return simplified_rows

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

if __name__ == "__main__":
    simplified_data = fetch_simplified_march_madness()
    if simplified_data:
        save_data(simplified_data, OUTPUT_FILE)
