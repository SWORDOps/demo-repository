import re
from .mitigation_logic import send_config_to_router

def find_orphaned_objects(config=None):
    """
    Scans the router's configuration to find route-maps and prefix-lists
    created by this tool that are no longer in use.
    """
    if config is None:
        config = send_config_to_router(['show running-config'])
        if "Error" in config:
            return {'error': 'Could not retrieve router configuration.'}

    orphaned_objects = {'route-maps': [], 'prefix-lists': []}

    # Find all route-maps and prefix-lists created by our tool
    tool_route_map_names = set(re.findall(r"route-map (DEPRIORITIZE_\S+|INFLUENCE_\S+|COMMUNITY_\S+)", config))
    tool_prefix_list_names = set(re.findall(r"ip prefix-list (PL_\S+)", config))

    # 1. Find orphaned route-maps
    for rm_name in tool_route_map_names:
        # A route-map is orphaned if its name doesn't appear in any 'neighbor ... route-map ...' line
        if f"route-map {rm_name} out" not in config:
            orphaned_objects['route-maps'].append(rm_name)

    # 2. Find orphaned prefix-lists
    for pl_name in tool_prefix_list_names:
        # A prefix-list is orphaned if its name doesn't appear in any 'match ip address prefix-list ...' line
        # within a route-map definition.
        if f"match ip address prefix-list {pl_name}" not in config:
            orphaned_objects['prefix-lists'].append(pl_name)

    return orphaned_objects

def cleanup_orphaned_objects(route_maps_to_clean, prefix_lists_to_clean):
    """
    Generates and sends commands to remove specified orphaned route-maps and prefix-lists.
    """
    commands = []
    for rm in route_maps_to_clean:
        commands.append(f"no route-map {rm}")
    for pl in prefix_lists_to_clean:
        commands.append(f"no ip prefix-list {pl}")

    if not commands:
        return "No objects specified for cleanup."

    commands.append('end')
    return send_config_to_router(commands)

def analyze_bgp_best_practices(config=None):
    """
    Analyzes the BGP configuration for adherence to security best practices,
    like the 'maximum-prefix' setting on eBGP neighbors.
    """
    if config is None:
        config = send_config_to_router(['show running-config'])
        if "Error" in config:
            return {'error': 'Could not retrieve router configuration.'}

    analysis_results = {'missing_max_prefix': []}

    # Regex to find all configured neighbors and their remote-as
    bgp_config_match = re.search(r"router bgp (\d+)", config)
    if not bgp_config_match:
        return analysis_results # No BGP configuration found

    local_as = bgp_config_match.group(1)

    # Find all neighbors within the BGP config section
    neighbor_configs = re.findall(r"neighbor (\S+) remote-as (\d+)", config)

    for neighbor_ip, remote_as in neighbor_configs:
        if remote_as != local_as: # This is an eBGP peer
            # Check if this neighbor has a maximum-prefix command
            neighbor_block_regex = re.compile(rf"neighbor {re.escape(neighbor_ip)}[\s\S]*?(?=neighbor|\Z)")
            neighbor_block_match = neighbor_block_regex.search(config)

            if neighbor_block_match:
                neighbor_block = neighbor_block_match.group(0)
                if 'maximum-prefix' not in neighbor_block:
                    analysis_results['missing_max_prefix'].append({
                        'neighbor_ip': neighbor_ip,
                        'remote_as': remote_as
                    })

    return analysis_results