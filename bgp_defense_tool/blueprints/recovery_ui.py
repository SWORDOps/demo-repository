from flask import Blueprint, render_template

bp = Blueprint('recovery', __name__)

LOG_FILE = "/var/log/cisco_recovery.log"

@bp.route('/recovery')
def recovery():
    """Displays the Hardware Recovery page."""
    log_content = ""
    try:
        with open(LOG_FILE, 'r') as f:
            log_content = f.read()
    except FileNotFoundError:
        log_content = f"Log file not found at {LOG_FILE}. Has the script been run yet?"
    except Exception as e:
        log_content = f"An error occurred while reading the log file: {e}"

    return render_template('recovery.html', log_content=log_content)
