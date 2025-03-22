import subprocess
import sys
import os
from threading import Thread

# Import the Flask app from app.py
try:
    from app import app
except ImportError:
    print("Warning: Could not import Flask app from app.py")
    app = None

from apscheduler.schedulers.background import BackgroundScheduler

# Force UTF-8 encoding in all subprocesses.
os.environ["PYTHONUTF8"] = "1"

def run_script(script_path, wait=True):
    """Run a Python script using the current interpreter in UTF-8 mode.
    
    If wait is True, use subprocess.run() and wait for the script to finish.
    If wait is False, use subprocess.Popen() so that the script runs in the background.
    """
    try:
        print(f"Running {script_path}...")
        # Use the current Python interpreter (sys.executable) instead of hardcoded path
        cmd = [sys.executable, "-X", "utf8", script_path]
        if wait:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=os.environ.copy()
            )
            if result.returncode != 0:
                print(f"Error running {script_path}:\n{result.stderr}")
            else:
                print(f"{script_path} completed successfully.")
        else:
            process = subprocess.Popen(cmd, env=os.environ.copy())
            print(f"{script_path} started with PID {process.pid}.")
    except Exception as e:
        print(f"An exception occurred while running {script_path}: {e}")

def update_all_scripts():
    """Run all update scripts sequentially and then publish the updated data."""
    # Check if script files exist before attempting to run them
    update_scripts = [
        "Data_Queries/march_madness_games.py",
        "Data_Queries/mlb_games.py",
        "Data_Queries/nba_games.py",
        "Data_Queries/nhl_games.py"
    ]
    
    # Verify each script exists
    scripts_to_run = []
    for script in update_scripts:
        if os.path.exists(script):
            scripts_to_run.append(script)
        else:
            # Try to get absolute path
            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base_dir, script)
            if os.path.exists(full_path):
                scripts_to_run.append(full_path)
            else:
                print(f"Warning: Script {script} not found, skipping.")
    
    # Run the scripts that were found
    for script in scripts_to_run:
        run_script(script, wait=True)
    
    publish_data()

def publish_data():
    """
    Publish the updated data when it's ready.
    
    This function can be extended to notify the Flask app, update a cache,
    or trigger a web socket event to connected clients.
    """
    print("Data published and ready to serve!")
    # Example: if your Flask app has a method to update its data, you could call it here.
    if app and hasattr(app, 'refresh_data'):
        try:
            app.refresh_data()
            print("App data refreshed successfully.")
        except Exception as e:
            print(f"Error refreshing app data: {e}")

if __name__ == "__main__":
    # Start the background scheduler to update data every hour.
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_all_scripts, 'interval', hours=1)
    scheduler.start()
    
    # Optionally, run an immediate update in a separate thread so that the server gets fresh data on startup.
    Thread(target=update_all_scripts).start()
    
    try:
        # Start the Flask server if app was successfully imported
        if app:
            print("Starting Flask server...")
            app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
        else:
            print("Flask app not available. Running in data update mode only.")
            # Keep the script running to allow scheduled updates
            import time
            while True:
                time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler...")
        scheduler.shutdown()
        print("Scheduler shutdown complete.")