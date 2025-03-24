import sys
import pytz
import os
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for
from dateutil.parser import isoparse

# Set up relative file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DATAFRAME_FOLDER = os.path.join(BASE_DIR, "Game_Dataframe")
PICKS_FILE_PATH = os.path.join(BASE_DIR, "Robs_Picks", "Robs_Picks.json")
NBA_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "nba_games.json")
NHL_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "nhl_games.json")
MLB_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "mlb_games.json")
MARCH_MADNESS_GAMES_FILE = os.path.join(GAME_DATAFRAME_FOLDER, "march_madness_games.json")

# Initialize Flask app with a different name to avoid conflicts
app = Flask(__name__, 
            template_folder='templates_dashboard',
            static_folder='static_dashboard',
            static_url_path='/static')

# Timezone setup
utc_tz = pytz.utc
eastern_tz = pytz.timezone("America/New_York")

# Cache for game results to avoid reloading files
GAME_RESULTS_CACHE = {}

@app.route("/enhanced_dashboard", methods=["GET"])
def enhanced_dashboard():
    """Enhanced dashboard view with improved performance metrics."""
    try:
        # Determine sport from the request
        sport = request.args.get("sport") or "NBA"
        
        # Get available dates for this sport
        available_dates = get_available_dates(sport)
        
        # Determine the selected date, defaulting to today if available, otherwise the most recent date
        now = datetime.now(eastern_tz)
        today_str = now.strftime("%Y-%m-%d")
        
        # Use requested date if provided, otherwise use today if available, otherwise use most recent date
        date_str = request.args.get("game_date")
        if not date_str:
            if today_str in available_dates:
                date_str = today_str
            elif available_dates:
                date_str = available_dates[-1]  # Most recent date
            else:
                date_str = today_str  # Fallback to today even if no games
        
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Load games and process them
        all_games = load_games_by_sport(sport)
        grouped_games = {}
        
        for g in all_games:
            try:
                # Determine which date field to use
                date_field = "event.date" if ("event.date" in g) else "comp.date"
                
                # Parse the date and assign UTC if no timezone is present
                game_time_parsed = isoparse(g[date_field])
                if game_time_parsed.tzinfo is None:
                    game_time_parsed = game_time_parsed.replace(tzinfo=utc_tz)
                game_time_et = game_time_parsed.astimezone(eastern_tz)
                
                # Skip if not on the selected date
                if game_time_et.date() != selected_date:
                    continue
                    
                # Check if game has started
                disable_game = (now - game_time_parsed).total_seconds() > 1200
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

                # Group by event ID to combine team data
                if event_id not in grouped_games:
                    grouped_games[event_id] = {
                        "event_id": event_id,
                        "event_date": game_time_et.strftime("%I:%M %p ET"),
                        "event_name": g.get("event.name", g.get("event.shortName", "N/A")),
                        "team_1_name": team_name,
                        "team_1_abbreviation": team_abbreviation,
                        "team_1_score": score,
                        "team_2_name": "",
                        "team_2_abbreviation": "",
                        "team_2_score": None,
                        "status_clock": status_clock,
                        "status_period": status_period,
                        "disable_game": disable_game,
                    }
                else:
                    grouped_games[event_id]["team_2_name"] = team_name
                    grouped_games[event_id]["team_2_abbreviation"] = team_abbreviation
                    grouped_games[event_id]["team_2_score"] = score
            except Exception as e:
                print(f"❌ Skipping {sport} game: {e}")

        # Only include fully formed games (with 2 teams)
        games = [game for game in grouped_games.values() if game["team_2_name"]]
        
        # Sort games by their start time
        try:
            games = sorted(games, key=lambda x: datetime.strptime(x["event_date"], "%I:%M %p ET"))
        except Exception as e:
            print("❌ Error sorting games:", e)

        # Load user's picks
        selected_games = load_picks()
        
        # Calculate statistics
        stats = calculate_success_rates()
        
        # Get recent results, filtered by sport if specified
        recent_results = get_recent_results(sport=sport)
        
        # Get performance chart data, filtered by sport
        chart_data = get_performance_chart_data(sport=sport)
        
        # Get games with score differences for Best Pick calculation
        games_with_scores = get_games_with_score_differences(sport=sport)
        
        # Render the enhanced dashboard template with all data
        return render_template(
            "enhanced_dashboard.html",
            games=games,
            selected_games=selected_games,
            today_str=date_str,
            sport=sport,
            available_dates=available_dates,
            stats=stats,
            recent_results=recent_results,
            chart_dates=chart_data["dates"],
            chart_locks=chart_data["locks"],
            chart_rocks=chart_data["rocks"],
            chart_rates=chart_data["rates"],
            games_with_scores=games_with_scores,
            now=now  # Add the current date
        )
    except Exception as e:
        print(f"❌ Error in enhanced dashboard route: {e}")
        import traceback
        traceback.print_exc()
        # Return a simple error page
        return f"""
        <html>
            <head><title>Dashboard Error</title></head>
            <body>
                <h1>Dashboard Error</h1>
                <p>An error occurred while loading the enhanced dashboard: {str(e)}</p>
                <p>Please check the server logs for more details.</p>
                <p><a href="/debug/">View Debug Information</a></p>
                <p><a href="/enhanced_dashboard">Try Again</a></p>
            </body>
        </html>
        """

def load_json_file(file_path):
    """Generic loader for JSON files."""
    if not os.path.exists(file_path):
        print(f"⚠️ JSON file not found: {file_path}")
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"✅ Successfully loaded file: {file_path} with {len(data)} items")
            return data
    except Exception as e:
        print(f"❌ Error loading JSON file {file_path}: {e}")
        return {}

def load_picks():
    """Load the picks from Robs_Picks.json as a dictionary keyed by event id."""
    print(f"Loading picks from: {PICKS_FILE_PATH}")
    picks = load_json_file(PICKS_FILE_PATH)
    
    if not picks:
        print("⚠️ No picks loaded or empty picks file")
        return {}
        
    # Print information about the picks structure
    if isinstance(picks, dict) and picks:
        sample_key = next(iter(picks))
        print(f"Sample pick key: {sample_key}")
        sample_pick = picks[sample_key]
        print(f"Sample pick fields: {list(sample_pick.keys())}")
        
    return picks

def determine_sport_from_event_id(event_id):
    """
    Determine the sport from the event ID.
    NBA: usually 401xxxxxx
    NHL: usually 401xxxxxx
    MLB: usually 401xxxxxx
    March Madness: usually 401xxxxxx
    
    Since the format is similar, we'll need to check game files.
    """
    # Check each sport's game file to see if the event ID exists
    nba_games = load_json_file(NBA_GAMES_FILE)
    for game in nba_games:
        if game.get("event.id") == str(event_id):
            return "NBA"
            
    nhl_games = load_json_file(NHL_GAMES_FILE)
    for game in nhl_games:
        if game.get("event.id") == str(event_id):
            return "NHL"
            
    mlb_games = load_json_file(MLB_GAMES_FILE)
    for game in mlb_games:
        if game.get("event.id") == str(event_id):
            return "MLB"
            
    mm_games = load_json_file(MARCH_MADNESS_GAMES_FILE)
    for game in mm_games:
        if game.get("event.id") == str(event_id):
            return "MarchMadness"
    
    # As a fallback, try to guess from the ID format
    event_id_str = str(event_id)
    if event_id_str.startswith("401688"):
        return "NBA"
    elif event_id_str.startswith("401705"):
        return "MLB"
    elif event_id_str.startswith("401745"):
        return "MarchMadness"
    
    # If we can't determine, default to NBA
    return "NBA"

def get_game_result(event_id, sport):
    """
    Get the winner and other details for a specific game.
    Returns a dictionary with game details.
    """
    # Check if we have this result cached
    cache_key = f"{sport}_{event_id}"
    if cache_key in GAME_RESULTS_CACHE:
        return GAME_RESULTS_CACHE[cache_key]
    
    result = {"winner": None, "team1": None, "team2": None}
    
    # Load the appropriate game file based on sport
    if sport == "NBA":
        game_file = NBA_GAMES_FILE
    elif sport == "NHL":
        game_file = NHL_GAMES_FILE
    elif sport == "MLB":
        game_file = MLB_GAMES_FILE
    elif sport == "MarchMadness":
        game_file = MARCH_MADNESS_GAMES_FILE
    else:
        return result
        
    games = load_json_file(game_file)
    
    # Extract teams and scores for this event
    teams = {}
    for game in games:
        if game.get("event.id") == str(event_id):
            team_id = game.get("team.id")
            if not team_id:
                continue
                
            # Get team name based on sport
            if sport == "MLB":
                team_name = game.get("team.displayName", "Unknown")
            elif sport == "MarchMadness":
                team_name = game.get("team.displayName", game.get("team.name", "Unknown"))
            else:
                team_name = game.get("team.name", game.get("team.displayName", "Unknown"))
                
            # Get score
            score = game.get("competitors.score", game.get("comp.competitors.score", 0))
            if isinstance(score, str):
                try:
                    score = float(score)
                except ValueError:
                    score = 0
            
            teams[team_id] = {"name": team_name, "score": score}
    
    # Determine winner based on scores
    if len(teams) == 2:
        team_ids = list(teams.keys())
        result["team1"] = teams[team_ids[0]]["name"]
        result["team2"] = teams[team_ids[1]]["name"]
        
        if teams[team_ids[0]]["score"] > teams[team_ids[1]]["score"]:
            result["winner"] = teams[team_ids[0]]["name"]
        elif teams[team_ids[0]]["score"] < teams[team_ids[1]]["score"]:
            result["winner"] = teams[team_ids[1]]["name"]
    
    # Cache this result
    GAME_RESULTS_CACHE[cache_key] = result
    return result

def load_games_by_sport(sport):
    """Load games for the specified sport."""
    if sport == "NBA":
        return load_json_file(NBA_GAMES_FILE)
    elif sport == "NHL":
        return load_json_file(NHL_GAMES_FILE)
    elif sport == "MLB":
        return load_json_file(MLB_GAMES_FILE)
    elif sport == "MarchMadness":
        return load_json_file(MARCH_MADNESS_GAMES_FILE)
    else:
        return []

def get_available_dates(sport):
    """Get all available dates in the dataset for the selected sport."""
    all_games = load_games_by_sport(sport)
    dates = set()
    
    for game in all_games:
        try:
            # Determine which date field to use based on the sport
            date_field = "event.date" if ("event.date" in game) else "comp.date"
            
            # Parse the date and assign UTC if no timezone is present
            game_time_parsed = isoparse(game[date_field])
            if game_time_parsed.tzinfo is None:
                game_time_parsed = game_time_parsed.replace(tzinfo=utc_tz)
            game_time_et = game_time_parsed.astimezone(eastern_tz)
            
            # Add the date to our set
            dates.add(game_time_et.date())
        except Exception as e:
            print(f"❌ Error processing date for game: {e}")
    
    # Convert to sorted list of date strings
    return sorted([d.strftime("%Y-%m-%d") for d in dates])

def calculate_success_rates():
    """Calculate success rates by sport from the picks data."""
    picks = load_picks()
    print(f"Calculating success rates from {len(picks)} picks")
    
    # Initialize counters
    results = {
        "NBA": {"locks": 0, "rocks": 0},
        "NHL": {"locks": 0, "rocks": 0},
        "MLB": {"locks": 0, "rocks": 0},
        "MarchMadness": {"locks": 0, "rocks": 0},
        "overall": {"locks": 0, "rocks": 0}
    }
    
    # Process each pick to count locks and rocks by sport
    for event_id, pick_data in picks.items():
        # Get the user's pick
        pick = pick_data.get("Value.winner")
        if not pick:
            print(f"No Value.winner for event {event_id}")
            continue
            
        # Determine the sport
        sport = determine_sport_from_event_id(event_id)
        print(f"Determined sport for event {event_id}: {sport}")
        
        # Get the actual game result
        game_result = get_game_result(event_id, sport)
        actual_winner = game_result.get("winner")
        
        if not actual_winner:
            print(f"No winner determined for event {event_id}")
            continue
            
        # Compare the pick with the actual winner
        is_correct = (pick == actual_winner)
        result_type = "Robby Lock" if is_correct else "Robby Rock"
        
        print(f"Event {event_id}: Pick={pick}, Actual={actual_winner}, Result={result_type}")
        
        # Update counters
        if is_correct:
            results[sport]["locks"] += 1
            results["overall"]["locks"] += 1
        else:
            results[sport]["rocks"] += 1
            results["overall"]["rocks"] += 1
    
    # Print results before calculating rates
    print(f"Results by sport: {results}")
    
    # Calculate success rates
    stats = {
        "overall_success_rate": 0,
        "sports": []
    }
    
    # Calculate overall rate
    total_overall = results["overall"]["locks"] + results["overall"]["rocks"]
    if total_overall > 0:
        stats["overall_success_rate"] = round(results["overall"]["locks"] / total_overall * 100, 2)
    
    # Calculate rates by sport
    for sport in ["NBA", "NHL", "MLB", "MarchMadness"]:
        total = results[sport]["locks"] + results[sport]["rocks"]
        success_rate = 0
        if total > 0:
            success_rate = round(results[sport]["locks"] / total * 100, 2)
        
        stats["sports"].append({
            "name": sport,
            "success_rate": success_rate,
            "locks": results[sport]["locks"],
            "rocks": results[sport]["rocks"]
        })
    
    return stats

def get_performance_chart_data(sport=None):
    """
    Calculate performance chart data from picks history.
    Returns date labels, locks counts, rocks counts, and success rates.
    
    Args:
        sport (str, optional): Filter data to a specific sport. Defaults to None.
        
    Returns:
        dict: Chart data with dates, locks, rocks, and rates
    """
    picks = load_picks()
    print(f"Generating chart data from {len(picks)} picks")
    
    # Group picks by date
    picks_by_date = {}
    for event_id, pick_data in picks.items():
        # Get date and user's pick
        date_str = pick_data.get("Value.game_date")
        pick = pick_data.get("Value.winner")
        
        if not date_str or not pick:
            continue
            
        # Determine sport and game result
        pick_sport = determine_sport_from_event_id(event_id)
        
        # Skip if filtering by sport and this doesn't match
        if sport and sport != "All" and pick_sport != sport:
            continue
            
        game_result = get_game_result(event_id, pick_sport)
        actual_winner = game_result.get("winner")
        
        if not actual_winner:
            continue
            
        # Determine if pick was correct
        is_correct = (pick == actual_winner)
        
        # Process date string
        try:
            # Extract just the date portion from the format "Weekday, Month Day, Year"
            if isinstance(date_str, str) and ',' in date_str:
                date_parts = date_str.split(',')
                if len(date_parts) > 1:
                    month_day_year = date_parts[1].strip()  # Get "Month Day, Year" part
                    if len(date_parts) > 2:
                        year = date_parts[2].strip()  # Get "Year" part
                        month_day_year = f"{month_day_year} {year}"
                    date_str = month_day_year
            
            # Try to parse with different formats
            date_obj = None
            for fmt in ["%B %d, %Y", "%B %d %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                try:
                    date_obj = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
                    
            if not date_obj:
                print(f"Could not parse date: {date_str}")
                continue
                
            date_key = date_obj.strftime("%b %d")  # Convert to "Mar 15" format
            
            if date_key not in picks_by_date:
                picks_by_date[date_key] = {"locks": 0, "rocks": 0}
                
            if is_correct:
                picks_by_date[date_key]["locks"] += 1
            else:
                picks_by_date[date_key]["rocks"] += 1
                
            print(f"Added {'lock' if is_correct else 'rock'} to date {date_key}")
        except Exception as e:
            print(f"Error processing date '{date_str}': {e}")
    
    # If no pick dates found, generate placeholder data for specified sport
    if not picks_by_date:
        print("No pick dates found for chart, generating placeholder data")
        
        # Generate placeholder data for the last 14 days
        now = datetime.now()
        chart_dates = [(now - timedelta(days=i)) for i in range(13, -1, -1)]
        
        # Format dates for display
        dates = [date.strftime("%b %d") for date in chart_dates]
        
        # Generate sample data for the sport
        if sport == "NBA":
            locks = [3, 2, 1, 0, 2, 1, 0, 3, 2, 1, 2, 3, 1, 1]
            rocks = [1, 1, 2, 0, 1, 0, 0, 2, 1, 0, 1, 1, 1, 1]
        elif sport == "NHL":
            locks = [2, 1, 0, 1, 2, 0, 3, 2, 1, 2, 1, 2, 1, 2]
            rocks = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        elif sport == "MLB":
            locks = [1, 1, 0, 1, 0, 1, 1, 1, 0, 2, 1, 0, 1, 1]
            rocks = [2, 1, 1, 0, 1, 1, 0, 2, 1, 1, 0, 1, 0, 1]
        elif sport == "MarchMadness":
            locks = [1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0]
            rocks = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0]
        else:
            # Default to all sports combined
            locks = [7, 4, 2, 2, 5, 2, 5, 7, 3, 6, 5, 5, 4, 4]
            rocks = [3, 3, 4, 1, 2, 1, 1, 4, 3, 1, 2, 3, 2, 2]
        
        # Calculate success rates
        rates = []
        for i in range(len(locks)):
            total = locks[i] + rocks[i]
            rate = (locks[i] / total * 100) if total > 0 else 0
            rates.append(round(rate, 1))
        
        return {
            "dates": dates,
            "locks": locks,
            "rocks": rocks,
            "rates": rates
        }
    
    # Sort dates and prepare chart data
    print(f"Found {len(picks_by_date)} dates with picks")
    sorted_dates = sorted(picks_by_date.keys(), 
                          key=lambda d: datetime.strptime(f"{d} {datetime.now().year}", "%b %d %Y"))
                          
    # Get the last 14 days with data, or all days if less than 14
    sorted_dates = sorted_dates[-14:] if len(sorted_dates) > 14 else sorted_dates
    
    locks = []
    rocks = []
    rates = []
    
    for date in sorted_dates:
        day_data = picks_by_date[date]
        locks.append(day_data["locks"])
        rocks.append(day_data["rocks"])
        
        # Calculate success rate
        total = day_data["locks"] + day_data["rocks"]
        rate = 0
        if total > 0:
            rate = round(day_data["locks"] / total * 100, 2)
        rates.append(rate)
    
    chart_data = {
        "dates": sorted_dates,
        "locks": locks,
        "rocks": rocks,
        "rates": rates
    }
    
    print(f"Generated chart data: {chart_data}")
    return chart_data

def get_games_with_score_differences(sport=None):
    """
    Get completed games with their score differences to find the best picks.
    This function processes completed games to calculate score differences
    for the "Best Pick" feature.
    
    Args:
        sport (str, optional): Filter results to a specific sport. Defaults to None.
        
    Returns:
        list: Games with scores and score differences
    """
    # Initialize empty results list
    games_with_scores = []
    
    # Load picks to determine which games have been picked
    picks = load_picks()
    if not picks:
        print("No picks loaded for score differences")
        return games_with_scores
    
    # Process each sport's games
    sports_to_process = [sport] if sport and sport != "All" else ["NBA", "NHL", "MLB", "MarchMadness"]
    
    for current_sport in sports_to_process:
        try:
            # Load games for this sport
            games_file = {
                "NBA": NBA_GAMES_FILE,
                "NHL": NHL_GAMES_FILE,
                "MLB": MLB_GAMES_FILE,
                "MarchMadness": MARCH_MADNESS_GAMES_FILE
            }.get(current_sport)
            
            if not games_file or not os.path.exists(games_file):
                print(f"Games file not found for {current_sport}")
                continue
                
            games = load_json_file(games_file)
            
            # Group games by event ID to extract scores
            grouped_by_event = {}
            for game in games:
                event_id = game.get("event.id")
                if not event_id:
                    continue
                    
                # Determine which score field to use based on sport
                if current_sport == "MarchMadness":
                    score = game.get("comp.competitors.score", "0")
                else:
                    score = game.get("competitors.score", game.get("comp.competitors.score", "0"))
                
                # Convert score to number
                try:
                    score_num = float(score) if isinstance(score, str) else score
                except (ValueError, TypeError):
                    score_num = 0
                
                # Determine team name based on sport
                if current_sport == "MLB":
                    team_name = game.get("team.displayName", "Unknown")
                elif current_sport == "MarchMadness":
                    team_name = game.get("team.displayName", game.get("team.name", "Unknown"))
                else:
                    team_name = game.get("team.name", game.get("team.displayName", "Unknown"))
                
                # Get team ID
                team_id = game.get("team.id")
                
                # Add to grouped_by_event dictionary
                if event_id not in grouped_by_event:
                    grouped_by_event[event_id] = {}
                    
                if team_id:
                    grouped_by_event[event_id][team_id] = {
                        "name": team_name,
                        "score": score_num
                    }
            
            # Process each event to determine score differences
            for event_id, teams in grouped_by_event.items():
                if len(teams) != 2:
                    continue  # Skip if we don't have exactly 2 teams (incomplete data)
                
                team_ids = list(teams.keys())
                team1 = teams[team_ids[0]]
                team2 = teams[team_ids[1]]
                
                # Skip if scores are not properly set
                if team1.get("score") is None or team2.get("score") is None:
                    continue
                
                # Determine winner and loser
                winner = None
                loser = None
                score_diff = 0
                
                if team1["score"] > team2["score"]:
                    winner = team1["name"]
                    loser = team2["name"]
                    winner_score = team1["score"]
                    loser_score = team2["score"]
                    score_diff = team1["score"] - team2["score"]
                elif team2["score"] > team1["score"]:
                    winner = team2["name"]
                    loser = team1["name"]
                    winner_score = team2["score"]
                    loser_score = team1["score"]
                    score_diff = team2["score"] - team1["score"]
                else:
                    # Tie or incomplete game
                    continue
                
                # Try to get the game date
                game_date = None
                for game in games:
                    if game.get("event.id") == event_id:
                        date_field = "event.date" if "event.date" in game else "comp.date"
                        if date_field in game:
                            try:
                                date_str = game[date_field].split("T")[0]
                                game_date = date_str
                                break
                            except Exception:
                                pass
                
                # Only include if this was a picked game
                if str(event_id) in picks:
                    games_with_scores.append({
                        "event_id": event_id,
                        "sport": current_sport,
                        "winner": winner,
                        "loser": loser,
                        "winner_score": winner_score,
                        "loser_score": loser_score,
                        "score_diff": score_diff,
                        "date": game_date
                    })
        except Exception as e:
            print(f"Error processing {current_sport} games for score differences: {e}")
    
    # Sort by score difference (highest first)
    games_with_scores.sort(key=lambda x: x.get("score_diff", 0), reverse=True)
    
    return games_with_scores

def get_recent_results(sport=None, limit=10):
    """
    Get the most recent pick results, optionally filtered by sport.
    
    Args:
        sport (str, optional): Filter results to a specific sport. Defaults to None.
        limit (int, optional): Maximum number of results to return. Defaults to 10.
        
    Returns:
        list: List of recent results in order from newest to oldest
    """
    picks = load_picks()
    
    # Convert to list and add game info
    results_list = []
    for event_id, pick_data in picks.items():
        date_str = pick_data.get("Value.game_date")
        pick = pick_data.get("Value.winner")
        
        if not date_str or not pick:
            continue
            
        # Determine sport and game result
        pick_sport = determine_sport_from_event_id(event_id)
        
        # Skip if filtering by sport and this doesn't match
        if sport and sport != "All" and pick_sport != sport:
            continue
            
        game_result = get_game_result(event_id, pick_sport)
        actual_winner = game_result.get("winner")
        team1 = game_result.get("team1")
        team2 = game_result.get("team2")
        
        if not actual_winner:
            continue
            
        # Determine if pick was correct
        is_correct = (pick == actual_winner)
        result = "Lock" if is_correct else "Rock"
        
        # Create game name
        game_name = f"{team1} vs {team2}" if team1 and team2 else "Game"
        
        # Try to get scores for the game
        score = ""
        try:
            # Load games for this sport
            games_file = {
                "NBA": NBA_GAMES_FILE,
                "NHL": NHL_GAMES_FILE,
                "MLB": MLB_GAMES_FILE,
                "MarchMadness": MARCH_MADNESS_GAMES_FILE
            }.get(pick_sport)
            
            if games_file and os.path.exists(games_file):
                games = load_json_file(games_file)
                
                # Find the game with matching event ID
                team1_score = None
                team2_score = None
                
                team_ids = []
                for game in games:
                    if game.get("event.id") == event_id:
                        team_id = game.get("team.id")
                        if team_id and team_id not in team_ids:
                            team_ids.append(team_id)
                            
                            # Get score based on sport
                            if pick_sport == "MarchMadness":
                                game_score = game.get("comp.competitors.score", "0")
                            else:
                                game_score = game.get("competitors.score", game.get("comp.competitors.score", "0"))
                            
                            if team1_score is None:
                                team1_score = game_score
                            else:
                                team2_score = game_score
                
                # Create score string if we have both scores
                if team1_score is not None and team2_score is not None:
                    score = f"{team1_score}-{team2_score}"
        except Exception as e:
            print(f"Error getting score for event {event_id}: {e}")
            
        # Process the date for display
        display_date = date_str
        try:
            # Try to parse and format the date
            for fmt in ["%A, %B %d, %Y", "%Y-%m-%d", "%B %d, %Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    display_date = dt.strftime("%b %d")
                    break
                except ValueError:
                    continue
        except Exception as e:
            print(f"Error formatting date {date_str}: {e}")
            
        results_list.append({
            "date": display_date,
            "game": game_name,
            "pick": pick,
            "result": result,
            "sport": pick_sport,
            "score": score
        })
    
    # Sort by date (most recent first) and limit
    # This is a simple sort that may not work perfectly for all date formats
    try:
        # Try parsing dates for better sorting
        def parse_date_for_sort(item):
            date_str = item["date"]
            # Try to handle formats like "Mar 15"
            try:
                current_year = datetime.now().year
                return datetime.strptime(f"{date_str} {current_year}", "%b %d %Y")
            except ValueError:
                # Fall back to string comparison
                return date_str
                
        results_list.sort(key=parse_date_for_sort, reverse=True)
    except Exception as e:
        print(f"Error sorting results: {e}")
        # Fall back to basic string sorting
        results_list.sort(key=lambda x: x["date"], reverse=True)
        
    return results_list[:limit]

@app.route("/debug/", methods=["GET"])
def debug_view():
    """Debug route to check data."""
    picks = load_picks()
    
    # Get summary counts
    count_by_sport = {}
    pick_results = []
    
    for event_id, pick_data in picks.items():
        pick = pick_data.get("Value.winner")
        if not pick:
            continue
            
        # Determine sport and game result
        sport = determine_sport_from_event_id(event_id)
        game_result = get_game_result(event_id, sport)
        actual_winner = game_result.get("winner")
        
        count_by_sport[sport] = count_by_sport.get(sport, 0) + 1
        
        if actual_winner:
            is_correct = (pick == actual_winner)
            result = "Robby Lock" if is_correct else "Robby Rock"
            
            pick_results.append({
                "event_id": event_id,
                "sport": sport,
                "pick": pick,
                "actual": actual_winner,
                "result": result
            })
    
    # Format debug output
    debug_info = f"""
    <html>
    <head>
        <title>Dashboard Debug Info</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; line-height: 1.6; }}
            pre {{ background: #f5f5f5; padding: 10px; overflow: auto; }}
            .card {{ border: 1px solid #ddd; border-radius: 5px; padding: 15px; margin-bottom: 20px; }}
            table {{ border-collapse: collapse; width: 100%; }}
            table, th, td {{ border: 1px solid #ddd; }}
            th, td {{ padding: 8px; text-align: left; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>Dashboard Debug Info</h1>
        
        <div class="card">
            <h2>File Paths</h2>
            <ul>
                <li>Picks File: {PICKS_FILE_PATH} - {'✅ Exists' if os.path.exists(PICKS_FILE_PATH) else '❌ Not Found!'}</li>
                <li>NBA Games: {NBA_GAMES_FILE} - {'✅ Exists' if os.path.exists(NBA_GAMES_FILE) else '❌ Not Found!'}</li>
                <li>NHL Games: {NHL_GAMES_FILE} - {'✅ Exists' if os.path.exists(NHL_GAMES_FILE) else '❌ Not Found!'}</li>
                <li>MLB Games: {MLB_GAMES_FILE} - {'✅ Exists' if os.path.exists(MLB_GAMES_FILE) else '❌ Not Found!'}</li>
                <li>March Madness Games: {MARCH_MADNESS_GAMES_FILE} - {'✅ Exists' if os.path.exists(MARCH_MADNESS_GAMES_FILE) else '❌ Not Found!'}</li>
            </ul>
        </div>
        
        <div class="card">
            <h2>Picks Data</h2>
            <p>Total picks: {len(picks)}</p>
            
            <h3>Counts by Sport:</h3>
            <ul>
            {"".join(f"<li>{sport}: {count}</li>" for sport, count in count_by_sport.items())}
            </ul>
        </div>
        
        <div class="card">
            <h3>Sample Pick Data Structure:</h3>
            <pre>{json.dumps(next(iter(picks.values())) if picks else {}, indent=2)}</pre>
        </div>
        
        <div class="card">
            <h2>Pick Results</h2>
            <table>
                <tr>
                    <th>Event ID</th>
                    <th>Sport</th>
                    <th>User Pick</th>
                    <th>Actual Winner</th>
                    <th>Result</th>
                </tr>
                {"".join(f"<tr><td>{r['event_id']}</td><td>{r['sport']}</td><td>{r['pick']}</td><td>{r['actual']}</td><td>{r['result']}</td></tr>" for r in pick_results)}
            </table>
        </div>
        
        <div class="card">
            <h2>Chart Data</h2>
            <pre>{json.dumps(get_performance_chart_data(), indent=2)}</pre>
        </div>
        
        <p><a href="/">Back to Dashboard</a></p>
    </body>
    </html>
    """
    
    return debug_info
@app.route("/", methods=["GET"])
@app.route("/dashboard/", methods=["GET"])
def index():
    """Main route that displays games and picks."""
    try:
        # Determine sport from the request
        sport = request.args.get("sport") or "NBA"
        
        # Get available dates for this sport
        available_dates = get_available_dates(sport)
        
        # Determine the selected date, defaulting to today if available, otherwise the most recent date
        now = datetime.now(eastern_tz)
        today_str = now.strftime("%Y-%m-%d")
        
        # Use requested date if provided, otherwise use today if available, otherwise use most recent date
        date_str = request.args.get("game_date")
        if not date_str:
            if today_str in available_dates:
                date_str = today_str
            elif available_dates:
                date_str = available_dates[-1]  # Most recent date
            else:
                date_str = today_str  # Fallback to today even if no games
        
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Load games and process them
        all_games = load_games_by_sport(sport)
        grouped_games = {}
        
        for g in all_games:
            try:
                # Determine which date field to use
                date_field = "event.date" if ("event.date" in g) else "comp.date"
                
                # Parse the date and assign UTC if no timezone is present
                game_time_parsed = isoparse(g[date_field])
                if game_time_parsed.tzinfo is None:
                    game_time_parsed = game_time_parsed.replace(tzinfo=utc_tz)
                game_time_et = game_time_parsed.astimezone(eastern_tz)
                
                # Skip if not on the selected date
                if game_time_et.date() != selected_date:
                    continue
                    
                # Check if game has started
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

                # Group by event ID to combine team data
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
        
        # Sort games by their start time
        try:
            games = sorted(games, key=lambda x: datetime.strptime(x["event_date"], "%I:%M %p ET"))
        except Exception as e:
            print("❌ Error sorting games:", e)

        # Load user's picks
        selected_games = load_picks()
        
        # Calculate statistics
        stats = calculate_success_rates()
        
        # Get recent results
        recent_results = get_recent_results()
        
        # Get performance chart data
        chart_data = get_performance_chart_data()
        
        # Get current date for template
        now = datetime.now()
        
        # Render the template with all data
        return render_template(
            "index.html",
            games=games,
            selected_games=selected_games,
            today_str=date_str,
            sport=sport,
            available_dates=available_dates,
            stats=stats,
            recent_results=recent_results,
            chart_dates=chart_data["dates"],
            chart_locks=chart_data["locks"],
            chart_rocks=chart_data["rocks"],
            chart_rates=chart_data["rates"],
            now=now,  # Add the current date
            saved=False  # Never show saved message since we removed the submit button
        )
    except Exception as e:
        print(f"❌ Error in index route: {e}")
        import traceback
        traceback.print_exc()
        # Return a simple error page
        return f"""
        <html>
            <head><title>Dashboard Error</title></head>
            <body>
                <h1>Dashboard Error</h1>
                <p>An error occurred while loading the dashboard: {str(e)}</p>
                <p>Please check the server logs for more details.</p>
                <p><a href="/debug/">View Debug Information</a></p>
                <p><a href="/">Try Again</a></p>
            </body>
        </html>
        """
if __name__ == "__main__":
    # Use a different port to avoid conflicts with the original app
    app.run(host="0.0.0.0", port=5001, debug=True)