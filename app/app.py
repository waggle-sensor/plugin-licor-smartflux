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
import timeout_decorator
import sys
TIMEOUT_SECONDS = 30

# for file transfer
import threading
import subprocess
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run(args, data_names, meta):
    """
    Main function to operate the SmartFlux data reader.

    :param ip_address: IP address of the SmartFlux device.
    :param port: Port number for the connection.
    :param data_names: Data keys mapping.
    :param meta: Metadata for the data.
    """
    tcp_socket = None
    with Plugin() as plugin:
        try:
            tcp_socket = connect(args)
            while True:
                data = parse_data(args, plugin, tcp_socket)
                logging.info(f"Data: {data}")
                publish_data(plugin, data, data_names, meta)
        except timeout_decorator.TimeoutError:
            logging.error(f"Unknown_Timeout")
            plugin.publish('exit.status', 'Unknown_Timeout')
            sys.exit("Timeout error while waiting for data.")
        except Exception as e:
            logging.error(f"{e}")
        finally:
            if tcp_socket:
                tcp_socket.close()
            logging.info("Connection closed.")



def connect(args):
    """
    Establishes a connection to a Licor SmartFlux device.

    :param ip_address: IP address of the SmartFlux device.
    :param port: Port number for the connection.
    :return: A socket object for communication.
    """
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.connect((args.ip, args.port))
    except Exception as e:
        logging.error(f"Connection failed: {e}. Check device, network, or Waggle node restrictions.")
        raise
    return tcp_socket



@timeout_decorator.timeout(TIMEOUT_SECONDS, use_signals=True)
def parse_data(args, plugin,  tcp_socket):
    """
    Receives and decodes data from a SmartFlux device.

    :param tcp_socket: The socket object connected to SmartFlux.
    :return: A dictionary of parsed data.
    """
    try:
        data = tcp_socket.recv(4096).decode("utf-8")
    except Exception as e:
        logging.error(f"Error getting data: {e}")
        raise

    if not "RunStatus done" in data:
       return(extract_data(data))
    else: # if run status done found
        print('Flux computation status completed, calling copy_flux_files()')
        run_copy_and_upload(args, data)
        return None
                

def extract_data(data):
    parsed_data = {}
    # RegEx for SmartFlux data extraction
    patterns = {
        'Seconds': r'\(Seconds (\d+)\)',
        'Nanoseconds': r'\(Nanoseconds (\d+)\)',
        'Ndx': r'\(Ndx (\d+)\)',
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
        'CO2MF': r'\(CO2MF ([\d.]+)\)',
        'H2OMF': r'\(H2OMF ([\d.]+)\)',
        'DewPt': r'\(DewPt ([\d.-]+)\)',
        'CO2SS': r'\(CO2SS ([\d.]+)\)',
        'H2OAW': r'\(H2OAW ([\d.]+)\)',
        'H2OAWO': r'\(H2OAWO ([\d.]+)\)',
        'CO2AW': r'\(CO2AW ([\d.]+)\)',
        'CO2AWO': r'\(CO2AWO ([\d.]+)\)',
        # Sonic variables
        'U': r'\(U ([-\d.]+)\)',
        'V': r'\(V ([-\d.]+)\)',
        'W': r'\(W ([-\d.]+)\)',
        'TS': r'\(TS ([-\d.]+)\)',
        'SOS': r'\(SOS ([-\d.]+)\)',
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, data)
        if match:
            try:
                parsed_data[key] = float(match.group(1))
            except ValueError:
                parsed_data[key] = match.group(1)
    
    return parsed_data


def publish_data(plugin, data, data_names, meta):
    """
    Publishes SmartFlux data to the Waggle plugin.

    :param plugin: Plugin object for publishing.
    :param data: Data dictionary to be published.
    :param data_names: Mapping of data keys to publishing names.
    :param meta: Metadata for the data.
    """
    if data:
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


def run_copy_and_upload(args, data):
    """
    Initiate file transfer in thread.
    """
    last_file_match = re.search(r'\(LastFile ([^\)]+)\)', data)
    if last_file_match:
        last_file = last_file_match.group(1)
        scp_thread = threading.Thread(target=copy_and_upload, args=(args, last_file))
        scp_thread.start()


def copy_and_upload(args, last_file):
    """Copy .ghg and .zip files from licor, upload, and delete."""
    # get the name, remove ext
    base_filename = last_file.split('.')[0]
    local_paths, remote_paths = create_file_paths(args, base_filename)
    Path(args.local_dir).mkdir(exist_ok=True)

    for ext in [".ghg", ".zip"]:
        copy_file(args, local_paths[ext], remote_paths[ext])
        upload_and_cleanup(local_paths[ext])


def create_file_paths(args, base_filename):
    """Generate file paths."""

    remote_data_dir = args.licor_dir
    year, month = re.match(r"(\d{4})-(\d{2})", base_filename).groups()

    remote_paths = {
        ".ghg": os.path.join(remote_data_dir, "raw", year, month, f"{base_filename}.ghg"),
        ".zip": os.path.join(remote_data_dir, "results", year, month, f"{base_filename}.zip"),
    }

    local_paths = {
        ".ghg": os.path.join(args.local_dir, f"{base_filename}.ghg"),
        ".zip": os.path.join(args.local_dir, f"{base_filename}.zip"),
    }

    return local_paths, remote_paths


def copy_file(args, local_path, remote_path):
    """Copy files."""
    scp_cmd = f"sshpass -p {args.passwd} scp {args.user}@{args.ip}:{remote_path} {local_path}"
    try:
        subprocess.run(scp_cmd, shell=True, check=True)
        logging.info(f"Copied to {local_path}.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Copy failed: {e}")


def upload_and_cleanup(local_path):
    """Upload and delete file from container."""
    if Path(local_path).exists():
        with Plugin() as plugin:
            plugin.upload_file(local_path)
            logging.info(f"Uploaded {local_path}.")
            os.remove(local_path)
            logging.info(f"Deleted {local_path}.")
    else:
        logging.error(f"{local_path} missing.")



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="TCP Device Interface for SmartFlux")
    parser.add_argument('--ip', type=str, required=True, help='SmartFlux IP address')
    parser.add_argument('--port', type=int, default=7200, help='TCP connection port (default: 7200)')
    parser.add_argument('--sensor', type=str, default="LI7500DS + Gill", help='Gas Analyzer and Sonic Sensor names (default: LI7500DS + Gill)')
    parser.add_argument('--interval', type=int, default=1, help='Data publishing interval in seconds (default: 1)')
    parser.add_argument('--user', type=str, default="licor", help='licor smartflux user id')
    parser.add_argument('--passwd', type=str, default="licor", help='licor smartflux password')
    parser.add_argument('--local_dir', type=str, default="/data/", help='container directory for saving flux files [temp]')
    parser.add_argument('--licor_dir', type=str, default="/home/licor/data/", help='licor smartflux data directory.')

    args = parser.parse_args()

    data_names = OrderedDict([
    ("Seconds", "time.seconds"),
    ("Nanoseconds", "time.nanoseconds"),
    ("Ndx", "index"),
    ("Date", "date"),
    ("Time", "time"),
    ("CO2Raw", "co2.raw"),
    ("H2ORaw", "h2o.raw"),
    ("CO2D", "co2.density"),
    ("CO2MG", "co2.mg_per_m3"),
    ("H2OD", "h2o.density"),
    ("H2OG", "h2o.g_per_m3"),
    ("Temp", "temperature"),
    ("Pres", "pressure"),
    ("Cooler", "cooler"),
    ("CO2MF", "co2.mole_fraction"),
    ("H2OMF", "h2o.mole_fraction"),
    ("DewPt", "dew_point"),
    ("CO2SS", "co2.signal_strength"),
    ("H2OAW", "h2o.absolute_water"),
    ("H2OAWO", "h2o.absolute_water_offset"),
    ("CO2AW", "co2.absolute_water"),
    ("CO2AWO", "co2.absolute_water_offset"),
    # Sonic variables
    ("U", "sonic.u"),
    ("V", "sonic.v"),
    ("W", "sonic.w"),
    ("TS", "sonic.temperature"),
    ("SOS", "sonic.speed_of_sound"),
])

    meta = {
    "sensor": args.sensor,
    "units": {
        "time.seconds": "s",
        "time.nanoseconds": "ns",
        "index": "unit",
        "date": "YYYY-MM-DD",
        "time": "HH:MM:SS",
        "co2.raw": "unit",
        "h2o.raw": "unit",
        "co2.density": "mg/m^3",
        "co2.mg_per_m3": "mg/m^3",
        "h2o.density": "g/m^3",
        "h2o.g_per_m3": "g/m^3",
        "temperature": "°C",
        "pressure": "kPa",
        "cooler": "unit",
        "co2.mole_fraction": "ppm",
        "h2o.mole_fraction": "ppm",
        "dew_point": "°C",
        "co2.signal_strength": "unit",
        "h2o.absolute_water": "unit",
        "h2o.absolute_water_offset": "unit",
        "co2.absolute_water": "unit",
        "co2.absolute_water_offset": "unit",
        # Sonic
        "sonic.u": "m/s",
        "sonic.v": "m/s",
        "sonic.w": "m/s",
        "sonic.temperature": "°C",
        "sonic.speed_of_sound": "m/s",
    },
    "description": {
        "time.seconds": "Epoch time in seconds",
        "time.nanoseconds": "Nanoseconds to complement epoch seconds",
        "index": "Data index",
        "date": "Date of data capture",
        "time": "Time of data capture",
        "co2.raw": "Raw CO2 measurement",
        "h2o.raw": "Raw H2O measurement",
        "co2.density": "CO2 density",
        "co2.mg_per_m3": "CO2 in mg per cubic meter",
        "h2o.density": "H2O density",
        "h2o.g_per_m3": "H2O in grams per cubic meter",
        "temperature": "Ambient temperature",
        "pressure": "Atmospheric pressure",
        "cooler": "Cooler status",
        "co2.mole_fraction": "CO2 mole fraction",
        "h2o.mole_fraction": "H2O mole fraction",
        "dew_point": "Dew point temperature",
        "co2.signal_strength": "CO2 signal strength",
        "h2o.absolute_water": "Absolute water content",
        "h2o.absolute_water_offset": "Absolute water content offset",
        "co2.absolute_water": "CO2 absolute water content",
        "co2.absolute_water_offset": "CO2 absolute water content offset",
        # Sonic
        "sonic.u": "Sonic U-component of wind speed",
        "sonic.v": "Sonic V-component of wind speed",
        "sonic.w": "Sonic vertical wind speed",
        "sonic.temperature": "Sonic temperature",
        "sonic.speed_of_sound": "Speed of sound",
    },
    }

    try:
        run(args, data_names, meta)
    except KeyboardInterrupt:
        logging.info("Interrupted by user, shutting down.")
    except Exception as e:
        logging.error(f"Startup failed: {e}")
    finally:
        logging.info("Application terminated.")

