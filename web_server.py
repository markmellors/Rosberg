import os
import socket
import system_state
import time

# NEW: pull in your GPS helpers you said you added
import gps_utils  # expects: current_fix(), as_geojson(), (optionally add_fix)

# --- HTML: status+map page ----------------------------------------------------
HTML_INDEX = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Pico Rover</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
    integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">
  <style>
    :root { --pad: 10px; }
    html, body { height: 100%; margin: 0; font: 14px/1.3 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
    #wrap { display:flex; flex-direction:column; height:100%; }
    #topbar { padding: var(--pad); display:flex; gap:12px; flex-wrap:wrap; align-items:center; border-bottom:1px solid #ddd; }
    #topbar .box { padding: 6px 10px; border: 1px solid #ddd; border-radius: 8px; }
    #map { flex: 1 1 auto; min-height: 300px; }
    code { background:#f5f5f5; padding:2px 6px; border-radius:6px; }
    #logs { padding: var(--pad); border-top:1px solid #eee; }
    button { margin-right: 8px; }
  </style>
</head>
<body>
<div id="wrap">
  <div id="topbar">
    <div class="box">GPS Time: <code id="gps_time">–</code></div>
    <div class="box">Fix: <code id="fix">–</code></div>
    <div class="box">Lat: <code id="lat">–</code></div>
    <div class="box">Lon: <code id="lon">–</code></div>
    <div class="box">Heading: <code id="heading">–</code></div>
    <div class="box">Δt (ms): <code id="dt">–</code></div>
    <div class="box">Logging: <code id="logging">–</code></div>
    <div class="box">Steering PWM: <code id="steer">–</code></div>
    <div class="box">Current WP: <code id="wp">–</code></div>
    <div class="box">Heading Error: <code id="herr">–</code></div>
    <form action="/steering" method="get" style="margin-left:auto">
      <button name="state" value="on">Enable Steering</button>
      <button name="state" value="off">Disable Steering</button>
    </form>
  </div>

  <div id="map"></div>

  <div id="logs">
    <h3>Log Files</h3>
    <ul id="file_list"></ul>
    <p><a href="/shutdown">Shutdown Pico</a></p>
  </div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
  integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
<script>
  // Basemaps
  const esri = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "Tiles &copy; Esri" }
  );
  const osm = L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }
  );

  const map = L.map("map", { layers: [esri] }).setView([0, 0], 2);
  const trackLine = L.polyline([], { weight: 3 }).addTo(map);
  const crumbLayer = L.layerGroup().addTo(map);
  const posMarker = L.circleMarker([0, 0], { radius: 6 }).addTo(map);

  L.control.layers({ "Aerial (Esri)": esri, "Streets (OSM)": osm },
                   { "Track": trackLine, "Breadcrumbs": crumbLayer },
                   { collapsed: true }).addTo(map);

  let initialized = false;

  async function refresh() {
    try {
      // Status JSON from Pico (lat/lon/t taken from gps_utils.current_fix on server)
      const s = await fetch("/status.json", { cache: "no-store" }).then(r => r.json());
      // GeoJSON trail from Pico (gps_utils.as_geojson on server)
      const t = await fetch("/track.json", { cache: "no-store" }).then(r => r.json());

      // Update topbar values
      if (s) {
        // these fields are echoed from server in status.json "extra"
        document.getElementById("gps_time").textContent = s.extra && s.extra.time || "–";
        document.getElementById("fix").textContent      = s.extra && s.extra.fix  || "–";
        document.getElementById("lat").textContent      = (s.lat  != null) ? s.lat.toFixed(6) : "–";
        document.getElementById("lon").textContent      = (s.lon  != null) ? s.lon.toFixed(6) : "–";
        document.getElementById("heading").textContent  = s.extra && s.extra.heading || "–";
        document.getElementById("dt").textContent       = s.extra && s.extra.dt || "–";
        document.getElementById("logging").textContent  = s.extra && s.extra.logging || "–";
        document.getElementById("steer").textContent    = s.extra && s.extra.steering || "–";
        document.getElementById("wp").textContent       = s.extra && s.extra.wp || "–";
        document.getElementById("herr").textContent     = s.extra && s.extra.herr || "–";

        if (s.lat != null && s.lon != null) {
          const p = [s.lat, s.lon];
          posMarker.setLatLng(p);
          if (!initialized) { map.setView(p, 17); initialized = true; }
        }

        // Update file list (lightweight echo from server)
        const files = (s.extra && s.extra.files) || [];
        const ul = document.getElementById("file_list");
        ul.innerHTML = "";
        for (const f of files) {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = "/" + f; a.textContent = f; li.appendChild(a); ul.appendChild(li);
        }
      }

      // Track drawing
      crumbLayer.clearLayers();
      if (t && t.features) {
        let line = [];
        for (const f of t.features) {
          if (f.geometry.type === "LineString") {
            line = f.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
          } else if (f.geometry.type === "MultiPoint") {
            const pts = f.geometry.coordinates.map(([lng, lat]) => [lat, lng]);
            const step = Math.max(1, Math.floor(pts.length / 100));
            for (let i = 0; i < pts.length; i += step) {
              L.circleMarker(pts[i], { radius: 3 }).addTo(crumbLayer);
            }
          }
        }
        trackLine.setLatLngs(line);
      }
    } catch (e) {
      console && console.warn && console.warn("refresh error", e);
    }
  }

  refresh();
  setInterval(refresh, 5000);
</script>
</body></html>
"""

should_exit = False  # Shared exit flag
shutdown_requested = False


def start_file_server(ip="0.0.0.0", port=80):
    global should_exit, shutdown_requested
    s = socket.socket()
    s.bind((ip, port))
    s.listen(1)
    print(f"Web server started at http://{ip}:{port}")
    
    while not should_exit:
        try:
            conn, addr = s.accept()
            request = conn.recv(1024).decode("utf-8")

            # ---- Steering control: handle and short-circuit to home page ----
            if request.startswith("GET /steering"):
                if "state=off" in request:
                    system_state.steering_enabled = False
                elif "state=on" in request:
                    system_state.steering_enabled = True
                # Re-serve the updated index instead of trying to serve a file
                serve_index(conn)
                continue
            # -----------------------------------------------------------------

            # NEW: lightweight JSON endpoints before file parsing
            if request.startswith("GET /status.json"):
                serve_status_json(conn)
                continue
            if request.startswith("GET /track.json"):
                serve_track_json(conn)
                continue

            requested_file = parse_filename_from_request(request)
            if requested_file == "shutdown":
                shutdown_requested = True
                serve_shutdown_page(conn)
            elif requested_file:
                serve_file(conn, requested_file)
            else:
                serve_index(conn)

        except Exception as e:
            print("Web server error:", e)
        finally:
            conn.close()
    print("Web server stopped.")
    s.close()
    
def parse_filename_from_request(request):
    try:
        lines = request.split("\r\n")
        get_line = lines[0]
        _, path, _ = get_line.split()
        if path != "/":
            # strip leading slash and any query string
            path = path.strip("/")
            path = path.split("?", 1)[0]   # <-- critical for "/steering?state=off"
            return path
    except:
        pass
    return None

def strip_prefix(s, prefix):
    return s[len(prefix):] if s.startswith(prefix) else s

def serve_index(conn):
    # Build the HTML page (status+map). The top bar values are driven by /status.json,
    # but we still compute them server-side so /status.json has everything it needs.

    # OPTIONAL: if nothing else calls add_fix, you can feed the track here
    # based on the latest strings from system_state.gps_data:
    #
    # try:
    #     gps = system_state.gps_data
    #     lat_str = strip_prefix(gps.get('lat', ''), 'Lat: ').strip()
    #     lon_str = strip_prefix(gps.get('lon', ''), 'Lon: ').strip()
    #     if lat_str and lon_str:
    #         gps_utils.add_fix(float(lat_str), float(lon_str))
    # except Exception as _:
    #     pass

    send_html(conn, HTML_INDEX)

def serve_status_json(conn):
    # Prefer your gps_utils.current_fix() (dict with lat, lon, t)
    fix = gps_utils.current_fix() or {}
    lat = fix.get("lat", None)
    lon = fix.get("lon", None)
    ts  = fix.get("t", None)

    # Enrich with your existing system_state info so the top bar can update
    gps = system_state.gps_data
    lat_str = strip_prefix(gps.get('lat', ''), 'Lat: ')
    lon_str = strip_prefix(gps.get('lon', ''), 'Lon: ')
    fix_str = strip_prefix(gps.get('fix', ''), 'Fix: ')
    heading = strip_prefix(gps.get('heading', ''), 'Head: ')
    ticks = gps.get('last_update_ticks', None)
    dt = time.ticks_diff(time.ticks_ms(), ticks) if ticks else '---'
    files = [f for f in os.listdir() if f.endswith(".csv")]

    payload = {
        "lat": lat,
        "lon": lon,
        "t": ts,
        "extra": {
            "time": gps.get('time', ''),
            "fix": fix_str,
            "heading": heading,
            "dt": dt,
            "logging": 'Yes' if system_state.logging else 'No',
            "steering": 'Enabled' if system_state.steering_enabled else 'Disabled',
            "wp": system_state.current_waypoint_index,
            "herr": f"{system_state.nav_heading_error:.2f}°",
            "files": files,
        }
    }
    send_json(conn, payload)

def serve_track_json(conn):
    # GeoJSON from gps_utils.as_geojson()
    try:
        payload = gps_utils.as_geojson()
    except Exception as e:
        # Fall back to empty feature collection on any error
        print("as_geojson error:", e)
        payload = {"type": "FeatureCollection", "features": []}
    send_json(conn, payload)

def serve_file(conn, filename):
    if filename not in os.listdir():
        conn.send("HTTP/1.0 404 Not Found\r\n\r\nFile not found.")
        return
    try:
        conn.send("HTTP/1.0 200 OK\r\nContent-Type: text/csv\r\n\r\n")
        with open(filename, "r") as f:
            for line in f:
                conn.send(line)
    except Exception as e:
        conn.send("HTTP/1.0 500 Internal Server Error\r\n\r\n")
        print(f"Error serving file {filename}:", e)
        
def serve_shutdown_page(conn):
    conn.sendall("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n")
    conn.sendall("<html><body><h3>Shutdown Requested</h3></body></html>")

def check_shutdown():
    return shutdown_requested

def stop():
    global should_exit
    should_exit = True

# --- tiny response helpers ----------------------------------------------------
def send_json(conn, obj):
    try:
        import ujson as json
    except:
        import json
    body = json.dumps(obj)
    conn.sendall("HTTP/1.0 200 OK\r\nContent-Type: application/json\r\nCache-Control: no-cache\r\n\r\n")
    conn.sendall(body)

def send_html(conn, html):
    conn.sendall("HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n")
    conn.sendall(html)
