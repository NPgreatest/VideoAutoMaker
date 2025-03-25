import os
import json

def create_project(name):
    base = os.path.join("projects", name)
    os.makedirs(base, exist_ok=True)
    os.makedirs(os.path.join(base, "audio"), exist_ok=True)
    os.makedirs(os.path.join(base, "video"), exist_ok=True)
    os.makedirs(os.path.join(base, "final"), exist_ok=True)
    return base

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)