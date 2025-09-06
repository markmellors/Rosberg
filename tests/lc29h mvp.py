from machine import UART, Pin
import time

# Set TX and RX pins before using UART
Pin(4, Pin.OUT)  # TX to GPS RX
Pin(5, Pin.IN)   # RX from GPS TX

# Now initialize UART
gps_uart = UART(1, baudrate=115200)  # 

# Send a test NMEA command (optional)
# gps_uart.write(b'$PMTK605*31\r\n')  # just an example for testing

# Read and print lines from GPS
def parse_lat_lon(lat_str, lat_dir, lon_str, lon_dir):
    # Convert raw NMEA lat/lon to decimal degrees
    lat_deg = int(lat_str[:2])
    lat_min = float(lat_str[2:])
    lat = lat_deg + lat_min / 60.0
    if lat_dir == 'S':
        lat = -lat

    lon_deg = int(lon_str[:3])
    lon_min = float(lon_str[3:])
    lon = lon_deg + lon_min / 60.0
    if lon_dir == 'W':
        lon = -lon

    return lat, lon

def extract_position(nmea_line):
    if nmea_line.startswith('$GNGGA') or nmea_line.startswith('$GNRMC'):
        parts = nmea_line.split(',')
        if parts[2] and parts[4]:  # Ensure lat/lon present
            lat, lon = parse_lat_lon(parts[2], parts[3], parts[4], parts[5])
            return lat, lon
    return None

# Example usage with your data stream:
while True:
    if gps_uart.any():
        line = gps_uart.readline()
        if line:
            try:
                decoded = line.decode('utf-8').strip()
                position = extract_position(decoded)
                if position:
                    print("Latitude:", position[0], "Longitude:", position[1])
            except Exception as e:
                print("Parse error:", e)

