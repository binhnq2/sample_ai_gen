import os

# Default configuration
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Ollama endpoint (default). Change if needed.
OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# MCP server settings (MCP server will run locally)
MCP_HOST = "127.0.0.1"
MCP_PORT = 5001

# Max recursive iterations for MCP to avoid infinite loops
MCP_MAX_ITER = 8
