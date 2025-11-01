from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import os
import json
import requests
from ..database import get_db_connection
from ..logic.mitigation_logic import (
    mitigate_hijack, withdraw_mitigation, depeer_neighbor, blackhole_route,
    signal_upstream, challenge_with_rpki, apply_flowspec_rule,
    withdraw_flowspec_rule, deploy_eem_sentry, deprioritize_route_for_neighbor,
    influence_neighbor_with_more_specific, inject_igp_route,
    get_active_influence_policies, withdraw_deprioritize_route_for_neighbor,
    withdraw_influence_neighbor_with_more_specific, withdraw_igp_route,
    set_community_for_neighbor, withdraw_set_community_for_neighbor,
    provision_neighbor, shutdown_neighbor, activate_neighbor
)
from ..logic.audit_logic import find_orphaned_objects, cleanup_orphaned_objects, analyze_bgp_best_practices

bp = Blueprint('main', __name__)

def load_config():
    # Assuming config.json is in the root directory, one level above the package
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

@bp.route('/')
def index():
    latest_summary = None
    recent_hijacks = None
    recent_flaps = None
    db_error = None
    config = load_config()
    active_policies = {'bgp': [], 'igp': []}

    try:
        db = get_db_connection()
        latest_summary = list(db.bgp_summary.aggregate([
            {'$sort': {'timestamp': -1}},
            {'$group': {'_id': '$neighbor', 'doc': {'$first': '$$ROOT'}}},
            {'$replaceRoot': {'newRoot': '$doc'}}
        ]))
        recent_hijacks = list(db.hijack_alerts.find().sort('timestamp', -1).limit(10))
        recent_flaps = list(db.bgp_flaps.find().sort('timestamp', -1).limit(10))
        active_policies = get_active_influence_policies()
    except Exception as e:
        db_error = f"Error connecting to the database: {e}"

    return render_template('index.html',
                           bgp_summary=latest_summary,
                           hijack_alerts=recent_hijacks,
                           bgp_flaps=recent_flaps,
                           db_error=db_error,
                           config=config,
                           active_policies=active_policies)

@bp.route('/update_config', methods=['POST'])
def update_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    config['auto_mitigate'] = 'auto_mitigate' in request.form
    config['prepend_on_mitigate'] = 'prepend_on_mitigate' in request.form
    config['prepend_count'] = int(request.form.get('prepend_count', 3))
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    return redirect(url_for('main.index'))

@bp.route('/history')
def history():
    db = get_db_connection()
    all_hijacks = list(db.hijack_alerts.find().sort('timestamp', -1))
    return render_template('history.html', hijack_alerts=all_hijacks)

@bp.route('/automation_log')
def automation_log():
    db = get_db_connection()
    logs = list(db.automation_log.find().sort('timestamp', -1))
    return render_template('automation_log.html', logs=logs)

RPKI_API_URL = "https://stat.ripe.net/data/rpki-validation/data.json"

def get_rpki_status(prefix, asn):
    params = {'resource': asn, 'prefix': prefix}
    try:
        response = requests.get(RPKI_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('validating_roas', [{}])[0].get('validity', 'not-found')
    except (requests.exceptions.RequestException, IndexError) as e:
        print(f"Error querying RPKI API: {e}")
        return "error"

@bp.route('/rpki_helper')
def rpki_helper():
    config = load_config()
    monitored_prefixes = config.get('monitored_prefixes', [])
    authorized_as = config.get('authorized_as')
    rpki_data = [{'prefix': p, 'status': get_rpki_status(p, authorized_as)} for p in monitored_prefixes]
    return render_template('rpki_helper.html', rpki_data=rpki_data, config=config)

@bp.route('/analytics')
def analytics():
    hijacks_over_time = []
    top_offenders = []
    db_error = None
    try:
        db = get_db_connection()
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        hijacks_over_time = list(db.hijack_alerts.aggregate([
            {'$match': {'timestamp': {'$gte': thirty_days_ago}}},
            {'$group': {'_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}}, 'count': {'$sum': 1}}},
            {'$sort': {'_id': 1}}
        ]))
        top_offenders = list(db.hijack_alerts.aggregate([
            {'$group': {'_id': '$hijacking_as', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]))
    except Exception as e:
        db_error = f"Error connecting to the database: {e}"
    hijacks_json = json.dumps(hijacks_over_time)
    return render_template('analytics.html', hijacks_over_time=hijacks_json, top_offenders=top_offenders, db_error=db_error)

@bp.route('/withdraw_bgp_influence', methods=['POST'])
def withdraw_bgp_influence():
    neighbor = request.form.get('neighbor')
    prefix = request.form.get('prefix')
    policy_type = request.form.get('policy_type')
    if policy_type == 'Deprioritize Route':
        withdraw_deprioritize_route_for_neighbor(neighbor, prefix)
    elif policy_type == 'Advertise More-Specific':
        withdraw_influence_neighbor_with_more_specific(neighbor, prefix)
    elif policy_type == 'Set BGP Community':
        withdraw_set_community_for_neighbor(neighbor, prefix)
    return redirect(url_for('main.index'))

@bp.route('/withdraw_igp_influence', methods=['POST'])
def withdraw_igp_influence():
    protocol = request.form.get('protocol')
    process_id = request.form.get('process_id')
    prefix = request.form.get('prefix')
    if all([protocol, process_id, prefix]):
        withdraw_igp_route(prefix, protocol, process_id)
    return redirect(url_for('main.index'))

@bp.route('/influence_igp', methods=['POST'])
def influence_igp():
    prefix = request.form.get('igp_prefix')
    protocol = request.form.get('igp_protocol')
    process_id = request.form.get('igp_process_id')
    inject_igp_route(prefix, protocol, process_id)
    return redirect(url_for('main.index'))

@bp.route('/influence_bgp', methods=['POST'])
def influence_bgp():
    neighbor_ip = request.form.get('neighbor_ip')
    prefix = request.form.get('prefix')
    action = request.form.get('action')
    if action == 'deprioritize':
        deprioritize_route_for_neighbor(neighbor_ip, prefix)
    elif action == 'more_specific':
        influence_neighbor_with_more_specific(neighbor_ip, prefix)
    elif action == 'set_community':
        communities = request.form.get('communities')
        set_community_for_neighbor(neighbor_ip, prefix, communities)
    return redirect(url_for('main.index'))

@bp.route('/on_router_defense', methods=['GET', 'POST'])
def on_router_defense():
    config = load_config()
    output = None
    if request.method == 'POST':
        prefix = request.form.get('prefix')
        unauthorized_asns_str = request.form.get('unauthorized_asns')
        unauthorized_asns = [asn.strip() for asn in unauthorized_asns_str.split(',')]
        output = deploy_eem_sentry(prefix, unauthorized_asns)
    return render_template('on_router_defense.html', config=config, output=output)

@bp.route('/flowspec', methods=['POST'])
def flowspec():
    source_prefix = request.form.get('source_prefix')
    dest_prefix = request.form.get('destination_prefix')
    action = request.form.get('action')
    if action == 'apply':
        apply_flowspec_rule(source_prefix, dest_prefix)
    elif action == 'withdraw':
        withdraw_flowspec_rule(source_prefix, dest_prefix)
    return redirect(url_for('main.index'))

@bp.route('/reroute', methods=['POST'])
def reroute():
    action = request.form.get('action')
    prefix = request.form.get('prefix')
    bgp_asn = os.getenv('BGP_ASN')
    if action == 'mitigate':
        mitigate_hijack(prefix, bgp_asn)
    elif action == 'withdraw_mitigation':
        withdraw_mitigation(prefix, bgp_asn)
    return redirect(url_for('main.index'))

@bp.route('/depeer', methods=['POST'])
def depeer():
    neighbor_ip = request.form.get('neighbor_ip')
    depeer_neighbor(neighbor_ip)
    return redirect(url_for('main.index'))

@bp.route('/blackhole', methods=['POST'])
def blackhole():
    prefix = request.form.get('blackhole_prefix')
    blackhole_route(prefix)
    return redirect(url_for('main.index'))

@bp.route('/rtbh', methods=['POST'])
def rtbh():
    prefix = request.form.get('prefix')
    config = load_config()
    communities = config.get('rtbh_communities', [])
    signal_upstream(prefix, communities)
    return redirect(url_for('main.index'))

@bp.route('/neighbors', methods=['GET', 'POST'])
def neighbors():
    if request.method == 'POST':
        action = request.form.get('action')
        neighbor_ip = request.form.get('neighbor_ip')
        if action == 'provision':
            remote_as = request.form.get('remote_as')
            description = request.form.get('description')
            provision_neighbor(neighbor_ip, remote_as, description)
        elif action == 'shutdown':
            shutdown_neighbor(neighbor_ip)
        elif action == 'activate':
            activate_neighbor(neighbor_ip)
        return redirect(url_for('main.neighbors'))
    db = get_db_connection()
    all_neighbors = list(db.bgp_summary.aggregate([
        {'$sort': {'timestamp': -1}},
        {'$group': {'_id': '$neighbor', 'doc': {'$first': '$$ROOT'}}},
        {'$replaceRoot': {'newRoot': '$doc'}}
    ]))
    return render_template('neighbors.html', neighbors=all_neighbors)

@bp.route('/auditing', methods=['GET', 'POST'])
def auditing():
    if request.method == 'POST':
        orphaned_route_maps = request.form.getlist('orphaned_route_maps')
        orphaned_prefix_lists = request.form.getlist('orphaned_prefix_lists')
        cleanup_orphaned_objects(orphaned_route_maps, orphaned_prefix_lists)
        return redirect(url_for('main.auditing'))
    config = get_active_influence_policies() # Re-using this to get config
    orphaned_objects = find_orphaned_objects(config)
    best_practice_analysis = analyze_bgp_best_practices(config)
    return render_template('auditing.html', orphaned_objects=orphaned_objects, best_practice_analysis=best_practice_analysis)