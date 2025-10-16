import requests
import json
from typing import Dict, Any
from . import config

SYSTEM_PROMPT = """
You are a specialized assistant that generates precise JUnit 5 tests (Mockito + AssertJ style)
for Java Service classes. You are allowed to request additional context (repo/entity files)
by returning a JSON object as the entire response with the format:

{"action":"read_file", "path": "<relative/path/from/project_root>"}

When you need multiple files, call again after receiving the file content.
When you have all you need and want to produce the test, return:

{"action":"done", "data": "<full junit test code as string>"}

Only return valid JSON for tool-calling stages. When returning "done", the "data" field must contain only the code string.

If you need anything else, respond with {"action":"error", "message":"..."}
"""

def call_llm(prompt: str, conversation: Dict[str, Any] | None = None, timeout: int = 300) -> Dict[str, Any]:
    """
    Send prompt to Ollama endpoint. Return parsed JSON if possible,
    otherwise return raw text under {"text": "..."}.
    """
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": f"{SYSTEM_PROMPT}\n\nUser prompt:\n{prompt}",
        "stream": False
    }
    resp = requests.post(config.OLLAMA_ENDPOINT, json=payload, timeout=timeout)
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        # fallback: text
        return {"text": resp.text}

    # Try to extract assistant response text
    # Different Ollama setups might return different keys; try common ones.
    if isinstance(data, dict):
        # many Ollama instances put output in "response" or "text"
        if "response" in data:
            text = data["response"]
        elif "text" in data:
            text = data["text"]
        elif "generated_text" in data:
            text = data["generated_text"]
        else:
            # fallback: stringified entire json
            text = json.dumps(data)
    else:
        text = str(data)

    # try to parse JSON from text (LLM is asked to produce JSON)
    try:
        parsed = json.loads(text.strip())
        return parsed
    except Exception:
        return {"text": text}
