import pytest
import socket
from bgp_defense_tool.monitors import ripestat_monitor

def test_get_abuseipdb_score_with_ip_lookup(mocker):
    """Test the full workflow including the IP lookup for an ASN."""
    # Mock the DNS lookup to return a predictable IP
    mocker.patch('socket.gethostbyname', return_value="123.123.123.123")

    # Mock the API call
    mock_api_get = mocker.patch('requests.get')
    mock_api_get.return_value.json.return_value = {'data': {'abuseConfidenceScore': 80}}

    api_key = "test_key"
    asn = "64496"

    # This is what's called in the main loop
    ip_to_check = ripestat_monitor.get_ip_for_asn(asn)
    score = ripestat_monitor.get_abuseipdb_score(ip_to_check, api_key)

    # Verify the DNS lookup was attempted
    socket.gethostbyname.assert_called_once_with("as64496.net")

    # Verify the correct IP was used in the API call
    mock_api_get.assert_called_once_with(
        ripestat_monitor.ABUSEIPDB_API_URL,
        headers={'Key': api_key, 'Accept': 'application/json'},
        params={'ipAddress': "123.123.123.123", 'maxAgeInDays': '90'}
    )

    assert score == 80

def test_get_abuseipdb_score_no_api_key():
    """Test that the function returns None when no API key is provided."""
    score = ripestat_monitor.get_abuseipdb_score("12345", None)
    assert score is None
