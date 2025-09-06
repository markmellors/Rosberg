# waypoint_utils.py
def load_waypoints(filename="waypoints.csv"):
    waypoints = []
    try:
        with open(filename, "r") as f:
            for line in f:
                if "," in line:
                    parts = line.strip().split(",")
                    try:
                        lat = float(parts[0])
                        lon = float(parts[1])
                        waypoints.append((lat, lon))
                    except ValueError:
                        print("Invalid waypoint:", line)
    except Exception as e:
        print("Error loading waypoints:", e)
    return waypoints
