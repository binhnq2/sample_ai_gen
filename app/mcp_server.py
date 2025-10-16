import threading
from flask import Flask, request, jsonify
import os
from .config import MCP_HOST, MCP_PORT
from .utils import read_text_file

class MCPServer:
    def __init__(self, base_dir: str = None, host: str = MCP_HOST, port: int = MCP_PORT):
        self.base_dir = base_dir or os.getcwd()
        self.host = host
        self.port = port
        self._app = Flask("mcp_server")
        self._register_routes()

        self._thread = None

    def _register_routes(self):
        app = self._app

        @app.route("/tool/read_file", methods=["POST"])
        def read_file():
            req = request.get_json() or {}
            rel_path = req.get("path")
            if not rel_path:
                return jsonify({"error": "path missing"}), 400
            # sanitize: prevent path traversal
            safe_path = os.path.normpath(os.path.join(self.base_dir, rel_path))
            if not safe_path.startswith(os.path.normpath(self.base_dir)):
                return jsonify({"error": "invalid path"}), 400
            if not os.path.exists(safe_path):
                return jsonify({"error": "not_found", "path": rel_path}), 404
            try:
                content = read_text_file(safe_path)
                return jsonify({"path": rel_path, "content": content})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/tool/list_files", methods=["POST"])
        def list_files():
            req = request.get_json() or {}
            rel_dir = req.get("path", "")
            safe_dir = os.path.normpath(os.path.join(self.base_dir, rel_dir))
            if not safe_dir.startswith(os.path.normpath(self.base_dir)):
                return jsonify({"error": "invalid path"}), 400
            if not os.path.isdir(safe_dir):
                return jsonify({"error": "not_dir", "path": rel_dir}), 404
            files = []
            for root, dirs, filenames in os.walk(safe_dir):
                for fn in filenames:
                    if fn.endswith(".java"):
                        full = os.path.join(root, fn)
                        rel = os.path.relpath(full, self.base_dir)
                        files.append(rel)
            return jsonify({"files": files})

        @app.route("/tool/save_output", methods=["POST"])
        def save_output():
            req = request.get_json() or {}
            rel_path = req.get("path")
            content = req.get("content", "")
            if not rel_path:
                return jsonify({"error": "path missing"}), 400
            safe_path = os.path.normpath(os.path.join(self.base_dir, rel_path))
            if not safe_path.startswith(os.path.normpath(self.base_dir)):
                return jsonify({"error": "invalid path"}), 400
            try:
                os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return jsonify({"saved": rel_path})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        def _run():
            # disable flask logging to keep UI clean
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            self._app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def set_base_dir(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
