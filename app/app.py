import socket
import logging
from waggle.plugin import Plugin
from collections import OrderedDict
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect_to_smartflux(ip_address, port):
    """
    Establishes a TCP connection to Licor SmartFlux.

    :param ip_address: The IP address of SmartFlux.
    :param port: The port number for the TCP connection.
    :return: A socket object.
    """
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((ip_address, port))
    except Exception as e:
        logging.error(f"Error connecting to TCP device: {e}")
        raise
    return tcp_socket



def read_and_parse_data(tcp_socket):
    try:
        data = tcp_socket.recv(4096).decode("utf-8")
        # Initialize the dictionary to hold parsed data
        parsed_data = {}
        # Regular expressions to extract each parameter
        patterns = {
            'Seconds': r'\(Seconds (\d+)\)',
            'Nanoseconds': r'\(Nanoseconds (\d+)\)',
            'Ndx': r'\(Ndx (\d+)\)',
            'DiagVal': r'\(DiagVal (\d+)\)',
            'DiagVal2': r'\(DiagVal2 (\d+)\)',
            'DiagBits': r'\(DiagBits (\d+)\)',
            'Date': r'\(Date ([\d-]+)\)',
            'Time': r'\(Time ([\d:]+)\)',
            'CO2Raw': r'\(CO2Raw ([\d.]+)\)',
            'H2ORaw': r'\(H2ORaw ([\d.]+)\)',
            'CO2D': r'\(CO2D ([\d.]+)\)',
            'CO2MG': r'\(CO2MG ([\d.]+)\)',
            'H2OD': r'\(H2OD ([\d.]+)\)',
            'H2OG': r'\(H2OG ([\d.]+)\)',
            'Temp': r'\(Temp ([\d.]+)\)',
            'Pres': r'\(Pres ([\d.]+)\)',
            'Cooler': r'\(Cooler ([\d.]+)\)',
            'ChopperCooler': r'\(ChopperCooler ([\d.]+)\)',
            'SFVin': r'\(SFVin ([\d.]+)\)',
            'CO2MF': r'\(CO2MF ([\d.]+)\)',
            'H2OMF': r'\(H2OMF ([\d.]+)\)',
            'DewPt': r'\(DewPt ([\d.-]+)\)',
            'CO2SS': r'\(CO2SS ([\d.]+)\)',
            'H2OAW': r'\(H2OAW ([\d.]+)\)',
            'H2OAWO': r'\(H2OAWO ([\d.]+)\)',
            'CO2AW': r'\(CO2AW ([\d.]+)\)',
            'CO2AWO': r'\(CO2AWO ([\d.]+)\)',
            'DSIVin': r'\(DSIVin ([\d.]+)\)',
            # Add more fields as needed
        }
        
        # Loop through the patterns and extract data
        for key, pattern in patterns.items():
            match = re.search(pattern, data)
            if match:
                # Convert to float if it looks like a number, otherwise keep as string
                try:
                    parsed_data[key] = float(match.group(1))
                except ValueError:
                    parsed_data[key] = match.group(1)
        
        return parsed_data
    except Exception as e:
        print(f"Error reading/parsing data: {e}")
        raise



def publish_data(plugin, data, data_names, meta):
    """
    Publishes data to the plugin.

    :param plugin: Plugin object for publishing data.
    :param data: Dictionary of data to be published.
    :param data_names: Mapping of data keys to their publishing names.
    :param meta: Metadata associated with the data.
    """
    for key, value in data.items():
        if key in data_names:
            try:
                meta_data = {
                    "missing": "-9999.0",
                    "units": meta["units"][data_names[key]],
                    "description": meta["description"][data_names[key]],
                    "name": data_names[key],
                    "sensor": meta["sensor"],
                }
                plugin.publish(data_names[key], value, meta=meta_data)
            except KeyError as e:
                logging.error(f"Error: Missing key in meta data - {e}")

def run_tcp_device_interface(ip_address, port, data_names, meta):
    """
    Runs the TCP device interface for reading and publishing data.

    :param ip_address: The IP address of the device.
    :param port: The port number for the TCP connection.
    :param data_names: Mapping of data keys to their publishing names.
    :param meta: Metadata associated with the data.
    """
    with Plugin() as plugin:
        tcp_socket = connect_to_smartflux(ip_address, port)

        try:
            while True:
                data = read_and_parse_data(tcp_socket)
                logging.info(f"Data: {data}")
                publish_data(plugin, data, data_names, meta)
        except Exception as e:
            logging.error(f"Error in TCP device interface: {e}")
        finally:
            tcp_socket.close()

if __name__ == "__main__":
    # Define the mapping of data keys to their publishing names and metadata
    data_names = OrderedDict([
        ("CO2Raw", "co2.raw"),
        ("H2ORaw", "h2o.raw"),

    ])
    meta = {
        "sensor": "LI7500DS",
        "units": {
            "co2.raw": "unit",
            "h2o.raw": "unit",
            # Add more fields as needed
        },
        "description": {
            "co2.raw": "Raw CO2 measurement",
            "h2o.raw": "Raw H2O measurement",
            # Add more fields as needed
        },
    }

    ip_address = '10.42.0.107'
    port = 7200

    run_tcp_device_interface(ip_address, port, data_names, meta)