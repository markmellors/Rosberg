from machine import UART
import sys
import time
import math


MAX_POINTS = 60 
_track = []                
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
        return f"Head: {heading:.2f}°"   # use a proper Unicode degree
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
                    lat_f, lon_f = parse_lat_lon(nmea)
                    if lat_f is not None and lon_f is not None:
                        add_fix(lat_f, lon_f)  # ts auto-filled
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

def _nmea_checksum(s: str) -> str:
    cs = 0
    for ch in s:
        cs ^= ord(ch)
    return f"*{cs:02X}\r\n"

def _send_pair(payload: str, wait_ms=600) -> str:
    """
    Send a $PAIR... command and return any short ASCII response.
    Example payload: "PAIR752,2,100"
    """
    cmd = f"${payload}{_nmea_checksum(payload)}"
    try:
        gps_uart.write(cmd)
    except Exception as e:
        print("GPS write failed:", e)
        return ""

    t0 = time.ticks_ms()
    resp = b""
    while time.ticks_diff(time.ticks_ms(), t0) < wait_ms:
        try:
            if gps_uart.any():
                resp += gps_uart.read(gps_uart.any() or 1)
            time.sleep_ms(10)
        except Exception:
            break

    text = ""
    try:
        text = resp.decode("ascii", "ignore")
    except Exception:
        pass
    if text:
        print("PAIR resp:", text)
    return text

def _send_pqtm(body: str, wait_ms=600) -> str:
    # (kept in case your firmware supports PQTM)
    cmd = f"${body}{_nmea_checksum(body)}"
    try:
        gps_uart.write(cmd)
    except Exception as e:
        print("GPS write failed:", e)
        return ""
    t0 = time.ticks_ms()
    resp = b""
    while time.ticks_diff(time.ticks_ms(), t0) < wait_ms:
        try:
            if gps_uart.any():
                resp += gps_uart.read(gps_uart.any() or 1)
            time.sleep_ms(10)
        except Exception:
            break
    try:
        text = resp.decode("ascii", "ignore")
        if text:
            print("PQTM resp:", text)
        return text
    except Exception:
        return ""

def disable_pps():
    """
    LC29H PAIR command to configure PPS.
    Per your doc: $PAIR752,<PPSType>,<PPSPulseWidth>*CS
    We'll try to DISABLE PPS with PPSType=0 (common 'off' selector) and width=0.
    Success is acknowledged by: $PAIR001,752,0*CS
    """
    txt = _send_pair("PAIR752,0,0", wait_ms=800)
    ok = "$PAIR001,752,0" in txt
    if ok:
        print("PAIR752: PPS disabled (ack okay).")
        return True

    print("PAIR752 disable not acknowledged; trying PQTM fallback...")
    # Fallback for firmwares that use PQTM (if supported on your unit)
    txt2 = _send_pqtm("PQTMCFGPPS,W,1,0,100,1,1,0", wait_ms=800)
    if "$PQTMCFGPPS" in txt2 or "OK" in txt2:
        print("PQTM fallback sent.")
    return ok


def add_fix(lat, lon, ts=None):
    global _track
    _track.append({"lat": lat, "lon": lon, "t": ts or int(time.time())})  # <-- time.time()
    if len(_track) > MAX_POINTS:
        _track = _track[-MAX_POINTS:]

def current_fix():
    """Return the latest fix or None."""
    return _track[-1] if _track else None

def as_geojson():
    """Return a tiny GeoJSON payload: points + line."""
    coords = [[p["lon"], p["lat"]] for p in _track]  # GeoJSON is [lon,lat]
    features = []
    if _track:
        # breadcrumb points (sparse to reduce payload if needed)
        features.append({
            "type": "Feature",
            "properties": {"kind": "points"},
            "geometry": {"type": "MultiPoint", "coordinates": coords}
        })
        # connecting line
        features.append({
            "type": "Feature",
            "properties": {"kind": "track"},
            "geometry": {"type": "LineString", "coordinates": coords}
        })
    return {"type": "FeatureCollection", "features": features}
