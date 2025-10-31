import time
import os
from netmiko import ConnectHandler
from dotenv import load_dotenv
from database import get_db_connection
from datetime import datetime

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

def get_bgp_summary(device):
    with ConnectHandler(**device) as net_connect:
        output = net_connect.send_command('show ip bgp summary', use_textfsm=True)
    return output

if __name__ == '__main__':
    db = get_db_connection()
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
                if summary:
                    now = datetime.utcnow()
                    for item in summary:
                        item['timestamp'] = now

                        # Check for flaps
                        last_state = db.bgp_summary.find_one(
                            {'neighbor': item['neighbor']},
                            sort=[('timestamp', -1)]
                        )

                        if last_state and last_state.get('state_pfxrcd') == 'Established' and item.get('state_pfxrcd') != 'Established':
                            db.bgp_flaps.insert_one({
                                'neighbor': item['neighbor'],
                                'previous_state': last_state['state_pfxrcd'],
                                'current_state': item['state_pfxrcd'],
                                'timestamp': now
                            })

                    db.bgp_summary.insert_many(summary)
            except Exception as e:
                print(f"Error collecting BGP data: {e}")
            time.sleep(300) # Sleep for 5 minutes