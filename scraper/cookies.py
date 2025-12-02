import json, os

def load_cookies(path="config/cookies.json"):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data
        except Exception:
            return None
