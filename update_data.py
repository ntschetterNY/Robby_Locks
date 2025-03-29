import argparse
import subprocess
import sys
import os
import time
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed

# Attempt to import the Flask app from app.py.
try:
    from app import app
except ImportError:
    print("Warning: Could not import Flask app from app.py. Running in data update mode only.")
    app = None

from apscheduler.schedulers.background import BackgroundScheduler

# Force UTF-8 encoding in all subprocesses.
os.environ["PYTHONUTF8"] = "1"

def run_script(script_path, wait=True):
    """Run a Python script using the current interpreter in UTF-8 mode."""
    try:
        print(f"Running {script_path}...")
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
                return False
            else:
                print(f"{script_path} completed successfully.")
                return True
        else:
            process = subprocess.Popen(cmd, env=os.environ.copy())
            print(f"{script_path} started with PID {process.pid}.")
            return process
    except Exception as e:
        print(f"An exception occurred while running {script_path}: {e}")
        return False

def update_all_scripts():
    """Run all update scripts concurrently and publish the updated data."""
    update_scripts = [
        "Data_Queries/march_madness_games.py",
        "Data_Queries/mlb_games.py",
        "Data_Queries/nba_games.py",
        "Data_Queries/nhl_games.py"
    ]
    
    # Verify each script exists.
    scripts_to_run = []
    for script in update_scripts:
        if os.path.exists(script):
            scripts_to_run.append(script)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base_dir, script)
            if os.path.exists(full_path):
                scripts_to_run.append(full_path)
            else:
                print(f"Warning: Script {script} not found, skipping.")
    
    # Run scripts concurrently using ThreadPoolExecutor.
    results = []
    with ThreadPoolExecutor(max_workers=len(scripts_to_run)) as executor:
        future_to_script = {executor.submit(run_script, script): script for script in scripts_to_run}
        for future in as_completed(future_to_script):
            script = future_to_script[future]
            try:
                success = future.result()
                results.append((script, success))
            except Exception as e:
                print(f"Exception occurred while running {script}: {e}")
                results.append((script, False))
    
    # Print a summary of the results.
    print("\nUpdate Summary:")
    for script, success in results:
        status = "Succeeded" if success else "Failed"
        print(f"  {os.path.basename(script)}: {status}")
    
    publish_data()

def publish_data():
    """Publish the updated data when it's ready."""
    print("Data published and ready to serve!")
    if app and hasattr(app, 'refresh_data'):
        try:
            app.refresh_data()
            print("App data refreshed successfully.")
        except Exception as e:
            print(f"Error refreshing app data: {e}")

def main(run_server=False):
    # Start the background scheduler to update data every 10 minutes.
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_all_scripts, 'interval', minutes=10)
    scheduler.start()

    # Run an immediate update in a non-daemon thread to ensure it completes.
    immediate_update_thread = Thread(target=update_all_scripts)
    immediate_update_thread.daemon = False
    immediate_update_thread.start()

    try:
        if run_server and app:
            print("Starting Flask server...")
            app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
        else:
            print("Running in data update mode only. Press Ctrl+C to exit.")
            # Keep the script running.
            while True:
                time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down scheduler...")
        scheduler.shutdown()
        print("Scheduler shutdown complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the update script as a standalone Python script.")
    parser.add_argument("--server", action="store_true", help="Start the Flask server if available.")
    args = parser.parse_args()
    main(run_server=args.server)
