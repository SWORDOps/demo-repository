from flask import Flask, render_template, request
from netmiko import ConnectHandler
import os
from dotenv import load_dotenv
import subprocess
import atexit

load_dotenv()

app = Flask(__name__)

import json

# In-memory store for BGP data
bgp_summary_data = None

def start_monitor():
    print("Starting BGP monitor...")
    monitor_process = subprocess.Popen(['python', 'bgp_monitor.py'])
    return monitor_process

def stop_monitor(process):
    print("Stopping BGP monitor...")
    process.terminate()

monitor_process = start_monitor()
atexit.register(stop_monitor, monitor_process)

@app.route('/')
def index():
    try:
        with open('bgp_summary.json', 'r') as f:
            bgp_summary_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        bgp_summary_data = None
    return render_template('index.html', bgp_summary=bgp_summary_data)

@app.route('/reroute', methods=['POST'])
def reroute():
    router_ip = request.form['router_ip']
    username = request.form['username'] or os.getenv('ROUTER_USER')
    password = request.form['password'] or os.getenv('ROUTER_PASSWORD')
    bgp_asn = request.form['bgp_asn']
    prefix = request.form['prefix']
    action = request.form['action']

    if not all([router_ip, bgp_asn, prefix, action]) or not (username and password):
        return render_template('index.html', output="Error: All fields are required.")

    device = {
        'device_type': 'cisco_ios',
        'host': router_ip,
        'username': username,
        'password': password,
    }

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