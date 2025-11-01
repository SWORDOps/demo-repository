import time
import os
import re
import sys
from netmiko import ConnectHandler
from dotenv import load_dotenv
from datetime import datetime

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from bgp_defense_tool.database import get_db_connection

# Load environment variables from the root .env file
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

def get_bgp_summary(device):
    """
    Gets BGP summary, enriches it with description and shutdown status from the
    running-config in a more robust way.
    """
    with ConnectHandler(**device) as net_connect:
        summary_output = net_connect.send_command('show ip bgp summary', use_textfsm=True)
        if not summary_output:
            return None

        run_config = net_connect.send_command('show running-config')

        # Find the BGP configuration section
        bgp_config_match = re.search(r"router bgp \d+([\s\S]*?)(?=^router|\Z)", run_config)
        if not bgp_config_match:
            return summary_output # Return basic summary if BGP config is missing

        bgp_config = bgp_config_match.group(1)
        neighbor_details = {}

        # Process each neighbor individually
        for neighbor_line in re.finditer(r"^\s*neighbor (\S+)", bgp_config, re.MULTILINE):
            neighbor_ip = neighbor_line.group(1)

            # Find the full configuration block for this specific neighbor
            # This is more robust than a single, complex regex.
            neighbor_block_regex = re.compile(rf"neighbor {re.escape(neighbor_ip)}[\s\S]*?(?=^ neighbor|\Z)")
            block_match = neighbor_block_regex.search(bgp_config)

            if block_match:
                block = block_match.group(0)
                desc_match = re.search(r"description (.*)", block)
                is_shutdown = 'shutdown' in block

                neighbor_details[neighbor_ip] = {
                    'description': desc_match.group(1).strip() if desc_match else 'N/A',
                    'is_shutdown': is_shutdown
                }

        # Enrich the summary output
        for neighbor in summary_output:
            details = neighbor_details.get(neighbor['neighbor'], {})
            neighbor['description'] = details.get('description', 'N/A')
            neighbor['is_shutdown'] = details.get('is_shutdown', False)

    return summary_output

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