from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
from netmiko import ConnectHandler
import os
from dotenv import load_dotenv
import subprocess
import atexit
from bson import json_util

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__)

@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt=None):
    if isinstance(date, (int, float)):
        date = datetime.fromtimestamp(date)
    return date.strftime(fmt or '%Y-%m-%d %H:%M:%S')

import json

# In-memory store for BGP data
bgp_summary_data = None

def start_monitors():
    print("Starting monitors...")
    bgp_monitor_path = os.path.join(os.path.dirname(__file__), 'bgp_monitor.py')
    ripestat_monitor_path = os.path.join(os.path.dirname(__file__), 'ripestat_monitor.py')
    bgp_monitor = subprocess.Popen(['python', bgp_monitor_path])
    ripestat_monitor = subprocess.Popen(['python', ripestat_monitor_path])
    return [bgp_monitor, ripestat_monitor]

def stop_monitors(processes):
    print("Stopping monitors...")
    for p in processes:
        p.terminate()

monitor_processes = start_monitors()
atexit.register(stop_monitors, monitor_processes)

from database import get_db_connection

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

@app.route('/')
def index():
    latest_summary = None
    recent_hijacks = None
    recent_flaps = None
    db_error = None
    config = load_config()

    try:
        db = get_db_connection()

        # Fetch the most recent BGP summary for each neighbor
        latest_summary = list(db.bgp_summary.aggregate([
            {'$sort': {'timestamp': -1}},
            {'$group': {
                '_id': '$neighbor',
                'doc': {'$first': '$$ROOT'}
            }},
            {'$replaceRoot': {'newRoot': '$doc'}}
        ]))

        # Fetch the most recent hijack alerts
        recent_hijacks = list(db.hijack_alerts.find().sort('timestamp', -1).limit(10))

        # Fetch the most recent BGP flaps
        recent_flaps = list(db.bgp_flaps.find().sort('timestamp', -1).limit(10))

    except Exception as e:
        db_error = f"Error connecting to the database: {e}"

    return render_template('index.html', bgp_summary=latest_summary, hijack_alerts=recent_hijacks, bgp_flaps=recent_flaps, db_error=db_error, config=config)

@app.route('/update_config', methods=['POST'])
def update_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    config['auto_mitigate'] = 'auto_mitigate' in request.form
    config['prepend_on_mitigate'] = 'prepend_on_mitigate' in request.form
    config['prepend_count'] = int(request.form.get('prepend_count', 3))

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

    return redirect(url_for('index'))

@app.route('/history')
def history():
    db = get_db_connection()
    all_hijacks = list(db.hijack_alerts.find().sort('timestamp', -1))
    return render_template('history.html', hijack_alerts=all_hijacks)

@app.route('/automation_log')
def automation_log():
    db = get_db_connection()
    logs = list(db.automation_log.find().sort('timestamp', -1))
    return render_template('automation_log.html', logs=logs)

import requests

RPKI_API_URL = "https://stat.ripe.net/data/rpki-validation/data.json"

def get_rpki_status(prefix, asn):
    """Gets the RPKI validation status for a prefix and ASN."""
    params = {'resource': asn, 'prefix': prefix}
    try:
        response = requests.get(RPKI_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('validating_roas', [{}])[0].get('validity', 'not-found')
    except (requests.exceptions.RequestException, IndexError) as e:
        print(f"Error querying RPKI API: {e}")
        return "error"

@app.route('/rpki_helper')
def rpki_helper():
    config = load_config()
    monitored_prefixes = config.get('monitored_prefixes', [])
    authorized_as = config.get('authorized_as')

    rpki_data = []
    for prefix in monitored_prefixes:
        rpki_data.append({
            'prefix': prefix,
            'status': get_rpki_status(prefix, authorized_as)
        })

    return render_template('rpki_helper.html', rpki_data=rpki_data)
from mitigation import mitigate_hijack, withdraw_mitigation, depeer_neighbor, blackhole_route, signal_upstream, challenge_with_rpki
    return render_template('rpki_helper.html', rpki_data=rpki_data, config=config)

@app.route('/analytics')
def analytics():
    hijacks_over_time = []
    top_offenders = []
    db_error = None

    try:
        db = get_db_connection()

        # Time-series data for hijacks over the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        hijacks_over_time = list(db.hijack_alerts.aggregate([
            {'$match': {'timestamp': {'$gte': thirty_days_ago}}},
            {'$group': {
                '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}}
        ]))

        # Top 10 offending ASNs
        top_offenders = list(db.hijack_alerts.aggregate([
            {'$group': {
                '_id': '$hijacking_as',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]))
    except Exception as e:
        db_error = f"Error connecting to the database: {e}"

    # Convert BSON to JSON serializable format
    hijacks_json = json.dumps(hijacks_over_time)

    return render_template('analytics.html',
                           hijacks_over_time=hijacks_json,
                           top_offenders=top_offenders,
                           db_error=db_error)

from mitigation_logic import mitigate_hijack, withdraw_mitigation, depeer_neighbor, blackhole_route, signal_upstream, challenge_with_rpki, apply_flowspec_rule, withdraw_flowspec_rule, deploy_eem_sentry

@app.route('/on_router_defense', methods=['GET', 'POST'])
def on_router_defense():
    config = load_config()
    output = None
    if request.method == 'POST':
        prefix = request.form.get('prefix')
        unauthorized_asns_str = request.form.get('unauthorized_asns')
        unauthorized_asns = [asn.strip() for asn in unauthorized_asns_str.split(',')]
        output = deploy_eem_sentry(prefix, unauthorized_asns)

    return render_template('on_router_defense.html', config=config, output=output)

@app.route('/flowspec', methods=['POST'])
def flowspec():
    source_prefix = request.form.get('source_prefix')
    dest_prefix = request.form.get('destination_prefix')
    action = request.form.get('action')

    if action == 'apply':
        output = apply_flowspec_rule(source_prefix, dest_prefix)
    elif action == 'withdraw':
        output = withdraw_flowspec_rule(source_prefix, dest_prefix)
    else:
        output = "Invalid action."

    return redirect(url_for('index', output=output))

@app.route('/reroute', methods=['POST'])
def reroute():
    action = request.form.get('action')
    prefix = request.form.get('prefix')
    rpki_status = request.form.get('rpki_status')
    bgp_asn = os.getenv('BGP_ASN') # BGP_ASN is now consistently from .env

    if action == 'mitigate':
        if rpki_status == 'invalid':
            output = challenge_with_rpki(prefix, bgp_asn)
        else:
            output = mitigate_hijack(prefix, bgp_asn)

    bgp_asn = os.getenv('BGP_ASN')

    if action == 'mitigate':
        # The 'challenge_with_rpki' is now just a specific mitigation
        output = mitigate_hijack(prefix, bgp_asn)
    elif action == 'withdraw_mitigation':
        output = withdraw_mitigation(prefix, bgp_asn)
    else:
        # Manual advertise/withdraw logic now uses the centralized action
        bgp_asn_form = request.form['bgp_asn']
        if not all([bgp_asn_form, prefix, action]):
             return render_template('index.html', output="Error: BGP ASN and Prefix are required for manual action.")

        config_commands = [
            f'router bgp {bgp_asn_form}',
            f'network {prefix}' if action == 'advertise' else f'no network {prefix}',
        ]
        output = send_config_to_router(config_commands)

    # To prevent breaking the UI, we'll just redirect to the index
    # A better solution would be to use AJAX to display the output
    return redirect(url_for('index', output=output))

@app.route('/depeer', methods=['POST'])
def depeer():
    neighbor_ip = request.form.get('neighbor_ip')
    output = depeer_neighbor(neighbor_ip)
    return render_template('index.html', output=output)

@app.route('/blackhole', methods=['POST'])
def blackhole():
    prefix = request.form.get('blackhole_prefix')
    output = blackhole_route(prefix)
    return render_template('index.html', output=output)

@app.route('/rtbh', methods=['POST'])
def rtbh():
    prefix = request.form.get('prefix')
    config = load_config()
    communities = config.get('rtbh_communities', [])
    output = signal_upstream(prefix, communities)
    return render_template('index.html', output=output)

@app.route('/depeer', methods=['POST'])
def depeer():
    neighbor_ip = request.form.get('neighbor_ip')
    output = depeer_neighbor(neighbor_ip)
    return render_template('index.html', output=output)

@app.route('/blackhole', methods=['POST'])
def blackhole():
    prefix = request.form.get('blackhole_prefix')
    output = blackhole_route(prefix)
    return render_template('index.html', output=output)

@app.route('/rtbh', methods=['POST'])
def rtbh():
    prefix = request.form.get('prefix')
    config = load_config()
    communities = config.get('rtbh_communities', [])
    output = signal_upstream(prefix, communities)
    return render_template('index.html', output=output)

if __name__ == '__main__':
    app.run(debug=True)
