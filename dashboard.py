import json
import os
from datetime import datetime
from flask import Blueprint, render_template, jsonify, current_app

# Create a blueprint instead of a separate Flask app.
dashboard_bp = Blueprint('dashboard', __name__, template_folder="templates_dashboard")

def load_json(filepath):
    # Build the full path relative to the application's root folder.
    full_path = os.path.join(current_app.root_path, filepath)
    if not os.path.exists(full_path):
        print(f"File not found: {full_path}")
        return []
    try:
        with open(full_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {full_path}: {e}")
        return []

def gather_all_games(march_madness, mlb_games, nba_games, nhl_games):
    games_dict = {}

    def process_list(games):
        if isinstance(games, dict):
            games = [games]
        for record in games:
            event_id = record.get("event.id")
            if not event_id:
                continue
            if event_id not in games_dict:
                games_dict[event_id] = {
                    "event.id": event_id,
                    "event.name": record.get("event.name", record.get("event.shortName", "N/A")),
                    "event.date": record.get("event.date", ""),
                    "competitors": []
                }
            score_str = record.get("comp.competitors.score") or record.get("competitors.score", "0")
            try:
                score = int(score_str)
            except:
                score = 0
            team_name = record.get("team.displayName") or record.get("team.name", "Unknown Team")
            games_dict[event_id]["competitors"].append({
                "score": score,
                "team_name": team_name
            })
    process_list(march_madness)
    process_list(mlb_games)
    process_list(nba_games)
    process_list(nhl_games)

    for eid, game in games_dict.items():
        comps = game["competitors"]
        if len(comps) == 2:
            game["combined_score"] = f"{comps[0]['score']}-{comps[1]['score']}"
            game["combined_teams"] = [comps[0]["team_name"], comps[1]["team_name"]]
    return games_dict

def get_game_start_datetime(pick):
    time_str = pick.get("Value.game_start_time", "").strip()
    date_str = pick.get("Value.game_date", "").strip()
    if not time_str or time_str.lower() == "n/a":
        return None
    parts = time_str.split()
    if len(parts) >= 2:
        time_str = parts[0] + " " + parts[1]
    datetime_str = f"{date_str} {time_str}"
    try:
        return datetime.strptime(datetime_str, "%A, %B %d, %Y %I:%M %p")
    except Exception as e:
        print("Error parsing game start datetime:", e)
        return None

def get_pick_date(pick):
    game_date = pick.get("Value.game_date", "")
    try:
        return datetime.strptime(game_date, "%A, %B %d, %Y").date()
    except Exception as e:
        print("Error parsing pick date:", e)
        return None

def determine_pick_result(pick, game):
    if not game or "combined_score" not in game:
        return "pending"
    picked_winner = pick.get("Value.winner", "").lower()
    scores_str = game["combined_score"].split("-")
    if len(scores_str) != 2:
        return "pending"
    try:
        score1 = int(scores_str[0].strip())
        score2 = int(scores_str[1].strip())
    except:
        return "pending"
    pick_date = get_pick_date(pick)
    current_date = datetime.now().date()
    if pick_date == current_date and score1 == 0 and score2 == 0:
        return "pending"
    if score1 == score2:
        if pick_date < current_date:
            return "tie"
        else:
            return "pending"
    if "combined_teams" not in game or len(game["combined_teams"]) != 2:
        return "pending"
    team1, team2 = game["combined_teams"]
    actual_winner = team1.lower() if score1 > score2 else team2.lower()
    return "win" if picked_winner in actual_winner else "loss"

@dashboard_bp.route("/dashboard")
def dashboard():
    # Load JSON files (paths are relative to the app's root folder)
    march_madness = load_json(os.path.join("Game_Dataframe", "march_madness_games.json"))
    mlb_games = load_json(os.path.join("Game_Dataframe", "mlb_games.json"))
    nba_games = load_json(os.path.join("Game_Dataframe", "nba_games.json"))
    nhl_games = load_json(os.path.join("Game_Dataframe", "nhl_games.json"))
    robs_picks = load_json(os.path.join("Robs_Picks", "Robs_Picks.json"))

    all_games = gather_all_games(march_madness, mlb_games, nba_games, nhl_games)
    correlated_picks = []
    win_count = 0
    loss_count = 0
    tie_count = 0
    pending_count = 0
    daily_stats = {}

    if isinstance(robs_picks, dict):
        for event_id, pick_data in robs_picks.items():
            game = all_games.get(event_id, {})
            result = determine_pick_result(pick_data, game)
            if result == "win":
                win_count += 1
            elif result == "loss":
                loss_count += 1
            elif result == "tie":
                tie_count += 1
            else:
                pending_count += 1

            game_date = get_pick_date(pick_data)
            if game_date and result in ["win", "loss", "tie"]:
                day_key = game_date.strftime("%Y-%m-%d")
                if day_key not in daily_stats:
                    daily_stats[day_key] = {"wins": 0, "losses": 0, "ties": 0, "total": 0}
                daily_stats[day_key]["total"] += 1
                if result == "win":
                    daily_stats[day_key]["wins"] += 1
                elif result == "loss":
                    daily_stats[day_key]["losses"] += 1
                elif result == "tie":
                    daily_stats[day_key]["ties"] += 1

            display_date = pick_data.get("Value.game_date", "N/A")
            correlated_picks.append({
                "event_id": event_id,
                "event_name": game.get("event.name", game.get("event.shortName", "N/A")),
                "event_date": display_date,
                "pick_winner": pick_data.get("Value.winner", "N/A"),
                "result": result,
                "game_date": game_date,
                "matching_game_data": game
            })

    correlated_picks.sort(key=lambda x: x["game_date"] if x["game_date"] else datetime.min.date(), reverse=True)
    total_decided = win_count + loss_count
    win_percentage = (win_count / total_decided * 100) if total_decided > 0 else 0

    daily_data = []
    for day, stats in sorted(daily_stats.items()):
        decided = stats["wins"] + stats["losses"]
        win_pct = (stats["wins"] / decided * 100) if decided > 0 else 0
        daily_data.append({
            "day": day,
            "win_percentage": round(win_pct, 1),
            "wins": stats["wins"],
            "losses": stats["losses"],
            "ties": stats["ties"],
            "total": stats["total"]
        })
    return render_template("dashboard.html",
                           march_madness=march_madness,
                           mlb_games=mlb_games,
                           nba_games=nba_games,
                           nhl_games=nhl_games,
                           robs_picks=robs_picks,
                           correlated_picks=correlated_picks,
                           win_count=win_count,
                           loss_count=loss_count,
                           tie_count=tie_count,
                           pending_count=pending_count,
                           win_percentage=round(win_percentage, 1),
                           daily_data=daily_data,
                           current_time=datetime.now().strftime("%Y-%m-%d %H:%M"))

@dashboard_bp.route("/api/monthly_stats")
def monthly_stats_api():
    return jsonify([])

# Allow running dashboard.py by itself for testing:
if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__, template_folder="templates_dashboard")
    app.register_blueprint(dashboard_bp)
    app.run(debug=True)
