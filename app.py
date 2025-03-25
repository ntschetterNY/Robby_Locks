import sys
sys.path.append("C:/Users/ntschetter.DESKTOP-2E1G5OF/Desktop/Robby_Locks/venv/Lib/site-packages")

import pytz
import os
import json
import platform  # for device name if desired
import dashboard
import dashboard_integration
from datetime import datetime
from flask import Flask, render_template, request
from dateutil.parser import isoparse
from pathlib import Path

# Get the project's root directory based on the current file's location
PROJECT_ROOT = Path(__file__).resolve().parent

# Build paths relative to the project folder
GAME_DATAFRAME_FOLDER = PROJECT_ROOT / "Game_Dataframe"
PICKS_FILE_PATH = PROJECT_ROOT / "Robs_Picks" / "Robs_Picks.json"

NBA_GAMES_FILE = GAME_DATAFRAME_FOLDER / "nba_games.json"
NHL_GAMES_FILE = GAME_DATAFRAME_FOLDER / "nhl_games.json"
MLB_GAMES_FILE = GAME_DATAFRAME_FOLDER / "mlb_games.json"
MARCH_MADNESS_GAMES_FILE = GAME_DATAFRAME_FOLDER / "march_madness_games.json"

# Initialize Flask app
app = Flask(__name__, 
            template_folder='templates_dashboard',
            static_folder='static_dashboard',
            static_url_path='/static')

# Initialize the enhanced dashboard
dashboard_integration.setup_enhanced_dashboard(app, dashboard)

# Timezone setup
utc_tz = pytz.utc
eastern_tz = pytz.timezone("America/New_York")

def load_json_file(file_path):
    """Generic loader for JSON files."""
    if not os.path.exists(file_path):
        print(f"⚠️ JSON file not found: {file_path}")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_picks():
    """Load the picks from Robs_Picks.json as a dictionary keyed by event id."""
    picks = load_json_file(PICKS_FILE_PATH)
    if not isinstance(picks, dict):
        picks = {}
    return picks

def load_nba_games():
    return load_json_file(NBA_GAMES_FILE)

def load_nhl_games():
    return load_json_file(NHL_GAMES_FILE)

def load_mlb_games():
    return load_json_file(MLB_GAMES_FILE)

def load_march_madness_games():
    games = load_json_file(MARCH_MADNESS_GAMES_FILE)
    print(f"Loaded {len(games)} March Madness games")
    if games:
        print(f"Sample game: {games[0]}")
    return games

@app.route("/", methods=["GET", "POST"])
def index():
    saved = False

    # Determine sport and game date from the request
    sport = request.form.get("sport_selector") or request.args.get("sport") or "NBA"
    now = datetime.now(eastern_tz)
    date_str = request.form.get("game_date") or request.args.get("game_date") or now.strftime("%Y-%m-%d")
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    grouped_games = {}

    # Choose the appropriate JSON file based on the sport
    if sport == "NBA":
        all_games = load_nba_games()
    elif sport == "NHL":
        all_games = load_nhl_games()
    elif sport == "MLB":
        all_games = load_mlb_games()
    elif sport == "MarchMadness":
        all_games = load_march_madness_games()
    else:
        all_games = []
    
    print(f"Processing {len(all_games)} games for {sport} on {selected_date}")

    # Process and group games by event id for the selected date
    for g in all_games:
        try:
            # For March Madness, use "event.date" if available; otherwise use "comp.date"
            date_field = "event.date" if ("event.date" in g) else "comp.date"
            print(f"Using date field: {date_field}, value: {g.get(date_field)}")
            
            # Parse the date and assign UTC if no timezone is present
            game_time_parsed = isoparse(g[date_field])
            if game_time_parsed.tzinfo is None:
                game_time_parsed = game_time_parsed.replace(tzinfo=utc_tz)
            game_time_et = game_time_parsed.astimezone(eastern_tz)
            
            print(f"Game date: {game_time_et.date()}, Selected date: {selected_date}")
            
            if game_time_et.date() != selected_date:
                continue
                
            disable_game = (now - game_time_et).total_seconds() > 1200
            event_id = g["event.id"]

            # Determine team details based on sport
            if sport == "MLB":
                team_name = g.get("team.displayName", "N/A")
                team_abbreviation = g.get("team.abbreviation", "N/A")
            elif sport == "MarchMadness":
                team_name = g.get("team.displayName", g.get("team.name", "N/A"))
                team_abbreviation = g.get("team.abbreviation", "N/A")
            else:
                team_name = g.get("team.name", g.get("team.displayName", "N/A"))
                team_abbreviation = g.get("team.abbreviation", "N/A")

            # Determine score and status fields based on sport
            if sport == "MarchMadness":
                score = g.get("comp.competitors.score", "0")
                status_clock = g.get("comp.status.displayClock", "N/A")
                status_period = g.get("comp.status.period", "N/A")
            else:
                score = g.get("competitors.score", g.get("comp.competitors.score", "0"))
                status_clock = g.get("status.clock", g.get("comp.status.displayClock", "N/A"))
                status_period = g.get("status.period", g.get("comp.status.period", "N/A"))

            if event_id not in grouped_games:
                grouped_games[event_id] = {
                    "event_id": event_id,
                    "event_date": game_time_et.strftime("%I:%M %p ET"),
                    "event_name": g.get("event.name", g.get("event.shortName", "N/A")),
                    "team_1_name": team_name,
                    "team_1_abbreviation": team_abbreviation,
                    "team_2_name": "",
                    "team_2_abbreviation": "",
                    "score": score,
                    "status_clock": status_clock,
                    "status_period": status_period,
                    "disable_game": disable_game,
                }
            else:
                grouped_games[event_id]["team_2_name"] = team_name
                grouped_games[event_id]["team_2_abbreviation"] = team_abbreviation
        except Exception as e:
            print(f"❌ Skipping {sport} game: {e}")

    # Only include fully formed games (with 2 teams)
    games = [game for game in grouped_games.values() if game["team_2_name"]]
    print(f"Found {len(games)} valid games for {sport} on {selected_date}")
    
    # Sort games by their start time if possible
    try:
        games = sorted(games, key=lambda x: datetime.strptime(x["event_date"], "%I:%M %p ET"))
    except Exception as e:
        print("❌ Error sorting games:", e)

    # Process picks submission
    if request.method == "POST" and "lock_picks" in request.form:
        existing_picks = load_picks()
        for key, value in request.form.items():
            if key.startswith("winner_"):
                event_id = key.split("_", 1)[1]
                ip_address = request.remote_addr or ""
                user_agent = request.headers.get("User-Agent", "")
                device_name = platform.node()
                nice_date_str = selected_date.strftime("%A, %B %d, %Y")
                if event_id in grouped_games:
                    event_start_time = grouped_games[event_id].get("event_date", "N/A")
                else:
                    event_start_time = "N/A"
                existing_picks[event_id] = {
                    "EventID": event_id,
                    "Value.winner": value,
                    "Value.address": ip_address,
                    "Value.device_name": device_name,
                    "Value.user_agent": user_agent,
                    "Value.timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Value.game_date": nice_date_str,
                    "Value.game_start_time": event_start_time
                }
        with open(PICKS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_picks, f, indent=4)
        saved = True

    selected_games = load_picks()

    return render_template(
        "index.html",
        saved=saved,
        games=games,
        selected_games=selected_games,
        today_str=date_str,
        sport=sport
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)