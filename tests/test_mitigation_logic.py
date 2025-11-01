import pytest
from bgp_defense_tool.logic import mitigation_logic

def test_shutdown_neighbor(mocker):
    """Test that shutdown_neighbor generates the correct Cisco IOS commands."""
    mock_send = mocker.patch('bgp_defense_tool.logic.mitigation_logic.send_config_to_router')

    neighbor_ip = "1.1.1.1"
    mitigation_logic.shutdown_neighbor(neighbor_ip)

    # Define the expected sequence of commands
    expected_commands = [
        'router bgp 65535',
        ' neighbor 1.1.1.1 shutdown',
        'end'
    ]

    # Assert that the mocked function was called with the correct commands
    mock_send.assert_called_once_with(expected_commands)

def test_activate_neighbor(mocker):
    """Test that activate_neighbor generates the correct Cisco IOS commands."""
    mock_send = mocker.patch('bgp_defense_tool.logic.mitigation_logic.send_config_to_router')

    neighbor_ip = "2.2.2.2"
    mitigation_logic.activate_neighbor(neighbor_ip)

    expected_commands = [
        'router bgp 65535',
        ' no neighbor 2.2.2.2 shutdown',
        'end'
    ]

    mock_send.assert_called_once_with(expected_commands)

def test_provision_neighbor(mocker):
    """Test that provision_neighbor generates the correct Cisco IOS commands with a description."""
    mock_send = mocker.patch('bgp_defense_tool.logic.mitigation_logic.send_config_to_router')

    neighbor_ip = "3.3.3.3"
    remote_as = "65500"
    description = "Test Peer"
    mitigation_logic.provision_neighbor(neighbor_ip, remote_as, description)

    expected_commands = [
        'router bgp 65535',
        ' neighbor 3.3.3.3 remote-as 65500',
        ' neighbor 3.3.3.3 description Test Peer',
        'end'
    ]

    assert mock_send.call_count == 2
    mock_send.assert_any_call(expected_commands)

def test_provision_neighbor_no_description(mocker):
    """Test that provision_neighbor generates the correct commands without a description."""
    mock_send = mocker.patch('bgp_defense_tool.logic.mitigation_logic.send_config_to_router')

    neighbor_ip = "4.4.4.4"
    remote_as = "65501"
    mitigation_logic.provision_neighbor(neighbor_ip, remote_as)

    expected_commands = [
        'router bgp 65535',
        ' neighbor 4.4.4.4 remote-as 65501',
        'end'
    ]

    assert mock_send.call_count == 2
    mock_send.assert_any_call(expected_commands)
