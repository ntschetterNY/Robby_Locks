# Import necessary libraries
from flask import render_template, redirect, url_for, request, current_app
from datetime import datetime, timedelta
import pytz
import json
import os
import logging
from collections import defaultdict
import hashlib
from dateutil.parser import isoparse

# Set up logger
logger = logging.getLogger('dashboard.integration')

def setup_enhanced_dashboard(app, dashboard_module):
    """
    Sets up the enhanced dashboard routes and functionality with dynamic data
    
    Args:
        app: Flask application instance
        dashboard_module: Module containing dashboard functionality
    """
    
    # Create a timezone-aware datetime object for "now"
    eastern_tz = pytz.timezone("America/New_York")
    utc_tz = pytz.utc
    
    # Define file paths based on the current directory
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    GAME_DATAFRAME_FOLDER = os.path.join(BASE_DIR, "Game_Dataframe")
    PICKS_FILE_PATH = os.path.join(BASE_DIR, "Robs_Picks", "Robs_Picks.json")
    
    # Game files paths by sport
    GAME_FILES = {
        "NBA": os.path.join(GAME_DATAFRAME_FOLDER, "nba_games.json"),
        "NHL": os.path.join(GAME_DATAFRAME_FOLDER, "nhl_games.json"),
        "MLB": os.path.join(GAME_DATAFRAME_FOLDER, "mlb_games.json"),
        "MarchMadness": os.path.join(GAME_DATAFRAME_FOLDER, "march_madness_games.json")
    }
    
    # Cache for game results
    GAME_RESULTS_CACHE = {}
    
    @app.route("/dashboard")
    def enhanced_dashboard():
        """Enhanced dashboard view with performance metrics."""
        now = datetime.now(eastern_tz)
        
        # Get query parameters for filtering
        sport = request.args.get("sport", "NBA")  # Default to NBA
        
        # Get available dates for this sport
        available_dates = get_available_dates(sport)
        
        # Determine the selected date
        today_str = now.strftime("%Y-%m-%d")
        
        # Use requested date if provided, otherwise use today if available, otherwise use most recent date
        game_date = request.args.get("game_date")
        if not game_date:
            if today_str in available_dates:
                game_date = today_str
            elif available_dates:
                game_date = available_dates[-1]  # Most recent date
            else:
                game_date = today_str  # Fallback to today even if no games
        
        # Load picks data
        selected_games = load_picks()
        
        # Load games for the specified date and sport
        games = load_games_for_date(sport, game_date, now)
        
        # Calculate statistics
        stats = calculate_success_rates(sport)
        
        # Get chart data
        chart_data = get_performance_chart_data(sport)
        
        # Get recent results, filtered by sport if specified
        recent_results = get_recent_results(sport)
        
        # Get games with score differences for Best Pick calculation
        games_with_scores = get_games_with_score_differences(sport)
        
        return render_template(
            "enhanced_dashboard.html",  # This template should be in templates_dashboard folder
            now=now,
            sport=sport,
            games=games,
            selected_games=selected_games,
            available_dates=available_dates,
            today_str=game_date,
            stats=stats,
            chart_dates=json.dumps(chart_data["dates"]),
            chart_locks=json.dumps(chart_data["locks"]),
            chart_rocks=json.dumps(chart_data["rocks"]),
            chart_rates=json.dumps(chart_data["rates"]),
            recent_results=recent_results,
            games_with_scores=games_with_scores
        )
    
    def load_json_file(file_path):
        """Generic loader for JSON files."""
        if not os.path.exists(file_path):
            print(f"⚠️ JSON file not found: {file_path}")
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"✅ Successfully loaded file: {file_path} with {len(data)} items")
                return data
        except Exception as e:
            print(f"❌ Error loading JSON file {file_path}: {e}")
            return []
    
    def load_picks():
        """Load the picks from Robs_Picks.json as a dictionary keyed by event id."""
        print(f"Loading picks from: {PICKS_FILE_PATH}")
        try:
            if os.path.exists(PICKS_FILE_PATH):
                with open(PICKS_FILE_PATH, "r", encoding="utf-8") as f:
                    picks = json.load(f)
                    print(f"✅ Successfully loaded picks: {len(picks)} picks found")
                    return picks
        except Exception as e:
            print(f"❌ Error loading picks: {e}")
        
        print("⚠️ No picks loaded or empty picks file")
        return {}
    
    def get_available_dates(sport):
        """Get all available dates in the dataset for the selected sport."""
        all_games = load_games_by_sport(sport)
        dates = set()
        
        for game in all_games:
            try:
                # Determine which date field to use
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
    
    def load_games_by_sport(sport):
        """Load games for the specified sport."""
        game_file = GAME_FILES.get(sport)
        if not game_file:
            print(f"⚠️ No game file defined for sport: {sport}")
            return []
            
        return load_json_file(game_file)
    
    def load_games_for_date(sport, date_str, now):
        """Load games for the specified sport and date."""
        all_games = load_games_by_sport(sport)
        games = []
        
        # Convert date_str to datetime object
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ Invalid date format: {date_str}")
            return games
        
        # Group games by event ID
        grouped_games = {}
        
        for game in all_games:
            try:
                # Determine which date field to use
                date_field = "event.date" if "event.date" in game else "comp.date"
                
                # Skip if the date field is missing
                if date_field not in game:
                    continue
                
                # Parse the date and assign UTC if no timezone is present
                game_time_parsed = isoparse(game[date_field])
                if game_time_parsed.tzinfo is None:
                    game_time_parsed = game_time_parsed.replace(tzinfo=utc_tz)
                game_time_et = game_time_parsed.astimezone(eastern_tz)
                
                # Skip if not on the selected date
                if game_time_et.date() != selected_date:
                    continue
                
                # Check if game has started
                disable_game = (now - game_time_parsed).total_seconds() > 1200
                
                # Get event ID
                event_id = game.get("event.id")
                if not event_id:
                    continue
                
                # Determine team details based on sport
                if sport == "MLB":
                    team_name = game.get("team.displayName", "N/A")
                    team_abbreviation = game.get("team.abbreviation", "N/A")
                elif sport == "MarchMadness":
                    team_name = game.get("team.displayName", game.get("team.name", "N/A"))
                    team_abbreviation = game.get("team.abbreviation", "N/A")
                else:
                    team_name = game.get("team.name", game.get("team.displayName", "N/A"))
                    team_abbreviation = game.get("team.abbreviation", "N/A")
                
                # Determine score and status fields based on sport
                if sport == "MarchMadness":
                    score = game.get("comp.competitors.score", "0")
                    status_clock = game.get("comp.status.displayClock", "N/A")
                    status_period = game.get("comp.status.period", "N/A")
                else:
                    score = game.get("competitors.score", game.get("comp.competitors.score", "0"))
                    status_clock = game.get("status.clock", game.get("comp.status.displayClock", "N/A"))
                    status_period = game.get("status.period", game.get("comp.status.period", "N/A"))
                
                # Group by event ID to combine team data
                if event_id not in grouped_games:
                    grouped_games[event_id] = {
                        "event_id": event_id,
                        "event_date": game_time_et.strftime("%I:%M %p ET"),
                        "event_name": game.get("event.name", game.get("event.shortName", "N/A")),
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
            print(f"❌ Error sorting games: {e}")
        
        return games
    
    def determine_sport_from_event_id(event_id):
        """Determine the sport from the event ID by checking game files."""
        event_id_str = str(event_id)
        
        # Check each sport's game file to see if the event ID exists
        for sport, game_file in GAME_FILES.items():
            if not os.path.exists(game_file):
                continue
                
            try:
                with open(game_file, "r", encoding="utf-8") as f:
                    games = json.load(f)
                    for game in games:
                        if game.get("event.id") == event_id_str:
                            return sport
            except Exception:
                continue
        
        # If we can't determine, try to guess from the ID format
        if event_id_str.startswith("401688"):
            return "NBA"
        elif event_id_str.startswith("401705"):
            return "MLB"
        elif event_id_str.startswith("401745"):
            return "MarchMadness"
        elif event_id_str.startswith("401"):  # Generic ESPN event ID
            return "NHL"  # Default to NHL for other 401 IDs
        
        # Default to NBA if we can't determine
        return "NBA"
    
    def get_game_result(event_id, sport):
        """Get the winner and other details for a specific game."""
        # Check if we have this result cached
        cache_key = f"{sport}_{event_id}"
        if cache_key in GAME_RESULTS_CACHE:
            return GAME_RESULTS_CACHE[cache_key]
        
        result = {"winner": None, "team1": None, "team2": None}
        
        # Get the sport-specific game file
        game_file = GAME_FILES.get(sport)
        if not game_file or not os.path.exists(game_file):
            return result
        
        # Load the games
        try:
            with open(game_file, "r", encoding="utf-8") as f:
                games = json.load(f)
        except Exception as e:
            print(f"❌ Error loading game file for {sport}: {e}")
            return result
        
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
    
    def calculate_success_rates(filter_sport=None):
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
                continue
                
            # Determine the sport
            sport = determine_sport_from_event_id(event_id)
            
            # Skip if filtering by sport and this doesn't match
            if filter_sport and filter_sport != "All" and sport != filter_sport:
                continue
                
            # Get the actual game result
            game_result = get_game_result(event_id, sport)
            actual_winner = game_result.get("winner")
            
            if not actual_winner:
                continue
                
            # Compare the pick with the actual winner
            is_correct = (pick == actual_winner)
            
            # Update counters
            if is_correct:
                results[sport]["locks"] += 1
                results["overall"]["locks"] += 1
            else:
                results[sport]["rocks"] += 1
                results["overall"]["rocks"] += 1
        
        # Calculate success rates
        stats = {
            "overall_success_rate": 0,
            "sports": []
        }
        
        # Calculate overall rate
        total_overall = results["overall"]["locks"] + results["overall"]["rocks"]
        if total_overall > 0:
            stats["overall_success_rate"] = round(results["overall"]["locks"] / total_overall * 100, 1)
        
        # Calculate rates by sport
        for sport in ["NBA", "NHL", "MLB", "MarchMadness"]:
            total = results[sport]["locks"] + results[sport]["rocks"]
            success_rate = 0
            if total > 0:
                success_rate = round(results[sport]["locks"] / total * 100, 1)
            
            stats["sports"].append({
                "name": sport,
                "success_rate": success_rate,
                "locks": results[sport]["locks"],
                "rocks": results[sport]["rocks"]
            })
        
        return stats
    
    def get_performance_chart_data(sport=None):
        """Calculate performance chart data from picks history."""
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
            except Exception as e:
                print(f"Error processing date '{date_str}': {e}")
        
        # Return empty data if no pick dates found
        if not picks_by_date:
            return {"dates": [], "locks": [], "rocks": [], "rates": []}
        
        # Sort dates and prepare chart data
        try:
            # Try to sort by date (most recent first)
            def parse_date(date_str):
                try:
                    current_year = datetime.now().year
                    return datetime.strptime(f"{date_str} {current_year}", "%b %d %Y")
                except:
                    return date_str
                    
            sorted_dates = sorted(picks_by_date.keys(), key=parse_date)
            
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
                    rate = round(day_data["locks"] / total * 100, 1)
                rates.append(rate)
            
            return {
                "dates": sorted_dates,
                "locks": locks,
                "rocks": rocks,
                "rates": rates
            }
        except Exception as e:
            print(f"Error preparing chart data: {e}")
            return {"dates": [], "locks": [], "rocks": [], "rates": []}
    
    def get_recent_results(sport=None, limit=10):
        """Get the most recent pick results, optionally filtered by sport."""
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
                # Get the sport-specific game file
                game_file = GAME_FILES.get(pick_sport)
                if game_file and os.path.exists(game_file):
                    with open(game_file, "r", encoding="utf-8") as f:
                        games = json.load(f)
                    
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
    
    def get_games_with_score_differences(sport=None):
        """Get completed games with their score differences to find the best picks."""
        # Initialize empty results list
        games_with_scores = []
        
        # Load picks to determine which games have been picked
        picks = load_picks()
        if not picks:
            return games_with_scores
        
        # Process each sport's games
        sports_to_process = [sport] if sport and sport != "All" else ["NBA", "NHL", "MLB", "MarchMadness"]
        
        for current_sport in sports_to_process:
            try:
                # Load games for this sport
                game_file = GAME_FILES.get(current_sport)
                if not game_file or not os.path.exists(game_file):
                    continue
                    
                games = load_json_file(game_file)
                
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