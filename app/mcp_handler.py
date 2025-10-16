import json
import requests
from . import config
from .utils import safe_load_json

class MCPHandler:
    """
    Orchestrates recursive handling between LLM and MCP server until LLM returns {"action":"done"}.
    """

    def __init__(self, project_base: str, log_fn=None):
        self.project_base = project_base
        self.log = log_fn or (lambda *args, **kwargs: None)
        self.mcp_url = f"http://{config.MCP_HOST}:{config.MCP_PORT}"

    def handle_recursive(self, initial_response: dict, llm_call_fn, max_iter: int = None):
        """
        initial_response: dict returned from llm_client.call_llm (parsed JSON or {'text':...})
        llm_call_fn: function(prompt: str) -> dict (LLM response)
        """
        max_iter = max_iter or config.MCP_MAX_ITER
        current = initial_response
        iter_count = 0

        while iter_count < max_iter:
            iter_count += 1
            self.log(f"[MCP-handler] Iteration {iter_count}, response: {str(current)[:200]}")

            # Expect JSON with 'action' key
            if not isinstance(current, dict):
                # if raw text, try parse
                current = safe_load_json(current) or {"text": str(current)}

            action = current.get("action")
            if not action:
                # no action provided -> stop and return raw string form
                self.log("[MCP-handler] No action found; returning raw response.")
                return current.get("text") if "text" in current else str(current)

            if action == "read_file":
                path = current.get("path")
                if not path:
                    return {"error": "missing path in read_file action"}
                self.log(f"[MCP-handler] Requesting file from MCP server: {path}")
                r = requests.post(f"{self.mcp_url}/tool/read_file", json={"path": path}, timeout=30)
                if r.status_code != 200:
                    self.log(f"[MCP-handler] MCP server read_file error: {r.text}")
                    return {"error": "mcp_read_failed", "detail": r.text}
                file_resp = r.json()
                # send the file content back to LLM, instruct to continue
                next_prompt = f"Tool returned file content for '{path}':\n```\n{file_resp.get('content')}\n```\nPlease continue the task and if you need more files, respond again with JSON action read_file. Otherwise respond with JSON action done with field data containing the complete JUnit test code."
                self.log(f"[MCP-handler] Sending file content back to LLM (prompt size approx {len(next_prompt)}).")
                current = llm_call_fn(next_prompt)
                continue

            elif action == "list_files":
                subpath = current.get("path", "")
                self.log(f"[MCP-handler] Requesting list_files under {subpath}")
                r = requests.post(f"{self.mcp_url}/tool/list_files", json={"path": subpath}, timeout=30)
                if r.status_code != 200:
                    self.log(f"[MCP-handler] MCP server list_files error: {r.text}")
                    return {"error": "mcp_list_failed", "detail": r.text}
                files = r.json().get("files", [])
                next_prompt = f"Tool returned list of files under '{subpath}':\n{json.dumps(files)}\nPlease decide which file(s) you need and respond with JSON read_file actions (one per file) or done if finished."
                current = llm_call_fn(next_prompt)
                continue

            elif action == "done":
                data = current.get("data", "")
                self.log("[MCP-handler] LLM finished; returning generated code.")
                return data

            elif action == "error":
                self.log(f"[MCP-handler] LLM signaled error: {current.get('message')}")
                return {"error": "llm_error", "message": current.get("message")}

            else:
                self.log(f"[MCP-handler] Unknown action '{action}'. Returning raw.")
                return current

        # exceeded max iterations
        self.log("[MCP-handler] Reached max MCP iterations.")
        return {"error": "max_iterations_exceeded", "count": iter_count}
