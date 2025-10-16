from .parser import parse_java_methods
from .llm_client import call_llm
from .mcp_handler import MCPHandler
from .mcp_server import MCPServer
from .config import MCP_PORT, MCP_HOST
import os

class TestGenFlow:
    def __init__(self, project_path: str, file_path: str, method_sig: str, log_signal=None):
        self.project_path = project_path
        self.file_path = file_path
        self.method_sig = method_sig
        self.log = log_signal or (lambda msg: print(msg))

        # start/ensure MCP server running with base dir set to project_path
        self.mcp_server = MCPServer(base_dir=self.project_path, host=MCP_HOST, port=MCP_PORT)
        self.mcp_server.start()
        self.mcp_handler = MCPHandler(project_base=self.project_path, log_fn=self.log)

    def run(self) -> str:
        self.log(f"Starting generation flow for method {self.method_sig}")
        # Read selected class file
        with open(self.file_path, 'r', encoding='utf-8') as f:
            src = f.read()

        # Build initial prompt: include source & instruction to request files via JSON actions
        initial_prompt = f"""
You are an assistant that will generate a JUnit 5 test for the method: {self.method_sig}

Here is the service class source (single file):
{src}

If you need additional files (repositories, entities, DTOs), request them using JSON like:
{{"action":"read_file", "path":"relative/path/to/File.java"}}

When you have gathered enough info, return:
{{"action":"done", "data":"<the full junit test code>"}}

Only return valid JSON for tool-calling and final response.
"""
        # Call LLM initial
        self.log("Sending initial prompt to LLM.")
        initial_resp = call_llm(initial_prompt)
        self.log(f"Received initial LLM response (type: {type(initial_resp)}).")

        # If response is dict and contains action/done/read_file etc, handle recursively
        result = self.mcp_handler.handle_recursive(initial_resp, llm_call_fn=lambda p: call_llm(p), max_iter=None)
        # result may be string or dict
        if isinstance(result, dict):
            if result.get("error"):
                self.log(f"Generation error: {result}")
                return f"Error: {result}"
        self.log("Generation completed.")
        return result if isinstance(result, str) else str(result)

