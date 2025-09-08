import network
import socket
import ubinascii
import time
import json
import system_state
import display_utils
import env_utils


env = env_utils.load_env()

_wlan = None
PREFERRED_NETWORKS = [
    (env.get("WIFI1_SSID"), env.get("WIFI1_PASS")),
    (env.get("WIFI2_SSID"), env.get("WIFI2_PASS")),
    (env.get("WIFI3_SSID"), env.get("WIFI3_PASS")),
]

NTRIP_HOST = env.get("NTRIP_HOST", "rtk2go.com")
NTRIP_PORT = int(env.get("NTRIP_PORT", "2101"))
MOUNTPOINT = env.get("NTRIP_MOUNTPOINT", "")
USERNAME = env.get("NTRIP_USERNAME", "")
PASSWORD = env.get("NTRIP_PASSWORD", "")

def is_valid_ssid(ssid_bytes):
    try:
        ssid = ssid_bytes.decode('utf-8').strip()
        return ssid and not all(c == '\x00' for c in ssid)
    except:
        return False
    
def try_scan(wlan, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            return wlan.scan()
        except Exception as e:
            print("Scan failed:", e)
            time.sleep(1)
    print("Timed out waiting for scan to succeed.")
    return []

def scan_for_networks(wlan):
    try:
        return wlan.scan()
    except Exception as e:
        print("Wi-Fi scan failed:", e)
        return []

def show_and_log_scan_results(scan_results):
    available = []
    print(f"Scan results ({len(scan_results)} networks):")
    for i in range(2, 11):
        system_state.display_lines[i] = ""

    for idx, net in enumerate(scan_results):
        try:
            ssid_bytes = net[0]
            rssi = net[3]
            if is_valid_ssid(ssid_bytes):
                ssid = ssid_bytes.decode('utf-8').strip()
                available.append(ssid)
                print(f"  SSID: {ssid}, RSSI: {rssi} dBm")
                if idx < 8:
                    system_state.display_lines[2 + idx] = f"{ssid} ({rssi}dBm)"
        except Exception as e:
            print("Error decoding SSID:", e)

    display_utils.update_display()
    return available

def connect_wifi():
    time.sleep(1)
    wlan = network.WLAN(network.STA_IF)
    time.sleep(1)
    wlan.active(True)
    time.sleep(3)

    for scan_attempt in range(3):
        system_state.display_lines[0] = f"Scan attempt {scan_attempt + 1}..."
        for i in range(2, 7):
            system_state.display_lines[i] = ""
        display_utils.update_display()

        scan_results = scan_for_networks(wlan)
        available_ssids = show_and_log_scan_results(scan_results)

        system_state.display_lines[1] = f"{len(available_ssids)} networks found"
        display_utils.update_display()
        time.sleep(0.5)

        for ssid, password in PREFERRED_NETWORKS:
            if ssid in available_ssids:
                print(f"Connecting to {ssid}...")
                system_state.display_lines[2] = f"Connecting to {ssid}..."
                start_time = time.time()
                system_state.display_lines[3] = "Waiting for connection..."
                display_utils.update_display()
                time.sleep(0.5)
                wlan.disconnect()
                time.sleep(0.5)
                wlan.active(False)
                time.sleep(1)
                wlan.active(True)
                time.sleep(1)
                wlan.connect(ssid, password)
                time.sleep(0.5)
                while not wlan.isconnected():
                    print("Waiting for connection...")
                    print("Status:", wlan.status())
                    time.sleep(2)

                    if time.time() - start_time > 18:
                        print("Connection timeout.")
                        system_state.display_lines[4] = "Timeout, retrying..."
                        display_utils.update_display()
                        wlan.disconnect()
                        time.sleep(2)
                        break
                else:
                    ip = wlan.ifconfig()[0]
                    print(f"Connected to {ssid} with IP {ip}")
                    system_state.display_lines[5] = f"Connected: {ssid}"
                    system_state.wifi_connected = True
                    system_state.wifi_ssid = ssid
                    system_state.wifi_ip = ip
                    for i in range(6, 11):
                        system_state.display_lines[i] = ""
                    display_utils.update_display()
                    return ip

        print("No preferred networks found.")
        system_state.display_lines[6] = "No preferred networks"
        display_utils.update_display()
        time.sleep(2)

    print("Wi-Fi failed. Halting.")
    system_state.display_lines[7] = "Wi-Fi failed. Halting."
    system_state.wifi_connected = False
    system_state.wifi_ssid = ""
    system_state.wifi_ip = ""
    display_utils.update_display()
    while True:
        time.sleep(1)

import system_state
import display_utils

def connect_ntrip(max_attempts=3, retry_delay=5):
    for attempt in range(1, max_attempts + 1):
        try:
            status_msg = f"NTRIP attempt {attempt}..."
            print(status_msg)
            system_state.display_lines[8] = status_msg
            display_utils.update_display()
            time.sleep(1)
            auth = ubinascii.b2a_base64(f"{USERNAME}:{PASSWORD}".encode()).decode().strip()
            headers = (
                f"GET /{MOUNTPOINT} HTTP/1.0\r\n"
                f"User-Agent: NTRIP PicoClient\r\n"
                f"Authorization: Basic {auth}\r\n\r\n"
            )
            addr = socket.getaddrinfo(NTRIP_HOST, NTRIP_PORT)[0][-1]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(addr)
            s.send(headers.encode())
            response = s.recv(1024)
            if b"ICY 200 OK" not in response:
                print("NTRIP connection failed (bad response)")
                s.close()
                continue

            print("Connected to NTRIP caster")
            system_state.display_lines[8] = "NTRIP connected"
            display_utils.update_display()

            s.settimeout(0.1)
            system_state.ntrip_connected = True
            system_state.last_ntrip_rx_ticks = time.ticks_ms()
            return s

        except Exception as e:
            print(f"NTRIP connection error: {e}")
            system_state.display_lines[8] = f"NTRIP error: retrying"
            display_utils.update_display()

            if attempt < max_attempts:
                time.sleep(retry_delay)
            else:
                system_state.display_lines[8] = "NTRIP FAILED"
                system_state.ntrip_connected = False
                display_utils.update_display()
                return None
            
def get_wlan():
    global _wlan
    if _wlan is None:
        _wlan = network.WLAN(network.STA_IF)
        _wlan.active(True)
    return _wlan

def ensure_wifi():
    """Return True if connected, otherwise try to reconnect."""
    wlan = get_wlan()
    if wlan.isconnected():
        return True
    # try reconnect using your existing connect_wifi logic
    ip = connect_wifi()
    return bool(ip)

def poll_ntrip_socket(ntrip_socket, timeout_ms=50):
    """
    Non-blocking-ish poll of the NTRIP socket. 
    If data arrives, mark ntrip_connected and update last_ntrip_rx_ticks.
    If socket errors, mark disconnected and return None (caller can reconnect).
    """
    if ntrip_socket is None:
        system_state.ntrip_connected = False
        return None
    try:
        ntrip_socket.settimeout(timeout_ms / 1000.0)
        chunk = ntrip_socket.recv(256)
        if chunk:
            # We received some RTCM—mark alive
            system_state.ntrip_connected = True
            system_state.last_ntrip_rx_ticks = time.ticks_ms()
            return chunk
    except OSError as e:
        # EAGAIN / timeout is fine; just check last activity
        pass
    except Exception as e:
        print("NTRIP poll error:", e)
        try:
            ntrip_socket.close()
        except:
            pass
        system_state.ntrip_connected = False
        return None

    # If no data for a while, consider it down (e.g., >10s with no bytes)
    if system_state.last_ntrip_rx_ticks is None:
        # we haven't seen any data yet—treat as unknown/down
        system_state.ntrip_connected = False
    else:
        silence_ms = time.ticks_diff(time.ticks_ms(), system_state.last_ntrip_rx_ticks)
        if silence_ms > 10000:
            system_state.ntrip_connected = False

    return ntrip_socket


