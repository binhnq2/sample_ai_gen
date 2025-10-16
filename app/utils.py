import os
import json

def safe_load_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None

def read_text_file(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()
