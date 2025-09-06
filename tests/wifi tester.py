# wifi_tester.py
# Standalone Wi-Fi scanner/connector for MicroPython (no LCD).
# Reads credentials from config.env in the same directory.

import network
import time

# ---------- Simple .env parser ----------
def load_env(filename="config.env"):
    env = {}
    try:
        with open(filename) as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except Exception as e:
        print("Failed to load", filename, "->", e)
    return env

# ---------- Helpers ----------
def is_valid_ssid(ssid_bytes):
    try:
        ssid = ssid_bytes.decode("utf-8").strip()
        return ssid and not all(c == "\x00" for c in ssid)
    except:
        return False

def build_preferred_networks(env):
    """
    Collect WIFIx_SSID / WIFIx_PASS pairs from config.env.
    Supports WIFI1_*, WIFI2_*, WIFI3_* ... up to 10 by default.
    """
    pairs = []
    for i in range(1, 11):
        ssid = env.get(f"WIFI{i}_SSID")
        pwd  = env.get(f"WIFI{i}_PASS")
        if ssid:  # allow empty password if it's an open network
            pairs.append((ssid, pwd or ""))
    return pairs

def scan_networks(wlan, retries=2, delay=1.0):
    all_networks = []
    for attempt in range(1, retries + 1):
        try:
            print(f"Scanning for available networks (attempt {attempt})...")
            nets = wlan.scan()  # list of tuples per MicroPython: (ssid,bssid,channel,RSSI,authmode,hidden)
            if nets:
                all_networks = nets
                break
        except Exception as e:
            print("Scan failed:", e)
        time.sleep(delay)
    return all_networks

def connect_with_timeout(wlan, ssid, password, timeout_s=18):
    print(f"Connecting to: {ssid!r}")
    try:
        # Some chipsets like a quick reset of the interface between attempts
        wlan.disconnect()
    except:
        pass
    time.sleep(0.3)
    wlan.active(False)
    time.sleep(0.5)
    wlan.active(True)
    time.sleep(0.5)

    if password:
        wlan.connect(ssid, password)
    else:
        wlan.connect(ssid)  # open network

    start = time.time()
    while not wlan.isconnected():
        status = wlan.status()
        print("  waiting... status:", status)
        time.sleep(1)
        if time.time() - start > timeout_s:
            print("  timeout while connecting")
            return False
    return True

# ---------- Main ----------
def main():
    env = load_env("config.env")
    preferred_networks = build_preferred_networks(env)

    if not preferred_networks:
        print("No WIFIx_SSID entries found in config.env. Add e.g.:")
        print("  WIFI1_SSID=MyWiFi")
        print("  WIFI1_PASS=MyPassword")
        return

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    time.sleep(1)  # let radio come up

    nets = scan_networks(wlan)
    if not nets:
        print("No networks found.")
        return

    # Build list of (ssid, rssi) for display and lookup
    available = []
    for net in nets:
        ssid_bytes = net[0]
        rssi = net[3]
        if is_valid_ssid(ssid_bytes):
            ssid = ssid_bytes.decode("utf-8").strip()
            available.append((ssid, rssi))

    # Print results
    print("\nAvailable networks:")
    for ssid, rssi in sorted(available, key=lambda x: x[1], reverse=True):
        print(f"  SSID: {ssid} | RSSI: {rssi} dBm")

    # Try connecting to the first matching preferred network
    known_ssids = {ssid for ssid, _ in available}
    for ssid, password in preferred_networks:
        if ssid in known_ssids:
            ok = connect_with_timeout(wlan, ssid, password, timeout_s=18)
            if ok:
                print("Connected to", ssid)
                print("IP info:", wlan.ifconfig())
                return
            else:
                print("Failed to connect to", ssid, "— trying next known network...")
                # continue to next preferred network

    print("No known networks could be connected.")

if __name__ == "__main__":
    main()
