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

def depeer_neighbor(neighbor_ip):
    """Tears down the BGP session with a neighbor."""
    device = get_device_config()
    bgp_asn = os.getenv('BGP_ASN')

    config_commands = [
        f'router bgp {bgp_asn}',
        f'no neighbor {neighbor_ip}',
    ]

    try:
        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except Exception as e:
        return f"Error de-peering neighbor: {e}"

def blackhole_route(prefix):
    """Creates a null-route for a prefix."""
    device = get_device_config()

    try:
        net = ip_network(prefix)
        config_commands = [
            f'ip route {net.network_address} {net.netmask} null0',
        ]

        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except (ValueError, Exception) as e:
        return f"Error creating blackhole route: {e}"

def challenge_with_rpki(prefix, bgp_asn):
    """Announces more-specific prefixes to mitigate a hijack, with a comment indicating RPKI validation failure."""
    device = get_device_config()
    try:
        net = ip_network(prefix)
        subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
        config_commands = [
            f'router bgp {bgp_asn}',
            'address-family ipv4 unicast',
            f'network {subnets[0].with_prefixlen} route-map RPKI_CHALLENGE',
            f'network {subnets[1].with_prefixlen} route-map RPKI_CHALLENGE',
            'exit',
            'route-map RPKI_CHALLENGE permit 10',
            'description "Mitigation for RPKI-invalid announcement"',
        ]

        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except (ValueError, Exception) as e:
        return f"Error during RPKI challenge: {e}"

def signal_upstream(prefix, communities):
    """Announces a prefix with the RTBH community to signal upstream providers."""
    device = get_device_config()
    bgp_asn = os.getenv('BGP_ASN')

    try:
        net = ip_network(prefix)
        route_map_name = f"RTBH_{net.network_address.exploded.replace(':', '_').replace('.', '_')}"

        config_commands = [
            f'route-map {route_map_name} permit 10',
            f'set community {" ".join(communities)}',
            'exit',
            f'router bgp {bgp_asn}',
            f'network {net.with_prefixlen} route-map {route_map_name}',
        ]

        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except (ValueError, Exception) as e:
        return f"Error signaling upstream: {e}"