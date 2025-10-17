import time
import os
from netmiko import ConnectHandler
from dotenv import load_dotenv

load_dotenv()

def get_bgp_summary(device):
    with ConnectHandler(**device) as net_connect:
        output = net_connect.send_command('show ip bgp summary', use_textfsm=True)
    return output

import json

if __name__ == '__main__':
    router_ip = os.getenv('ROUTER_IP')
    username = os.getenv('ROUTER_USER')
    password = os.getenv('ROUTER_PASSWORD')

    if not all([router_ip, username, password]):
        print("Error: ROUTER_IP, ROUTER_USER, and ROUTER_PASSWORD must be set in .env")
    else:
        device = {
            'device_type': 'cisco_ios',
            'host': router_ip,
            'username': username,
            'password': password,
        }

        while True:
            try:
                summary = get_bgp_summary(device)
                with open('bgp_summary.json', 'w') as f:
                    json.dump(summary, f)
            except Exception as e:
                print(f"Error collecting BGP data: {e}")
            time.sleep(300) # Sleep for 5 minutes