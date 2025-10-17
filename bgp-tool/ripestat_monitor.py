import requests
import json
import time

import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

from mitigation import mitigate_hijack, prepend_as_path
from database import get_latest_bgp_summary

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config

config = load_config()
MONITORED_PREFIXES = config['monitored_prefixes']
AUTHORIZED_AS = config['authorized_as']
AUTO_MITIGATE = config.get('auto_mitigate', False)
PREPEND_ON_MITIGATE = config.get('prepend_on_mitigate', False)
PREPEND_COUNT = config.get('prepend_count', 3)

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
    bgp_asn = os.getenv('BGP_ASN')
    while True:
        hijacks = check_for_hijacks()
        if hijacks:
            now = datetime.utcnow()
            for alert in hijacks:
                alert['timestamp'] = now
            db.hijack_alerts.insert_many(hijacks)

            if AUTO_MITIGATE:
                for alert in hijacks:
                    print(f"Auto-mitigating hijack for prefix {alert['prefix']}...")
                    mitigate_hijack(alert['prefix'], bgp_asn)

            if PREPEND_ON_MITIGATE:
                summary = get_latest_bgp_summary()
                for neighbor in summary:
                    if neighbor['state_pfxrcd'] == 'Established':
                        print(f"Applying AS_PATH prepending to neighbor {neighbor['neighbor']}...")
                        prepend_as_path(neighbor['neighbor'], bgp_asn, PREPEND_COUNT)

        time.sleep(300) # Sleep for 5 minutes