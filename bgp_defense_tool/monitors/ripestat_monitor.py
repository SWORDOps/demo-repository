import requests
import json
import time
import os
from datetime import datetime
from dotenv import load_dotenv
from ipaddress import ip_network

import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Local module imports
from bgp_defense_tool.database import get_db_connection
from bgp_defense_tool.logic.mitigation_logic import mitigate_hijack, signal_upstream

# Load environment variables from the root .env file
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
def load_config():
    """Loads the main configuration file from the project root."""
    config_path = os.path.join(project_root, 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

# --- API Communication ---
RIPE_API_URL = "https://stat.ripe.net/data/bgp-state/data.json"
RPKI_API_URL = "https://stat.ripe.net/data/rpki-validation/data.json"

ABUSEIPDB_API_URL = 'https://api.abuseipdb.com/api/v2/check'

import socket

def get_ip_for_asn(asn):
    """
    Attempts to find a representative IP address for an ASN by performing a DNS
    lookup on a domain likely associated with the AS. This is a heuristic.
    """
    try:
        # Many ASNs have a web presence at as<ASN>.net
        domain = f"as{asn}.net"
        ip_address = socket.gethostbyname(domain)
        return ip_address
    except socket.gaierror:
        # Fallback for demonstration if the domain doesn't resolve.
        # This is still a placeholder, but the primary method is more realistic.
        print(f"Could not resolve {domain}, falling back to a placeholder IP.")
        p1 = (int(asn) >> 16) & 255
        p2 = int(asn) & 255
        return f"10.{p1}.{p2}.1"

def get_abuseipdb_score(ip_address, api_key):
    """
    Gets the abuse confidence score for an IP address from AbuseIPDB.
    """
    if not api_key:
        return None

    headers = {'Key': api_key, 'Accept': 'application/json'}
    params = {'ipAddress': ip_address, 'maxAgeInDays': '90'}

    try:
        response = requests.get(ABUSEIPDB_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('abuseConfidenceScore')
    except requests.exceptions.RequestException as e:
        print(f"Error querying AbuseIPDB API for ASN {asn} (IP: {ip_address}): {e}")
        return None


def get_rpki_status(prefix, asn):
    """Gets the RPKI validation status for a prefix and ASN from RIPEstat."""
    params = {'resource': asn, 'prefix': prefix}
    try:
        response = requests.get(RPKI_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        roas = data.get('data', {}).get('validating_roas', [])
        if not roas:
            return 'not-found'
        return roas[0].get('validity', 'not-found')
    except (requests.exceptions.RequestException, IndexError) as e:
        print(f"Error querying RPKI API: {e}")
        return "error"

BGPVIEW_API_URL = "https://api.bgpview.io/prefix/"

def check_ripe_for_hijacks(monitored_prefixes, authorized_as):
    """Queries RIPEstat for BGP state and detects hijacks."""
    alerts = []
    for prefix in monitored_prefixes:
        params = {'resource': prefix}
        try:
            response = requests.get(RIPE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            for state in data.get('data', {}).get('bgp_state', []):
                path = state.get('path', [])
                if path and str(path[-1]) != str(authorized_as):
                    rpki_status = get_rpki_status(prefix, path[-1])
                    alerts.append({
                        'prefix': prefix,
                        'hijacking_as': str(path[-1]),
                        'path': [str(p) for p in path],
                        'timestamp': time.time(),
                        'rpki_status': rpki_status,
                        'source': 'ripestat'
                    })
        except requests.exceptions.RequestException as e:
            print(f"Error querying RIPEstat API for {prefix}: {e}")
    return alerts

def check_bgpview_for_hijacks(monitored_prefixes, authorized_as):
    """Queries BGPView for BGP state and detects hijacks."""
    alerts = []
    for prefix in monitored_prefixes:
        url = f"{BGPVIEW_API_URL}{prefix}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            for pfx in data.get('data', {}).get('prefixes', []):
                origin_as = pfx.get('asn', {}).get('asn')
                if origin_as and str(origin_as) != str(authorized_as):
                    rpki_status = get_rpki_status(prefix, origin_as)
                    # BGPView doesn't provide the full path, so we create a simplified one
                    path = [str(origin_as)]
                    alerts.append({
                        'prefix': prefix,
                        'hijacking_as': str(origin_as),
                        'path': path,
                        'timestamp': time.time(),
                        'rpki_status': rpki_status,
                        'source': 'bgpview'
                    })
        except requests.exceptions.RequestException as e:
            print(f"Error querying BGPView API for {prefix}: {e}")
    return alerts

# --- Policy Engine ---
def evaluate_and_execute_policies(alert, policies, bgp_asn, rtbh_communities, db):
    """
    Evaluates a hijack alert against automation policies, executes actions,
    and logs them to the database.
    """
    for policy in policies:
        conditions = policy.get('conditions', {})
        actions = policy.get('actions', [])

        # Condition matching
        prefix_match = ('prefix' not in conditions) or (conditions['prefix'] == alert['prefix'])
        rpki_match = ('rpki_status' not in conditions) or (conditions['rpki_status'] == alert['rpki_status'])

        if prefix_match and rpki_match:
            log_entry = {
                'timestamp': datetime.utcnow(),
                'policy_name': policy['name'],
                'alert_prefix': alert['prefix'],
                'hijacking_as': alert['hijacking_as'],
                'actions_taken': []
            }
            print(f"Alert for {alert['prefix']} matched policy '{policy['name']}'. Executing actions...")

            for action in actions:
                output = ""
                if action == 'announce_more_specific':
                    print(f"  - Action: Announcing more-specifics for {alert['prefix']}")
                    output = mitigate_hijack(alert['prefix'], bgp_asn)
                elif action == 'signal_rtbh':
                    print(f"  - Action: Signaling upstream RTBH for {alert['prefix']}")
                    output = signal_upstream(alert['prefix'], rtbh_communities)

                log_entry['actions_taken'].append({'action': action, 'output': output})

            if log_entry['actions_taken']:
                db.automation_log.insert_one(log_entry)

            # Stop after the first matching policy
            return

# --- Main Loop ---
if __name__ == '__main__':
    db = get_db_connection()
    bgp_asn = os.getenv('BGP_ASN')

    print("Starting RIPEstat monitor...")
    while True:
        # Reload config in each loop to pick up changes without restarting
        config = load_config()
        monitored_prefixes = config.get('monitored_prefixes', [])
        authorized_as = config.get('authorized_as')
        policies = config.get('automation_policies', [])
        rtbh_communities = config.get('rtbh_communities', [])

        print(f"[{datetime.utcnow()}] Checking for hijacks for prefixes: {monitored_prefixes}")

        # Query both data sources
        ripe_hijacks = check_ripe_for_hijacks(monitored_prefixes, authorized_as)
        bgpview_hijacks = check_bgpview_for_hijacks(monitored_prefixes, authorized_as)

        # Correlate and de-duplicate alerts
        correlated_hijacks = {}
        for hijack in ripe_hijacks + bgpview_hijacks:
            key = (hijack['prefix'], hijack['hijacking_as'])
            if key not in correlated_hijacks:
                hijack['sources'] = [hijack.pop('source')]
                correlated_hijacks[key] = hijack
            else:
                correlated_hijacks[key]['sources'].append(hijack['source'])

        final_alerts = list(correlated_hijacks.values())

        if final_alerts:
            print(f"Detected {len(final_alerts)} unique hijack(s) after correlation!")
            now = datetime.utcnow()
            abuse_api_key = os.getenv('ABUSEIPDB_API_KEY')

            for alert in final_alerts:
                alert['timestamp'] = now
                # Enrich with threat intelligence
                ip_to_check = get_ip_for_asn(alert['hijacking_as'])
                alert['abuse_confidence_score'] = get_abuseipdb_score(ip_to_check, abuse_api_key)

            # Insert enriched, de-duplicated alerts into the database
            db.hijack_alerts.insert_many(final_alerts)

            # Evaluate policies for each unique hijack
            if policies:
                for alert in final_alerts:
                    evaluate_and_execute_policies(alert, policies, bgp_asn, rtbh_communities, db)
            else:
                print("No automation policies defined. Manual intervention required.")

        # Wait for 5 minutes before the next check
        time.sleep(300)