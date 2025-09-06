# env_utils.py
def load_env(filename="config.env"):
    env = {}
    try:
        with open(filename) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    except Exception as e:
        print("Failed to load .env:", e)
    return env
