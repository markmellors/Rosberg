import time
display_enabled = False
logging = False
log_file = None
display_lines = [""] * 12

wifi_connected = False
wifi_ssid = ""
wifi_ip = ""
ntrip_connected = False
last_ntrip_rx_ticks = None  # ticks_ms() of last RTCM/NTRIP data seen

gps_data = {
    "time": "",
    "lat": "",
    "lon": "",
    "heading": "",
    "fix": "",
    "last_update_ticks": ""
}

# system_state.py
waypoints = []
wp_count = 0
current_waypoint_index = 0
nav_distance = None
nav_heading_error = 0
steering_enabled = True
waypoints = []
current_waypoint_index = 0

def update_display_lines():
    display_lines[0] = gps_data.get("lat", "")
    display_lines[1] = gps_data.get("lon", "")
    display_lines[2] = gps_data.get("heading", "")
    display_lines[3] = gps_data.get("fix", "")
    display_lines[4] = f"GPS UTC: {gps_data.get('time', '')}"

    # Remove old dt line, use the lower lines for connectivity
    display_lines[5]  = f"WiFi: {'UP' if wifi_connected else 'DOWN'} {wifi_ssid}"
    display_lines[6] = f"IP: {wifi_ip}" if wifi_connected else "IP: ---"
    display_lines[7] = f"NTRIP: {'OK' if ntrip_connected else 'NO DATA'}"
    
    display_lines[8] = "logging" if logging else ""



