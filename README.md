# AIJUnitGen

AIJUnitGen — Desktop app that uses local Ollama LLM to generate JUnit tests for Java Service classes.

## Features
- PyQt6 GUI
- Lightweight Java parsing via `javalang`
- MCP server (Flask) exposing tools: read_file, list_files, save_output
- Recursive MCP handling: LLM can request files until it returns `done`
- Uses Ollama local model (`llama3` by default)

## Requirements
- Python 3.10+
- Ollama local server running (example endpoint: http://localhost:11434/api/generate)
- Install dependencies:
```bash
pip install -r requirements.txt
