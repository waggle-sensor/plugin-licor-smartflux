"""
The waggle plugin designed to interface with Licor SmartFlux over TCP/IP connections. 
It reads, parses, and publishes data from SmartFlux to the beehive.

@ToDo
1. It should change sonic wind data sensor name.
2. Time need to be tested for accuracy.
"""

import socket
import logging
from waggle.plugin import Plugin
from collections import OrderedDict
import re
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def connect(ip_address, port):
    """
    Establishes a connection to a Licor SmartFlux device.

    :param ip_address: IP address of the SmartFlux device.
    :param port: Port number for the connection.
    :return: A socket object for communication.
    """
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((ip_address, port))
    except Exception as e:
        logging.error(f"Connection failed: {e}. Check device, network, or Waggle node restrictions.")
        raise
    return tcp_socket

def parse_data(tcp_socket):
    """
    Receives and decodes data from a SmartFlux device.

    :param tcp_socket: The socket object connected to SmartFlux.
    :return: A dictionary of parsed data.
    """
    try:
        data = tcp_socket.recv(4096).decode("utf-8")
        parsed_data = {}
        # RegEx for SmartFlux data extraction
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
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, data)
            if match:
                try:
                    parsed_data[key] = float(match.group(1))
                except ValueError:
                    parsed_data[key] = match.group(1)
        
        return parsed_data
    except Exception as e:
        logging.error(f"Error processing data: {e}")
        raise

def publish_data(plugin, data, data_names, meta):
    """
    Publishes SmartFlux data to the Waggle plugin.

    :param plugin: Plugin object for publishing.
    :param data: Data dictionary to be published.
    :param data_names: Mapping of data keys to publishing names.
    :param meta: Metadata for the data.
    """

    timestamp_nanoseconds = int(data.get('Seconds', 0) * 1e9) # 0 if not found

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
                plugin.publish(data_names[key], value, meta=meta_data, 
                               timestamp=timestamp_nanoseconds)
            except KeyError as e:
                logging.error(f"Metadata key missing: {e}")

def run(ip_address, port, data_names, meta):
    """
    Main function to operate the SmartFlux data reader.

    :param ip_address: IP address of the SmartFlux device.
    :param port: Port number for the connection.
    :param data_names: Data keys mapping.
    :param meta: Metadata for the data.
    """
    tcp_socket = None
    try:
        with Plugin() as plugin:
            tcp_socket = connect(ip_address, port)
            while True:
                data = parse_data(tcp_socket)
                logging.info(f"Data: {data}")
                publish_data(plugin, data, data_names, meta)
    except Exception as e:
        logging.error(f"{e}")
    finally:
        if tcp_socket:
            tcp_socket.close()
        logging.info("Connection closed.")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="TCP Device Interface for SmartFlux")
        parser.add_argument('--ip', type=str, required=True, help='SmartFlux IP address')
        parser.add_argument('--port', type=int, default=7200, help='TCP connection port (default: 7200)')
        parser.add_argument('--sensor', type=str, default="LI7500DS", help='Sensor type (default: LI7500DS)')

        args = parser.parse_args()

        data_names = OrderedDict([
            ("CO2Raw", "co2.raw"),
            ("H2ORaw", "h2o.raw"),
            ("CO2D", "co2.density"),
            ("CO2MG", "co2.mg_per_m3"),
            ("H2OD", "h2o.density"),
            ("H2OG", "h2o.g_per_m3"),
            ("CO2MF", "co2.mole_fraction"),
            ("H2OMF", "h2o.mole_fraction"),
            ("CO2SS", "co2.signal_strength"),
            ("H2OAW", "h2o.absolute_water"),
            ("H2OAWO", "h2o.absolute_water_offset"),
            ("CO2AW", "co2.absolute_water"),
            ("CO2AWO", "co2.absolute_water_offset"),
        ])
        meta = {
            "sensor": args.sensor, 
            "units": {
                "co2.raw": "unit",
                "h2o.raw": "unit",
                "co2.density": "mg/m^3",
                "co2.mg_per_m3": "mg/m^3",
                "h2o.density": "g/m^3",
                "h2o.g_per_m3": "g/m^3",
                "co2.mole_fraction": "ppm",
                "h2o.mole_fraction": "ppm",
                "co2.signal_strength": "unit",
                "h2o.absolute_water": "unit",
                "h2o.absolute_water_offset": "unit",
                "co2.absolute_water": "unit",
                "co2.absolute_water_offset": "unit",
            },
            "description": {
                "co2.raw": "Raw CO2 measurement",
                "h2o.raw": "Raw H2O measurement",
                "co2.density": "CO2 density",
                "co2.mg_per_m3": "CO2 in mg per cubic meter",
                "h2o.density": "H2O density",
                "h2o.g_per_m3": "H2O in grams per cubic meter",
                "co2.mole_fraction": "CO2 mole fraction",
                "h2o.mole_fraction": "H2O mole fraction",
                "co2.signal_strength": "CO2 signal strength",
                "h2o.absolute_water": "Absolute water content",
                "h2o.absolute_water_offset": "Absolute water content offset",
                "co2.absolute_water": "CO2 absolute water content",
                "co2.absolute_water_offset": "CO2 absolute water content offset",
            },
        }

        run(args.ip, args.port, data_names, meta)
    except KeyboardInterrupt:
        logging.info("Interrupted by user, shutting down.")
    except Exception as e:
        logging.error(f"Startup failed: {e}")
    finally:
        logging.info("Application terminated.")

