from ipaddress import ip_network
import os
from netmiko import ConnectHandler
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
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