import os
import socket
import system_state
import time

HTML_HEADER = """\
HTTP/1.0 200 OK\r
Content-Type: text/html\r
\r
<html><head><title>Pico Rover</title>
<meta http-equiv="refresh" content="1">
</head><body>
"""

HTML_FOOTER = "</body></html>"
html = HTML_HEADER
html += "<h2>System Status</h2>"
html += HTML_FOOTER
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

            requested_file = parse_filename_from_request(request)
            #print("HTTP request:", request)
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
    gps = system_state.gps_data
    lat = strip_prefix(gps.get('lat', ''), 'Lat: ')
    lon = strip_prefix(gps.get('lon', ''), 'Lon: ')
    fix = strip_prefix(gps.get('fix', ''), 'Fix: ')
    heading = strip_prefix(gps.get('heading', ''), 'Head: ').replace('ø', '&deg;')  # keep your LCD happy, fix HTML

    ticks = gps.get('last_update_ticks', None)
    dt = time.ticks_diff(time.ticks_ms(), ticks) if ticks else '---'
    files = [f for f in os.listdir() if f.endswith(".csv")]

    html = HTML_HEADER
    html += "<h2>System Status</h2>"
    html += f"<p><b>GPS Time:</b> {gps.get('time','')}</p>"
    html += f"<p><b>Fix:</b> {fix}</p>"
    html += f"<p><b>Lat:</b> {lat}</p>"
    html += f"<p><b>Lon:</b> {lon}</p>"
    html += f"<p><b>Heading:</b> {heading}</p>"
    html += f"<p><b>Time Since Last GPS Update:</b> {dt} ms</p>"
    html += f"<p><b>Logging:</b> {'Yes' if system_state.logging else 'No'}</p>"
    html += f"<p><b>Steering PWM:</b> {'Enabled' if system_state.steering_enabled else 'Disabled'}</p>"
    html += f"<p><b>Current WP:</b> {system_state.current_waypoint_index}</p>"
    html += f"<p><b>Heading Error:</b> {system_state.nav_heading_error:.2f}&deg;</p>"


    html += """
    <form action="/steering" method="get">
        <button name="state" value="on">Enable Steering</button>
        <button name="state" value="off">Disable Steering</button>
    </form>
    <hr>
    <h2>Log Files</h2><ul>
    """

    for f in files:
        html += f'<li><a href="/{f}">{f}</a></li>\n'
    
    html += "</ul><hr>"
    html += '<a href="/shutdown">Shutdown Pico</a>'
    html += HTML_FOOTER
    conn.sendall(html)


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
