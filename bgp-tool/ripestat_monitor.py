import requests
import json
import time

import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config['monitored_prefixes'], config['authorized_as']

MONITORED_PREFIXES, AUTHORIZED_AS = load_config()

RIPE_API_URL = "https://stat.ripe.net/data/bgp-state/data.json"

def check_for_hijacks():
    alerts = []
    for prefix in MONITORED_PREFIXES:
        params = {'resource': prefix}
        try:
            response = requests.get(RIPE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            for state in data.get('data', {}).get('bgp_state', []):
                path = state.get('path', [])
                if path and path[-1] != AUTHORIZED_AS:
                    alerts.append({
                        'prefix': prefix,
                        'hijacking_as': path[-1],
                        'path': path,
                        'timestamp': time.time()
                    })
        except requests.exceptions.RequestException as e:
            print(f"Error querying RIPEstat API: {e}")
    return alerts

from database import get_db_connection
from datetime import datetime

if __name__ == '__main__':
    db = get_db_connection()
    while True:
        hijacks = check_for_hijacks()
        if hijacks:
            # Add a timestamp to each alert
            for alert in hijacks:
                alert['timestamp'] = datetime.utcnow()
            db.hijack_alerts.insert_many(hijacks)
        time.sleep(300) # Sleep for 5 minutes