import os
import json
import pytz
import socket
from datetime import datetime, timedelta
from flask import Flask, render_template, request
from dateutil.parser import isoparse  # More robust ISO date parser

# File paths
GAME_DATAFRAME_FOLDER = r"C:\Users\NathanTschetter\OneDrive - The Vorea Group\Desktop\Robby_Locks\Game_Dataframe"
PICKS_FILE_PATH = r"C:\Users\NathanTschetter\OneDrive - The Vorea Group\Desktop\Robby_Locks\Robs_Picks\Robs_Picks.json"
NBA_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "nba_games.json")
NHL_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "nhl_games.json")
MLB_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "mlb_games.json")
MARCH_MADNESS_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "march_madness_games.json")

app = Flask(__name__)

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


def load_nba_games():
    return load_json_file(NBA_GAMES_FILE)


def load_nhl_games():
    return load_json_file(NHL_GAMES_FILE)


def load_mlb_games():
    return load_json_file(MLB_GAMES_FILE)


def load_march_madness_games():
    return load_json_file(MARCH_MADNESS_GAMES_FILE)


def load_picks():
    """Load user picks from JSON."""
    if not os.path.exists(PICKS_FILE_PATH):
        return {}
    with open(PICKS_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_picks(picks, request_data):
    """Save user picks to JSON with additional debugging information."""
    os.makedirs(os.path.dirname(PICKS_FILE_PATH), exist_ok=True)
    ip_address = request.remote_addr
    device_name = socket.gethostname()
    user_agent = request.headers.get('User-Agent')
    timestamp = datetime.now(eastern_tz).strftime("%Y-%m-%d %I:%M:%S %p ET")
    for game_id, winner in request_data.items():
        if game_id.startswith("winner_"):
            game_id_clean = game_id.replace("winner_", "")
            game_info = picks.get(game_id_clean, {})
            if not isinstance(game_info, dict):
                game_info = {}
            picks[game_id_clean] = {
                "winner": winner,
                "ip_address": ip_address,
                "device_name": device_name,
                "user_agent": user_agent,
                "timestamp": timestamp,
                "game_date": request_data.get("game_date", "N/A"),
                "game_start_time": game_info.get("game_start_time", "N/A")
            }
    with open(PICKS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=4)


@app.route("/", methods=["GET", "POST"])
def index():
    games = []
    selected_games = load_picks()
    # Default sport is NBA; sport selector options: NBA, NHL, MLB, MarchMadness.
    sport = request.form.get("sport_selector") or request.args.get("sport") or "NBA"
    now = datetime.now(eastern_tz)
    # Retrieve the date from form submission or default to today's date.
    date_str = request.form.get("game_date") or request.args.get("game_date") or now.strftime("%Y-%m-%d")
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    grouped_games = {}

    # Debug: Print selected sport and date
    print(f"Selected sport: {sport}, Selected date: {selected_date}")

    if sport == "NBA":
        all_games = load_nba_games()
        print(f"Loaded {len(all_games)} NBA game entries")
        # Expected keys: "game.id", "event.date", "event.name", "team.name", "team.abbreviation"
        for g in all_games:
            try:
                game_time_utc = isoparse(g["event.date"]).replace(tzinfo=utc_tz)
                game_time_et = game_time_utc.astimezone(eastern_tz)
                # Debug: Print parsed game time
                # print(f"NBA game time ET: {game_time_et}")
                if game_time_et.date() != selected_date:
                    continue
                disable_game = (now - game_time_et).total_seconds() > 1200  # 20 minutes
                game_id = g["game.id"]
                if game_id not in grouped_games:
                    grouped_games[game_id] = {
                        "game_id": game_id,
                        "event_date": game_time_et.strftime("%I:%M %p ET"),
                        "event_name": g["event.name"],
                        "team_1_name": g["team.name"],
                        "team_1_abbreviation": g["team.abbreviation"],
                        "team_2_name": "",
                        "team_2_abbreviation": "",
                        "disable_game": disable_game,
                        "game_start_time": game_time_et.strftime("%Y-%m-%d %I:%M %p ET")
                    }
                else:
                    grouped_games[game_id]["team_2_name"] = g["team.name"]
                    grouped_games[game_id]["team_2_abbreviation"] = g["team.abbreviation"]
            except Exception as e:
                print(f"❌ Skipping NBA game: {g.get('event.date')} - {e}")

    elif sport == "NHL":
        all_games = load_nhl_games()
        print(f"Loaded {len(all_games)} NHL game entries")
        # Expected keys: "game.id", "event.date", "event.name", "team.name", "team.abbreviation"
        for g in all_games:
            try:
                game_time_utc = isoparse(g["event.date"]).replace(tzinfo=utc_tz)
                game_time_et = game_time_utc.astimezone(eastern_tz)
                if game_time_et.date() != selected_date:
                    continue
                disable_game = (now - game_time_et).total_seconds() > 1200
                game_id = g["game.id"]
                if game_id not in grouped_games:
                    grouped_games[game_id] = {
                        "game_id": game_id,
                        "event_date": game_time_et.strftime("%I:%M %p ET"),
                        "event_name": g["event.name"],
                        "team_1_name": g["team.name"],
                        "team_1_abbreviation": g["team.abbreviation"],
                        "team_2_name": "",
                        "team_2_abbreviation": "",
                        "disable_game": disable_game,
                        "game_start_time": game_time_et.strftime("%Y-%m-%d %I:%M %p ET")
                    }
                else:
                    grouped_games[game_id]["team_2_name"] = g["team.name"]
                    grouped_games[game_id]["team_2_abbreviation"] = g["team.abbreviation"]
            except Exception as e:
                print(f"❌ Skipping NHL game: {g.get('event.date')} - {e}")

    elif sport == "MLB":
        all_games = load_mlb_games()
        print(f"Loaded {len(all_games)} MLB game entries")
        # Expected keys: "event.date", "event.shortName", "team.displayName", "team.abbreviation", "event.id"
        for g in all_games:
            try:
                game_time_utc = isoparse(g["event.date"]).replace(tzinfo=utc_tz)
                game_time_et = game_time_utc.astimezone(eastern_tz)
                if game_time_et.date() != selected_date:
                    continue
                disable_game = (now - game_time_et).total_seconds() > 1200
                game_id = g["event.id"]
                if game_id not in grouped_games:
                    grouped_games[game_id] = {
                        "game_id": game_id,
                        "event_date": game_time_et.strftime("%I:%M %p ET"),
                        "event_name": g["event.shortName"],
                        "team_1_name": g["team.displayName"],
                        "team_1_abbreviation": g["team.abbreviation"],
                        "team_2_name": "",
                        "team_2_abbreviation": "",
                        "disable_game": disable_game,
                        "game_start_time": game_time_et.strftime("%Y-%m-%d %I:%M %p ET")
                    }
                else:
                    grouped_games[game_id]["team_2_name"] = g["team.displayName"]
                    grouped_games[game_id]["team_2_abbreviation"] = g["team.abbreviation"]
            except Exception as e:
                print(f"❌ Skipping MLB game: {g.get('event.date')} - {e}")

    elif sport == "MarchMadness":
        all_games = load_march_madness_games()
        print(f"Loaded {len(all_games)} March Madness game entries")
        # Expected keys: "event.date", "event.name" or "event.shortName", "team.displayName", "team.abbreviation", "event.id"
        for g in all_games:
            try:
                game_time_utc = isoparse(g["event.date"]).replace(tzinfo=utc_tz)
                game_time_et = game_time_utc.astimezone(eastern_tz)
                if game_time_et.date() != selected_date:
                    continue
                disable_game = (now - game_time_et).total_seconds() > 1200
                game_id = g["event.id"]
                if game_id not in grouped_games:
                    grouped_games[game_id] = {
                        "game_id": game_id,
                        "event_date": game_time_et.strftime("%I:%M %p ET"),
                        "event_name": g.get("event.name", g.get("event.shortName", "N/A")),
                        "team_1_name": g["team.displayName"],
                        "team_1_abbreviation": g["team.abbreviation"],
                        "team_2_name": "",
                        "team_2_abbreviation": "",
                        "disable_game": disable_game,
                        "game_start_time": game_time_et.strftime("%Y-%m-%d %I:%M %p ET")
                    }
                else:
                    grouped_games[game_id]["team_2_name"] = g["team.displayName"]
                    grouped_games[game_id]["team_2_abbreviation"] = g["team.abbreviation"]
            except Exception as e:
                print(f"❌ Skipping March Madness game: {g.get('event.date')} - {e}")

    # Remove incomplete matchups and sort games by start time
    games = [game for game in grouped_games.values() if game["team_2_name"]]
    try:
        games = sorted(games, key=lambda x: datetime.strptime(x["event_date"], "%I:%M %p ET"))
    except Exception as e:
        print("❌ Error sorting games:", e)

    # If this is a POST request, save picks
    if request.method == "POST":
        request_data = request.form.to_dict()
        save_picks(selected_games, request_data)

    return render_template(
        "index.html",
        saved=bool(selected_games),
        games=games,
        selected_games=selected_games,
        today_str=date_str,
        sport=sport
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
