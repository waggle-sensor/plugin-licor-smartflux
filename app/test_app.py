import pytest
from unittest.mock import MagicMock, patch
import socket
import timeout_decorator
from collections import OrderedDict
from unittest import mock  # Import mock correctly

# Assuming the code is in a file named 'app.py' in the same directory
from app import connect, extract_data, parse_data, publish_data, run  # Import parse_data, publish_data, run


def test_extract_data():
    data_string = '(Data (Seconds 1709240296)(Nanoseconds 0)(Ndx 261930)(DiagVal 255)(DiagVal2 0)(DiagBits 0)(Date 2024-02-29)(Time 20:58:16:000)(CO2Raw 0.149896)(H2ORaw 0.0241019)(CO2D 19.2597)(CO2MG 847.427)(H2OD 147.998)(H2OG 2.66396)(Temp 23.7733)(Pres 100.009)(Cooler 2.02839)(ChopperCooler 2.38329)(SFVin 0)(CO2MF 475.393)(H2OMF 3.65308)(DewPt -6.93847)(CO2SS 100.631)(H2OAW 48186.6)(H2OAWO 46839.6)(CO2AW 28094.1)(CO2AWO 37474.4)(DSIVin 23.8762))(CH4Data (SECONDS 0)(NANOSECONDS 0)(CH4 0)(CH4D 0)(RSSI 0)(DIAG 0))(SonicData (U -1.5)(V 2.5)(W 0.5)(TS 20.5)(SOS 340.5)(AnemDiag -9999))'
    expected_data = {
        'Seconds': 1709240296.0, 'Nanoseconds': 0.0, 'Ndx': 261930.0, 'Date': '2024-02-29', 'Time': '20:58:16:000',
        'CO2Raw': 0.149896, 'H2ORaw': 0.0241019, 'CO2D': 19.2597, 'CO2MG': 847.427, 'H2OD': 147.998, 'H2OG': 2.66396,
        'Temp': 23.7733, 'Pres': 100.009, 'Cooler': 2.02839, 'CO2MF': 475.393, 'H2OMF': 3.65308, 'DewPt': -6.93847,
        'CO2SS': 100.631, 'H2OAW': 48186.6, 'H2OAWO': 46839.6, 'CO2AW': 28094.1, 'CO2AWO': 37474.4,
        'U': -1.5, 'V': 2.5, 'W': 0.5, 'TS': 20.5, 'SOS': 340.5
    }
    parsed_data = extract_data(data_string)
    assert parsed_data == expected_data, f"Expected: {expected_data}, but got: {parsed_data}"


@patch('app.extract_data')
@patch('time.sleep', return_value=None)
@patch('socket.socket')
def test_parse_data(mock_socket_cls, mock_sleep, mock_extract_data):
    args_mock = MagicMock()
    mock_tcp_socket = MagicMock()
    mock_socket_cls.return_value = mock_tcp_socket
    valid_data_string = '(Data (Seconds 123))' # Minimal valid data string
    mock_tcp_socket.recv.return_value = valid_data_string.encode('utf-8')
    expected_parsed_data = {'Seconds': 123.0} # Expected output from extract_data
    mock_extract_data.return_value = expected_parsed_data

    parsed_data = parse_data(args_mock, mock_tcp_socket)

    assert parsed_data == expected_parsed_data, f"Expected parse_data to return: {expected_parsed_data}, but got: {parsed_data}"
    mock_extract_data.assert_called_once() # Verify extract_data was called


@patch('app.run_copy_and_upload')
@patch('time.sleep', return_value=None)
@patch('socket.socket')
def test_parse_data_run(mock_socket_cls, mock_sleep, mock_run_copy_and_upload):
    args_mock = MagicMock()
    mock_tcp_socket = MagicMock()
    mock_socket_cls.return_value = mock_tcp_socket
    run_status_done_string = '(Data (RunStatus done))'
    mock_tcp_socket.recv.return_value = run_status_done_string.encode('utf-8')

    parsed_data = parse_data(args_mock, mock_tcp_socket)

    assert parsed_data is None, "Expected parse_data to return None when 'RunStatus done' is received"
    mock_run_copy_and_upload.assert_called_once_with(args_mock, run_status_done_string) 


@patch('app.Plugin')
def test_publish_data(mock_plugin_cls):
    mock_plugin_instance = MagicMock()
    mock_plugin_cls.return_value.__enter__.return_value = mock_plugin_instance
    data = {'Seconds': 123, 'CO2Raw': 100.5, 'H2ORaw': 200.5}
    data_names_mock = OrderedDict([("CO2Raw", "co2.raw"), ("H2ORaw", "h2o.raw")]) # Minimal data_names for this test
    meta_mock = { # Minimal meta for this test
        "sensor": "LI7500DS/uSonic-3",
        "units": {"co2.raw": "unit", "h2o.raw": "unit"},
        "description": {"co2.raw": "Raw CO2", "h2o.raw": "Raw H2O"}
    }
    publish_data(mock_plugin_instance, data, data_names_mock, meta_mock)

    mock_plugin_instance.publish.assert_any_call(
        'co2.raw', 100.5, meta=mock.ANY, timestamp=123000000000) # Use mock.ANY
    mock_plugin_instance.publish.assert_any_call(
        'h2o.raw', 200.5, meta=mock.ANY, timestamp=123000000000) # Use mock.ANY
    assert mock_plugin_instance.publish.call_count == 2 # Verify publish called twice
    published_args = [call[0][0] for call in mock_plugin_instance.publish.call_args_list]
    assert 'co2.raw' in published_args
    assert 'h2o.raw' in published_args


