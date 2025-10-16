from flask import Flask, render_template, request
from netmiko import ConnectHandler
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

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