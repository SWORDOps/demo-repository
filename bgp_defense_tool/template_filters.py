from datetime import datetime

def strftime(date, fmt=None):
    """Jinja2 filter to format a datetime object."""
    if isinstance(date, (int, float)):
        date = datetime.fromtimestamp(date)
    return date.strftime(fmt or '%Y-%m-%d %H:%M:%S')