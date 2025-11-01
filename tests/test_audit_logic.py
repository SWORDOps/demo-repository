import pytest
from bgp_defense_tool.logic import audit_logic

MOCK_CONFIG = """
router bgp 65535
 neighbor 1.1.1.1 remote-as 65501
 neighbor 1.1.1.1 route-map DEPRIORITIZE_192.0.2.0_24_1.1.1.1 out
 neighbor 2.2.2.2 remote-as 65502
 neighbor 2.2.2.2 maximum-prefix 1000
!
route-map DEPRIORITIZE_192.0.2.0_24_1.1.1.1 permit 10
 match ip address prefix-list PL_192.0.2.0_24
!
route-map COMMUNITY_10.0.0.0_8_3.3.3.3 permit 10
 match ip address prefix-list PL_10.0.0.0_8
!
ip prefix-list PL_192.0.2.0_24 permit 192.0.2.0/24
ip prefix-list PL_10.0.0.0_8 permit 10.0.0.0/8
ip prefix-list PL_ORPHANED permit 172.16.0.0/16
"""

def test_find_orphaned_objects():
    """Test that orphaned objects are correctly identified from a mock config."""
    orphaned = audit_logic.find_orphaned_objects(config=MOCK_CONFIG)

    assert "COMMUNITY_10.0.0.0_8_3.3.3.3" in orphaned['route-maps']
    assert "PL_ORPHANED" in orphaned['prefix-lists']
    assert len(orphaned['route-maps']) == 1
    assert len(orphaned['prefix-lists']) == 1

def test_analyze_bgp_best_practices():
    """Test that BGP best practice violations are correctly identified."""
    analysis = audit_logic.analyze_bgp_best_practices(config=MOCK_CONFIG)

    assert len(analysis['missing_max_prefix']) == 2
    assert {'neighbor_ip': '1.1.1.1', 'remote_as': '65501'} in analysis['missing_max_prefix']
    assert {'neighbor_ip': '2.2.2.2', 'remote_as': '65502'} in analysis['missing_max_prefix']

def test_cleanup_orphaned_objects(mocker):
    """Test that the cleanup function generates the correct 'no' commands."""
    mock_send = mocker.patch('bgp_defense_tool.logic.audit_logic.send_config_to_router')

    route_maps_to_clean = ["COMMUNITY_10.0.0.0_8_3.3.3.3"]
    prefix_lists_to_clean = ["PL_ORPHANED"]

    audit_logic.cleanup_orphaned_objects(route_maps_to_clean, prefix_lists_to_clean)

    expected_commands = [
        "no route-map COMMUNITY_10.0.0.0_8_3.3.3.3",
        "no ip prefix-list PL_ORPHANED",
        "end"
    ]

    mock_send.assert_called_once_with(expected_commands)
