from ipaddress import ip_network
import os
from netmiko import ConnectHandler
from dotenv import load_dotenv

from dotenv import load_dotenv

# Load environment variables from the root .env file
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

def get_device_config():
    """Returns a dictionary with the device connection parameters from environment variables."""
    return {
        'device_type': 'cisco_ios',
        'host': os.getenv('ROUTER_IP'),
        'username': os.getenv('ROUTER_USER'),
        'password': os.getenv('ROUTER_PASSWORD'),
    }

def send_config_to_router(config_commands):
    """
    Connects to the router and sends a set of configuration commands.

    Args:
        config_commands (list): A list of command strings to be executed.

    Returns:
        str: The output from the router or an error message.
    """
    device = get_device_config()
    if not all([device['host'], device['username'], device['password']]):
        return "Error: Router IP, Username, and Password must be set in the .env file."

    try:
        with ConnectHandler(**device) as net_connect:
            output = net_connect.send_config_set(config_commands)
        return output
    except Exception as e:
        return f"Error connecting to router or sending commands: {e}"


def mitigate_hijack(prefix, bgp_asn):
    """Constructs commands to announce more-specific prefixes and sends them to the router."""
    try:
        net = ip_network(prefix)
        # Announce two /25s for a /24, for example
        subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
        config_commands = [f'router bgp {bgp_asn}']
        config_commands.extend([f'network {sub.with_prefixlen}' for sub in subnets])

        return send_config_to_router(config_commands)
    except (ValueError, Exception) as e:
        return f"Error during mitigation: {e}"

def withdraw_mitigation(prefix, bgp_asn):
    """Constructs commands to withdraw more-specific prefixes and sends them to the router."""
    try:
        net = ip_network(prefix)
        subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
        config_commands = [f'router bgp {bgp_asn}']
        config_commands.extend([f'no network {sub.with_prefixlen}' for sub in subnets])

        return send_config_to_router(config_commands)
    except (ValueError, Exception) as e:
        return f"Error during withdrawal: {e}"

def depeer_neighbor(neighbor_ip):
    """Constructs commands to tear down a BGP session and sends them to the router."""
    bgp_asn = os.getenv('BGP_ASN')
    config_commands = [
        f'router bgp {bgp_asn}',
        f'no neighbor {neighbor_ip}',
    ]
    return send_config_to_router(config_commands)

def blackhole_route(prefix):
    """Constructs commands to create a null-route for a prefix and sends them to the router."""
    try:
        net = ip_network(prefix)
        config_commands = [f'ip route {net.network_address} {net.netmask} null0']
        return send_config_to_router(config_commands)
    except (ValueError, Exception) as e:
        return f"Error creating blackhole route: {e}"

def signal_upstream(prefix, communities):
    """Constructs commands to announce a prefix with an RTBH community and sends them to the router."""
    bgp_asn = os.getenv('BGP_ASN')
    try:
        net = ip_network(prefix)
        # Sanitize prefix for route-map name
        route_map_name = f"RTBH_{net.network_address.exploded.replace(':', '_').replace('.', '_')}"

        config_commands = [
            f'route-map {route_map_name} permit 10',
            f'set community {" ".join(communities)} no-export',
            'exit',
            f'router bgp {bgp_asn}',
            f'address-family ipv4 unicast',
            f'network {net.with_prefixlen} route-map {route_map_name}',
            'exit-address-family'
        ]
        return send_config_to_router(config_commands)
    except (ValueError, Exception) as e:
        return f"Error signaling upstream: {e}"

def challenge_with_rpki(prefix, bgp_asn):
    """Constructs commands to announce a more-specific prefix for an RPKI-invalid hijack."""
    # This is a specific form of mitigation
    return mitigate_hijack(prefix, bgp_asn)

def apply_flowspec_rule(source_prefix=None, dest_prefix=None):
    """Constructs commands to apply a BGP Flowspec rule to drop traffic."""
    if not source_prefix and not dest_prefix:
        return "Error: At least one of source_prefix or dest_prefix must be specified."

    bgp_asn = os.getenv('BGP_ASN')
    commands = [f'router bgp {bgp_asn}', 'address-family ipv4 flowspec']

    rule_def = "flow-spec"
    if dest_prefix:
        rule_def += f" destination {dest_prefix}"
    if source_prefix:
        rule_def += f" source {source_prefix}"

    commands.append(rule_def)
    commands.append("  action drop")
    commands.append("end")

    return send_config_to_router(commands)

def set_community_for_neighbor(neighbor_ip, prefix, communities):
    """
    Applies a BGP community string for a specific prefix to a single neighbor.
    """
    bgp_asn = os.getenv('BGP_ASN')
    # Sanitize inputs for command strings
    prefix_sanitized = prefix.replace('/', '_').replace('.', '_')
    neighbor_sanitized = neighbor_ip.replace('.', '_')
    # Community strings can be complex, so we'll just use a generic name
    route_map_name = f"COMMUNITY_{prefix_sanitized}_{neighbor_sanitized}"
    prefix_list_name = f"PL_COMMUNITY_{prefix_sanitized}"

    commands = [
        # Create an ACL to match the specific prefix
        f'ip prefix-list {prefix_list_name} permit {prefix}',
        # Create the route-map
        f'route-map {route_map_name} permit 10',
        f' match ip address prefix-list {prefix_list_name}',
        f' set community {communities}',
        'exit',
        # Create a second sequence to permit other routes without modification
        f'route-map {route_map_name} permit 20',
        'exit',
        # Apply the route-map to the neighbor
        f'router bgp {bgp_asn}',
        f' neighbor {neighbor_ip} route-map {route_map_name} out',
        'end'
    ]

    return send_config_to_router(commands)

# --- BGP Neighbor Management Functions ---

def shutdown_neighbor(neighbor_ip):
    """Gracefully shuts down a BGP neighbor."""
    bgp_asn = os.getenv('BGP_ASN')
    commands = [
        f'router bgp {bgp_asn}',
        f' neighbor {neighbor_ip} shutdown',
        'end'
    ]
    return send_config_to_router(commands)

def activate_neighbor(neighbor_ip):
    """Activates a BGP neighbor that was previously shut down."""
    bgp_asn = os.getenv('BGP_ASN')
    commands = [
        f'router bgp {bgp_asn}',
        f' no neighbor {neighbor_ip} shutdown',
        'end'
    ]
    return send_config_to_router(commands)

def provision_neighbor(neighbor_ip, remote_as, description=""):
    """Configures a new BGP neighbor on the router."""
    bgp_asn = os.getenv('BGP_ASN')
    commands = [
        f'router bgp {bgp_asn}',
        f' neighbor {neighbor_ip} remote-as {remote_as}',
    ]
    if description:
        commands.append(f' neighbor {neighbor_ip} description {description}')
    commands.append('end')
    return send_config_to_router(commands)

import re

# Define constants for our specific IGP injection method
IGP_ROUTE_TAG = '777'
IGP_ROUTE_MAP_NAME = 'BGP_TOOL_IGP_INJECT'


def get_active_influence_policies():
    """
    Parses the router's running configuration to find active influence policies
    created by this tool.
    """
    active_policies = {'bgp': [], 'igp': []}

    # Get the running config from the router
    try:
        config = send_config_to_router(['show running-config'])
        if "Error" in config:
            return active_policies
    except Exception:
        return active_policies

    # Regex to find BGP neighbor policies applied by this tool
    bgp_policy_regex = re.compile(r"neighbor (\S+) route-map (DEPRIORITIZE|INFLUENCE|COMMUNITY)_(\S+)_(\S+) out")

    for line in config.splitlines():
        match = bgp_policy_regex.search(line)
        if match:
            neighbor_ip, policy_type, prefix, _ = match.groups()
            # Reconstruct the original prefix from the sanitized version
            original_prefix = prefix.replace('_', '/').replace('-', '.')

            policy_name = 'Unknown'
            if policy_type == 'DEPRIORITIZE':
                policy_name = 'Deprioritize Route'
            elif policy_type == 'INFLUENCE':
                policy_name = 'Advertise More-Specific'
            elif policy_type == 'COMMUNITY':
                policy_name = 'Set BGP Community'

            active_policies['bgp'].append({
                'type': policy_name,
                'neighbor': neighbor_ip,
                'prefix': original_prefix,
                # Add a unique ID for easy DOM manipulation/API calls
                'id': f"bgp-{policy_type}-{neighbor_ip}-{original_prefix}".replace('.', '_').replace('/', '_')
            })

    # --- New IGP Policy Detection Logic ---
    # Regex to find our tagged static routes
    igp_route_regex = re.compile(rf"ip route (\S+ \S+) Null0 tag {IGP_ROUTE_TAG}")
    # Regex to find which IGP is using our route-map
    igp_redist_regex = re.compile(rf"router (ospf|eigrp) (\d+)\s*\n(?: .*\n)*?.*?redistribute static route-map {IGP_ROUTE_MAP_NAME}")

    # Find all prefixes from tagged routes
    injected_routes_str = igp_route_regex.findall(config)

    # Find the IGP process that is using our route map
    igp_match = igp_redist_regex.search(config)
    if igp_match and injected_routes_str:
        protocol, process_id = igp_match.groups()
        for route_str in injected_routes_str:
            try:
                # Parse the route string '192.168.1.0 255.255.255.0' into an ip_network object
                net = ip_network(route_str.replace(' ', '/'), strict=False)
                prefix = net.with_prefixlen
                active_policies['igp'].append({
                    'type': 'IGP Route Injection',
                    'protocol': protocol.upper(),
                    'process_id': process_id,
                    'prefix': prefix,
                    'id': f"igp-{protocol}-{process_id}-{prefix}".replace('.', '_').replace('/', '_')
                })
            except ValueError:
                # Skip any routes that can't be parsed, though this shouldn't happen
                continue

    return active_policies


def withdraw_igp_route(prefix, protocol, process_id):
    """
    Withdraws a previously injected static route and cleans up the IGP config
    if it's the last injected route.
    """
    try:
        net = ip_network(prefix)
    except (ValueError, Exception) as e:
        return f"Error: Invalid prefix specified: {e}"

    # Get the current config to check if this is the last route
    config = send_config_to_router(['show running-config'])
    if "Error" in config:
        return "Error: Could not retrieve router config to check for other injected routes."

    # Find all tagged routes
    igp_route_regex = re.compile(rf"ip route (\S+ \S+) Null0 tag {IGP_ROUTE_TAG}")
    all_injected_routes_str = igp_route_regex.findall(config)

    # The command to remove the specific static route
    commands = [
        f'no ip route {net.network_address} {net.netmask} Null0 tag {IGP_ROUTE_TAG}',
    ]

    # Check if the route we are about to remove is the last one
    is_last_route = False
    if len(all_injected_routes_str) == 1:
        try:
            # Check if the single route in the config matches the one we're removing
            last_route_net = ip_network(all_injected_routes_str[0].replace(' ', '/'), strict=False)
            if last_route_net == net:
                is_last_route = True
        except ValueError:
            pass # Ignore if parsing fails

    if is_last_route:
        # If it is the last route, remove the redistribution and the route-map
        commands.extend([
            f'router {protocol.lower()} {process_id}',
            f' no redistribute static route-map {IGP_ROUTE_MAP_NAME}',
            'exit',
            f'no route-map {IGP_ROUTE_MAP_NAME}',
        ])

    commands.append('end')
    return send_config_to_router(commands)

def withdraw_deprioritize_route_for_neighbor(neighbor_ip, prefix):
    """
    Withdraws the AS_PATH prepending policy for a specific neighbor and prefix.
    """
    bgp_asn = os.getenv('BGP_ASN')
    prefix_sanitized = prefix.replace('/', '_').replace('.', '_')
    neighbor_sanitized = neighbor_ip.replace('.', '_')
    route_map_name = f"DEPRIORITIZE_{prefix_sanitized}_{neighbor_sanitized}"
    prefix_list_name = f"PL_{prefix_sanitized}"

    commands = [
        f'router bgp {bgp_asn}',
        f' no neighbor {neighbor_ip} route-map {route_map_name} out',
        'exit',
        f'no route-map {route_map_name}',
        f'no ip prefix-list {prefix_list_name}',
        'end'
    ]
    return send_config_to_router(commands)

def withdraw_influence_neighbor_with_more_specific(neighbor_ip, prefix):
    """
    Withdraws the more-specific advertisement for a specific neighbor and prefix.
    """
    bgp_asn = os.getenv('BGP_ASN')
    try:
        net = ip_network(prefix)
        subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
    except (ValueError, Exception) as e:
        return f"Error creating subnets: {e}"

    prefix_sanitized = prefix.replace('/', '_').replace('.', '_')
    neighbor_sanitized = neighbor_ip.replace('.', '_')
    route_map_name = f"INFLUENCE_{prefix_sanitized}_{neighbor_sanitized}"
    prefix_list_name = f"PL_MORE_SPECIFIC_{prefix_sanitized}"

    commands = [
        f'router bgp {bgp_asn}',
        f' no neighbor {neighbor_ip} route-map {route_map_name} out',
    ]
    commands.extend([f' no network {sub.with_prefixlen}' for sub in subnets])
    commands.extend([
        'exit',
        f'no route-map {route_map_name}',
        f'no ip prefix-list {prefix_list_name}',
        'end'
    ])
    return send_config_to_router(commands)

def withdraw_set_community_for_neighbor(neighbor_ip, prefix):
    """
    Withdraws a BGP community string policy for a specific neighbor and prefix.
    """
    bgp_asn = os.getenv('BGP_ASN')
    prefix_sanitized = prefix.replace('/', '_').replace('.', '_')
    neighbor_sanitized = neighbor_ip.replace('.', '_')
    route_map_name = f"COMMUNITY_{prefix_sanitized}_{neighbor_sanitized}"
    prefix_list_name = f"PL_COMMUNITY_{prefix_sanitized}"

    commands = [
        f'router bgp {bgp_asn}',
        f' no neighbor {neighbor_ip} route-map {route_map_name} out',
        'exit',
        f'no route-map {route_map_name}',
        f'no ip prefix-list {prefix_list_name}',
        'end'
    ]
    return send_config_to_router(commands)


def inject_igp_route(prefix, protocol, process_id):
    """
    Injects a tagged static route and redistributes it into an IGP process
    using a dedicated, safe route-map.
    """
    try:
        net = ip_network(prefix)
    except (ValueError, Exception) as e:
        return f"Error: Invalid prefix specified: {e}"

    if protocol.lower() not in ['ospf', 'eigrp']:
        return "Error: Invalid protocol specified. Must be 'ospf' or 'eigrp'."

    commands = [
        # Create/ensure the route-map for our tagged routes exists
        f'route-map {IGP_ROUTE_MAP_NAME} permit 10',
        f' match tag {IGP_ROUTE_TAG}',
        'exit',
        # Create the tagged static route pointing to Null0
        f'ip route {net.network_address} {net.netmask} Null0 tag {IGP_ROUTE_TAG}',
        # Enter the router configuration for the specified IGP
        f'router {protocol.lower()} {process_id}',
        # Redistribute static routes that match our route-map
        f' redistribute static route-map {IGP_ROUTE_MAP_NAME}',
        'end'
    ]

    return send_config_to_router(commands)

def influence_neighbor_with_more_specific(neighbor_ip, prefix):
    """
    Advertises more-specific prefixes to a single neighbor using a route-map.
    """
    bgp_asn = os.getenv('BGP_ASN')
    try:
        net = ip_network(prefix)
        subnets = list(net.subnets(new_prefix=net.prefixlen + 1))
    except (ValueError, Exception) as e:
        return f"Error creating subnets: {e}"

    # Sanitize inputs for command strings
    prefix_sanitized = prefix.replace('/', '_').replace('.', '_')
    neighbor_sanitized = neighbor_ip.replace('.', '_')
    route_map_name = f"INFLUENCE_{prefix_sanitized}_{neighbor_sanitized}"
    prefix_list_name = f"PL_MORE_SPECIFIC_{prefix_sanitized}"

    commands = [
        # Create the more-specific network statements so they exist in the BGP table
        f'router bgp {bgp_asn}',
    ]
    commands.extend([f' network {sub.with_prefixlen}' for sub in subnets])
    commands.extend([
        'exit',
        # Create a prefix-list to match the more-specifics
        f'ip prefix-list {prefix_list_name} permit {subnets[0].with_prefixlen}',
        f'ip prefix-list {prefix_list_name} permit {subnets[1].with_prefixlen}',
        # Create the route-map to only permit the more-specifics
        f'route-map {route_map_name} permit 10',
        f' match ip address prefix-list {prefix_list_name}',
        'exit',
        # Apply the route-map to the neighbor
        f'router bgp {bgp_asn}',
        f' neighbor {neighbor_ip} route-map {route_map_name} out',
        'end'
    ])

    return send_config_to_router(commands)

def withdraw_flowspec_rule(source_prefix=None, dest_prefix=None):
    """Constructs commands to withdraw a BGP Flowspec rule."""
    if not source_prefix and not dest_prefix:
        return "Error: At least one of source_prefix or dest_prefix must be specified."

    bgp_asn = os.getenv('BGP_ASN')
    commands = [f'router bgp {bgp_asn}', 'address-family ipv4 flowspec']

    rule_def = "no flow-spec"
    if dest_prefix:
        rule_def += f" destination {dest_prefix}"
    if source_prefix:
        rule_def += f" source {source_prefix}"

    commands.append(rule_def)
    commands.append("end")

    return send_config_to_router(commands)

def deploy_eem_sentry(prefix, unauthorized_asns):
    """
    Generates commands to deploy a Cisco EEM applet that watches for a BGP hijack.
    """
    if not prefix or not unauthorized_asns:
        return "Error: Prefix and at least one unauthorized ASN must be provided."

    # Sanitize inputs for use in command strings
    prefix_sanitized = prefix.replace('/', '_').replace('.', '_')
    applet_name = f"Sentry_{prefix_sanitized}"

    # Create a regex pattern for the unauthorized ASNs: (ASN1|ASN2|ASN3)$
    asn_pattern = f"({'|'.join(unauthorized_asns)})$"

    # The EEM applet script itself
    eem_script = [
        'event manager applet ' + applet_name,
        ' event syslog pattern "%BGP-5-ADJCHANGE: neighbor .* Up"',
        ' action 1.0 info type routername',
        ' action 2.0 cli command "enable"',
        ' action 3.0 cli command "show bgp ipv4 unicast ' + prefix + '"',
        ' action 4.0 regexp "' + asn_pattern + '" "$_cli_result" match',
        ' action 5.0 if $match eq "1"',
        '  action 5.1 syslog priority critical msg "HIJACK DETECTED on $_info_routername: Prefix ' + prefix + ' announced by unauthorized AS!"',
        ' action 6.0 end',
    ]

    return send_config_to_router(eem_script)

def deprioritize_route_for_neighbor(neighbor_ip, prefix, prepend_count=10):
    """
    Applies heavy AS_PATH prepending for a specific prefix to a single neighbor
    to make the route less preferable.
    """
    bgp_asn = os.getenv('BGP_ASN')
    # Sanitize inputs for command strings
    prefix_sanitized = prefix.replace('/', '_').replace('.', '_')
    neighbor_sanitized = neighbor_ip.replace('.', '_')
    route_map_name = f"DEPRIORITIZE_{prefix_sanitized}_{neighbor_sanitized}"

    commands = [
        # Create an ACL to match the specific prefix
        f'ip prefix-list PL_{prefix_sanitized} permit {prefix}',
        # Create the route-map
        f'route-map {route_map_name} permit 10',
        f' match ip address prefix-list PL_{prefix_sanitized}',
        f' set as-path prepend {" ".join([str(bgp_asn)] * prepend_count)}',
        'exit',
        # Create a second sequence to permit other routes without modification
        f'route-map {route_map_name} permit 20',
        'exit',
        # Apply the route-map to the neighbor
        f'router bgp {bgp_asn}',
        f' neighbor {neighbor_ip} route-map {route_map_name} out',
        'end'
    ]

    return send_config_to_router(commands)