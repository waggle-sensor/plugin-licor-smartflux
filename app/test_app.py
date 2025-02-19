import pytest
from unittest.mock import MagicMock, patch
import socket
import timeout_decorator
from collections import OrderedDict

# Assuming the code is in a file named 'app.py' in the same directory
from app import connect, extract_data  # Import the extract_data function


# Define a shorter TIMEOUT_SECONDS for tests (if needed for timeout tests)
TIMEOUT_SECONDS = 0.1  # e.g., 0.1 seconds for faster tests


def test_extract_data_valid_string():
    """
    Test that extract_data function correctly parses a valid data string.
    """
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