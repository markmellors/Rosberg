import time
import system_state

def start_logging(gps_data):
    gps_time = gps_data.get("time", "")
    if gps_time and gps_time != "---":
        time_str = gps_time.replace(":", "").replace(" UTC", "")
        filename = f"log_{time_str}.csv"
    else:
        t = time.localtime()
        filename = "log_{:04d}{:02d}{:02d}_{:02d}{:02d}{:02d}.csv".format(*t[:6])

    try:
        system_state.log_file = open(filename, "w")
        system_state.log_file.write("time,latitude,longitude,heading\n")  # CSV header
        system_state.logging = True
        print(f"Logging started: {filename}")
    except Exception as e:
        print("Error opening log file:", e)

def stop_logging():
    if system_state.log_file:
        system_state.log_file.close()
        system_state.log_file = None
    system_state.logging = False

def log_if_needed(gps_data): 
    if system_state.logging and gps_data.get("fix"):
        try:
            time_str = gps_data.get('time', '').replace(" UTC", "")
            lat = gps_data.get('lat', '').split(": ")[1] if "Lat: " in gps_data.get('lat', '') else ''
            lon = gps_data.get('lon', '').split(": ")[1] if "Lon: " in gps_data.get('lon', '') else ''
            heading = gps_data.get('heading', '').split(": ")[1].replace("ø", "") if "Head: " in gps_data.get('heading', '') else ''
            line = f"{time_str},{lat},{lon},{heading}\n"
            system_state.log_file.write(line)
        except Exception as e:
            print("Log write error:", e)
