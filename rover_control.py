
from machine import Pin, PWM, time_pulse_us
import time
from pin_defs import RC_STEERING, RC_MODE, STEER_PWM
from gps_utils import approx_distance, calculate_bearing
import system_state

FULL_LEFT = 1048
FULL_RIGHT = 2043
NEUTRAL_STEER = 1500
AUTO_THRESHOLD = 1500
TARGET_DISTANCE = 100

wp_index_override_state = {
    "was_high": False
}

# Steering servo setup
steer_pwm = PWM(Pin(STEER_PWM))
steer_pwm.freq(50)

rc_pins = {
    "steering": Pin(RC_STEERING, Pin.IN),
    "mode":     Pin(RC_MODE, Pin.IN),
}

rc_inputs = {
    "steering": 1500,
    "mode":     1000,
}

def read_rc_inputs():
    for key, pin in rc_pins.items():
        try:
            pulse = time_pulse_us(pin, 1, 20000)  # 25ms timeout
            if 900 < pulse < 2200:  # sanity check
                rc_inputs[key] = pulse
        except OSError:
            # timeout or invalid pulse
            pas
            
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))

def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def steering_pid(dist, target, last_error, integral):
    P, I, D = 0.3, 0, 0
    error = dist - target
    derivative = error - last_error
    integral += error
    return constrain(P * error + I * integral + D * derivative, -90, 90)

def set_esc_throttle(value):  # -1 to 1
    us = int(map_range(value, -1, 1, 1000, 2000))
    duty = int(us * 65535 / 20000)
    esc_pwm.duty_u16(duty)

def set_steering_angle(angle):  # 0 to 180 deg
    us = int(map_range(angle, -30, 30, 1100, 1900))  # adjust for your servo
    duty = int(us * 65535 / 20000)
    steer_pwm.duty_u16(duty)


def extract_lat_lon():
    try:
        lat_str = system_state.gps_data.get("lat", "").split(": ")[1]
        lon_str = system_state.gps_data.get("lon", "").split(": ")[1]
        return float(lat_str), float(lon_str)
    except:
        return None, None

def extract_heading():
    try:
        heading_str = system_state.gps_data.get("heading", "").split(": ")[1].replace("ø", "")
        return float(heading_str)
    except:
        return None

def check_waypoint_advance():
    # RC override logic: look for rising edge
    steer_us = rc_inputs["steering"]
    nav_distance = system_state.nav_distance

    should_advance = False

    if steer_us > 1750:
        if not wp_index_override_state["was_high"]:
            wp_index_override_state["was_high"] = True
            should_advance = True  # rising edge
    else:
        wp_index_override_state["was_high"] = False

    if nav_distance is not None and nav_distance < 2:
        should_advance = True

    if should_advance:
        system_state.current_waypoint_index = (system_state.current_waypoint_index + 1) % system_state.wp_count
        print("Switching to waypoint", system_state.current_waypoint_index)

def update():
    read_rc_inputs()
    
    steer_in = rc_inputs["steering"]
    mode_in = rc_inputs["mode"]
    
    if mode_in > AUTO_THRESHOLD:
        check_waypoint_advance()
        lat, lon = extract_lat_lon()
        heading = extract_heading()

        if lat is not None and lon is not None and heading is not None:
            waypoint = system_state.waypoints[system_state.current_waypoint_index]
            target_lat, target_lon = waypoint

            distance = approx_distance(lat, lon, target_lat, target_lon)
            target_bearing = calculate_bearing(lat, lon, target_lat, target_lon)

            heading_error = (target_bearing - heading + 540) % 360 - 180  # Normalize to [-180, 180]

            # For now, use heading error directly as "distance" input to PID
            angle = steering_pid(heading_error, 0, heading_error, 0)
            system_state.nav_distance = distance
            system_state.nav_heading_error = heading_error
            #print("distance: ", distance)
            #print("heading: ", heading_error)
            system_state.display_lines[9] = f"WP: {system_state.current_waypoint_index}"
        else:
            angle = 0  # fallback
    else:
        angle = map_range(steer_in, FULL_LEFT, FULL_RIGHT, -30, 30)
        system_state.display_lines[10] = "RC"
        
    if system_state.steering_enabled:
        set_steering_angle(angle)


