from ipaddress import ip_network
from netmiko import ConnectHandler
import os

def get_device_config():
    """Returns a dictionary with the device connection parameters."""
    return {
        'device_type': 'cisco_ios',
        'host': os.getenv('ROUTER_IP'),
        'username': os.getenv('ROUTER_USER'),
        'password': os.getenv('ROUTER_PASSWORD'),
    }

def mitigate_hijack(prefix, bgp_asn):
    """Announces more-specific prefixes to mitigate a hijack."""
    device = get_device_config()
    try:
        net = ip_network(prefix)
        subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
        config_commands = [f'router bgp {bgp_asn}']
        config_commands.extend([f'network {sub.with_prefixlen}' for sub in subnets])

        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except (ValueError, Exception) as e:
        return f"Error during mitigation: {e}"

def withdraw_mitigation(prefix, bgp_asn):
    """Withdraws the more-specific prefixes that were announced during mitigation."""
    device = get_device_config()
    try:
        net = ip_network(prefix)
        subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
        config_commands = [f'router bgp {bgp_asn}']
        config_commands.extend([f'no network {sub.with_prefixlen}' for sub in subnets])

        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except (ValueError, Exception) as e:
        return f"Error during withdrawal: {e}"

def prepend_as_path(neighbor_ip, bgp_asn, prepend_count):
    """Applies a route-map to a neighbor to prepend the AS path."""
    device = get_device_config()
    route_map_name = f"PREPEND_AS_PATH_{neighbor_ip.replace('.', '_')}"

    config_commands = [
        f'route-map {route_map_name} permit 10',
        f'set as-path prepend {" ".join([str(bgp_asn)] * prepend_count)}',
        'exit',
        f'router bgp {bgp_asn}',
        f'neighbor {neighbor_ip} route-map {route_map_name} out',
    ]

    try:
        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except Exception as e:
        return f"Error applying AS_PATH prepending: {e}"