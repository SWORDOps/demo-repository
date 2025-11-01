from bgp_defense_tool import create_app
import subprocess
import atexit
import os

def start_monitors():
    """Starts the background monitoring scripts."""
    print("Starting background monitors...")
    monitor_dir = os.path.join(os.path.dirname(__file__), 'bgp_defense_tool', 'monitors')
    bgp_monitor_path = os.path.join(monitor_dir, 'bgp_monitor.py')
    ripestat_monitor_path = os.path.join(monitor_dir, 'ripestat_monitor.py')

    bgp_monitor = subprocess.Popen(['python', bgp_monitor_path])
    ripestat_monitor = subprocess.Popen(['python', ripestat_monitor_path])

    return [bgp_monitor, ripestat_monitor]

def stop_monitors(processes):
    """Stops the background monitoring scripts."""
    print("Stopping background monitors...")
    for p in processes:
        p.terminate()

if __name__ == '__main__':
    app = create_app()

    # Start the background monitors
    monitor_processes = start_monitors()

    # Register the cleanup function to run on exit
    atexit.register(stop_monitors, monitor_processes)

    # Start the Flask web server
    app.run(debug=True)