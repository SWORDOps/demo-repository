import requests
import json
import time

import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

# Configuration - will be moved to a separate file later
MONITORED_PREFIXES = ['192.0.2.0/24']
AUTHORIZED_AS = os.getenv('BGP_ASN')

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

if __name__ == '__main__':
    while True:
        hijacks = check_for_hijacks()
        if hijacks:
            alerts_path = os.path.join(os.path.dirname(__file__), 'hijack_alerts.json')
            with open(alerts_path, 'w') as f:
                json.dump(hijacks, f)
        # In a real application, you might want to clear the alerts file
        # if there are no hijacks, but for now we'll leave it as is.
        time.sleep(300) # Sleep for 5 minutes