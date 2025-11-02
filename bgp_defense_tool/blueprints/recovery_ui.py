from flask import Blueprint, render_template
import shutil

bp = Blueprint('recovery', __name__, template_folder='../templates')

LOG_FILE = "/var/log/cisco_recovery.log"

def check_dependencies():
    """Checks for the shell command dependencies of the recovery script."""
    dependencies = {
        "Core": ["bash", "stty", "timeout", "logger", "lsusb", "find"],
        "Analysis": ["strings", "binwalk", "hexdump", "grep", "awk"],
        "JTAG": ["openocd"],
        "Automation": ["expect"]
    }

    dependency_status = []
    for category, commands in dependencies.items():
        for cmd in commands:
            status = "Found" if shutil.which(cmd) else "Missing"
            suggestion = ""
            if status == "Missing":
                # Provide a generic suggestion; user will know their package manager
                suggestion = f"sudo apt-get install {cmd} / sudo yum install {cmd}"
            dependency_status.append({
                "category": category,
                "command": cmd,
                "status": status,
                "suggestion": suggestion
            })
    return dependency_status

@bp.route('/recovery')
def recovery():
    """Displays the Hardware Recovery page with a dependency pre-flight check."""
    log_content = ""
    try:
        with open(LOG_FILE, 'r') as f:
            # Read the last 50 lines for brevity in the UI
            lines = f.readlines()
            log_content = "".join(lines[-50:])
    except FileNotFoundError:
        log_content = f"Log file not found at {LOG_FILE}. Has the script been run yet?"
    except Exception as e:
        log_content = f"An error occurred while reading the log file: {e}"

    dependencies = check_dependencies()

    return render_template('recovery.html', log_content=log_content, dependencies=dependencies)
