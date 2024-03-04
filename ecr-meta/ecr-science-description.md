# Plugin for LI-COR smartFlux system

# Li7500DS
The Li7500DS is a state-of-the-art open path gas analyzer designed by LI-COR Biosciences, specifically engineered for high precision measurements of carbon dioxide (CO2) and water vapor (H2O) concentrations in the atmosphere.

## Usage in Eddy Covariance Measurements
The Li7500DS and sonic anemometer are used for eddy covariance system to measure fluxes of CO2 and H2O in the atmosphere. This method involves calculating the covariance between vertical wind speed (obtained from the sonic anemometer) and the scalars CO2 and H2O concentrations measured by the Li7500DS. The setup allows for direct, real-time monitoring of gas exchange, providing valuable insights into ecosystem, boundary layer fluxes, carbon and water cycle in the atmosphere.

## Waggle Plugin for Li7500DS via SmartFlux
The plugin collects data from the LiCOR SmartFlux system over TCP/IP networks. It enables the reading, parsing, and publishing of the data to the Waggle beehive for further analysis and storage. The plugin connects to the SmartFlux device using its IP address and port number. It then listens for data transmitted over the network. Incoming data from SmartFlux is parsed using regular expressions extracting CO2 and H2O conc., temperature, pressure. Parsed data is published with appropriate metadata

### Example Command

```bash
python3 /app/app.py --ip 192.168.1.100 --port 7200 --sensor LI7500DS
```

- --ip: IP address of the SmartFlux device.
- --port: Port number for TCP/IP connection (default: 7200).
- --sensor: Type of sensor used, defaulting to LI7500DS for specific gas analysis.