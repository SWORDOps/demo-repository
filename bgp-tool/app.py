from flask import Flask, render_template, request
from datetime import datetime
from netmiko import ConnectHandler
import os
from dotenv import load_dotenv
import subprocess
import atexit

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__)

@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt=None):
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

@app.route('/')
def index():
    bgp_summary_path = os.path.join(os.path.dirname(__file__), 'bgp_summary.json')
    hijack_alerts_path = os.path.join(os.path.dirname(__file__), 'hijack_alerts.json')
    try:
        with open(bgp_summary_path, 'r') as f:
            bgp_summary_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        bgp_summary_data = None

    try:
        with open(hijack_alerts_path, 'r') as f:
            hijack_alerts_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        hijack_alerts_data = None

    return render_template('index.html', bgp_summary=bgp_summary_data, hijack_alerts=hijack_alerts_data)

from ipaddress import ip_network

@app.route('/reroute', methods=['POST'])
def reroute():
    action = request.form.get('action')
    prefix = request.form.get('prefix')

    if action == 'mitigate':
        router_ip = os.getenv('ROUTER_IP')
        username = os.getenv('ROUTER_USER')
        password = os.getenv('ROUTER_PASSWORD')
        bgp_asn = os.getenv('BGP_ASN') # Assuming BGP_ASN is in .env for mitigation
        if not all([router_ip, username, password, bgp_asn, prefix]):
            return render_template('index.html', output="Error: Missing required environment variables for mitigation.")
    else:
        router_ip = request.form['router_ip']
        username = request.form['username'] or os.getenv('ROUTER_USER')
        password = request.form['password'] or os.getenv('ROUTER_PASSWORD')
        bgp_asn = request.form['bgp_asn']
        if not all([router_ip, bgp_asn, prefix, action]) or not (username and password):
            return render_template('index.html', output="Error: All fields are required.")

    device = {
        'device_type': 'cisco_ios',
        'host': router_ip,
        'username': username,
        'password': password,
    }

    if action == 'mitigate':
        try:
            net = ip_network(prefix)
            subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
            config_commands = [f'router bgp {bgp_asn}']
            config_commands.extend([f'network {sub.with_prefixlen}' for sub in subnets])
        except ValueError:
            return render_template('index.html', output=f"Error: Invalid prefix '{prefix}' for mitigation.")
    elif action == 'withdraw_mitigation':
        try:
            net = ip_network(prefix)
            subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
            config_commands = [f'router bgp {bgp_asn}']
            config_commands.extend([f'no network {sub.with_prefixlen}' for sub in subnets])
        except ValueError:
            return render_template('index.html', output=f"Error: Invalid prefix '{prefix}' for mitigation.")
    else:
        config_commands = [
            f'router bgp {bgp_asn}',
            f'network {prefix}' if action == 'advertise' else f'no network {prefix}',
        ]

    output = ""
    try:
        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
    except Exception as e:
        output = str(e)

    return render_template('index.html', output=output)

if __name__ == '__main__':
    app.run(debug=True)