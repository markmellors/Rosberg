from machine import UART
import sys
import time
import math

DEGREE_SYMBOL = chr(248)

gps_uart = UART(1, baudrate=115200)
gps_uart_buffer = b""  # persistent buffer

def parse_lat_lon(nmea):
    try:
        parts = nmea.split(',')
        lat = float(parts[2])
        lat_dir = parts[3]
        lon = float(parts[4])
        lon_dir = parts[5]

        lat_deg = int(lat / 100)
        lat_min = lat - lat_deg * 100
        latitude = lat_deg + lat_min / 60
        if lat_dir == 'S':
            latitude = -latitude

        lon_deg = int(lon / 100)
        lon_min = lon - lon_deg * 100
        longitude = lon_deg + lon_min / 60
        if lon_dir == 'W':
            longitude = -longitude

        return latitude, longitude
    except (IndexError, ValueError):
        return None, None

def extract_position(nmea):
    if nmea.startswith('$GNGGA'):
        lat, lon = parse_lat_lon(nmea)
        if lat and lon:
            return "Lat: {:.6f}".format(lat), "Lon: {:.6f}".format(lon)
    return None, None

def parse_fix_quality(nmea):
    try:
        fix = int(nmea.split(',')[6])
        return {
            0: "Fix: None",
            1: "Fix: GPS",
            2: "Fix: DGPS",
            4: "Fix: RTK Fixed",
            5: "Fix: RTK Float"
        }.get(fix, f"Fix: {fix}")
    except:
        return "Fix: Unknown"

def parse_heading(nmea):
    try:
        heading = float(nmea.split(',')[1])
        return f"Head: {heading:.2f}{DEGREE_SYMBOL}"
    except:
        return None

def parse_time(nmea):
    try:
        raw_time = nmea.split(',')[1]
        if len(raw_time) >= 6:
            return f"{raw_time[0:2]}:{raw_time[2:4]}:{raw_time[4:6]} UTC"
    except:
        pass
    return None

def process_buffer(buffer, latest):
    try:
        decoded = buffer.decode('ascii', 'ignore')
        for sentence in decoded.replace('\n', '').split('$'):
            if not sentence:
                continue
            nmea = '$' + sentence.strip()
            if nmea.startswith('$GNGGA'):
                lat_str, lon_str = extract_position(nmea)
                if lat_str and lon_str:
                    latest['lat'] = lat_str
                    latest['lon'] = lon_str
                latest['time'] = parse_time(nmea)
                latest['fix'] = parse_fix_quality(nmea)
                latest['last_update_ticks'] = time.ticks_ms()
            elif nmea.startswith('$GNVTG'):
                heading_str = parse_heading(nmea)
                if heading_str:
                    latest['heading'] = heading_str
    except Exception as e:
        sys.print_exception(e)
        print("Buffer processing error:", repr(e))
        print("buffer: {buffer}")
        print("decoded: {decoded}")

def read_and_parse(latest):
    global gps_uart_buffer
    if gps_uart.any():
        try:
            gps_uart_buffer += gps_uart.read(gps_uart.any())
            if b'\n' in gps_uart_buffer:
                chunks = gps_uart_buffer.split(b'\n')
                for chunk in chunks[:-1]:
                    process_buffer(chunk + b'\n', latest)
                gps_uart_buffer = chunks[-1]  # retain incomplete part
        except Exception as e:
            print("UART read exception:", e)
            
            

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # in meters

def calculate_bearing(lat1, lon1, lat2, lon2):
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    x = math.sin(delta_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1)*math.cos(phi2)*math.cos(delta_lambda)
    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360  # normalize

def approx_distance(lat1, lon1, lat2, lon2):
    # Approximates distance in meters for small deltas
    R = 6371000  # Earth radius in meters
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return R * math.sqrt(x*x + y*y)

def write_rtcm(data: bytes):
    try:
        gps_uart.write(data)
    except Exception as e:
        print("UART write exception:", e)
