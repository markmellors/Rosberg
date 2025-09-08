import time
import network_utils
import gps_utils
import display_utils
import logging_utils
import button_handler
import web_server
import system_state
import _thread
import rover_control
import waypoint_utils
from machine import Pin
import pin_defs

system_state.display_lines[0] = "Starting..."

# Load waypoints
system_state.waypoints = waypoint_utils.load_waypoints()
system_state.wp_count = len(system_state.waypoints)
print("Loaded waypoints:", system_state.waypoints)

display_utils.update_display()

# Connect to WiFi and display IP
ip = network_utils.connect_wifi()
system_state.display_lines[6] = "IP: " + str(ip)

# Start web server thread
_thread.start_new_thread(web_server.start_file_server, (ip, 80))

# Connect to NTRIP caster
ntrip_socket = network_utils.connect_ntrip()

last_display = time.ticks_ms()

gps_utils.disable_pps()

# Main loop
while True:	
    gps_data = gps_utils.read_and_parse(system_state.gps_data)
    button_handler.check_buttons(system_state.gps_data)
    logging_utils.log_if_needed(system_state.gps_data)
    rover_control.update()
    
    if ntrip_socket:
        chunk = network_utils.poll_ntrip_socket(ntrip_socket)
        if isinstance(chunk, (bytes, bytearray)) and chunk:
            gps_utils.write_rtcm(chunk)
            
    if system_state.display_enabled and time.ticks_diff(time.ticks_ms(), last_display) > 200:
        system_state.update_display_lines()
        display_utils.update_display()
        last_display = time.ticks_ms()

    if web_server.check_shutdown():
        web_server.stop()
        break
    time.sleep_ms(2)