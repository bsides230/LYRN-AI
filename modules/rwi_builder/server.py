import http.server
import socketserver
import threading
import json
import os
from urllib.parse import urlparse, parse_qs
from pathlib import Path

class RWIServer:
    def __init__(self, app, script_dir, port=0):
        self.app = app
        self.script_dir = script_dir
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        handler_class = lambda *args, **kwargs: RWIRequestHandler(self.app, self.script_dir, *args, **kwargs)
        # Allow port reuse to avoid "Address already in use" during development/restarts
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.ThreadingTCPServer(("0.0.0.0", self.port), handler_class)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        print(f"RWI Builder Server started at http://localhost:{self.port}")
        return self.port

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

class RWIRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, app, script_dir, *args, **kwargs):
        self.app = app
        self.script_dir = Path(script_dir)
        self.build_prompt_dir = self.script_dir / "build_prompt"
        # Serve static files from modules/rwi_builder/static
        static_dir = self.script_dir / "modules" / "rwi_builder" / "static"
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def log_message(self, format, *args):
        # Suppress default logging to keep console clean, or redirect to app log if needed
        pass

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*") # Useful for debugging
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        return json.loads(body)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path.startswith("/api/"):
            try:
                self.handle_api_get(parsed_path)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
                print(f"API GET Error: {e}")
        else:
            if self.path == "/":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            try:
                self.handle_api_post(self.path)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
                print(f"API POST Error: {e}")
        else:
            self.send_error(404, "Not Found")

    def handle_api_get(self, parsed_path):
        path = parsed_path.path

        if path == "/api/initial_data":
            # Load components.json
            components_path = self.build_prompt_dir / "components.json"
            components = []
            if components_path.exists():
                with open(components_path, 'r', encoding='utf-8') as f:
                    components = json.load(f)

            # Ensure RWI is in the list (logic from SystemPromptBuilderPopup)
            if not any(c['name'] == 'RWI' for c in components):
                 components.insert(0, {"name": "RWI", "order": -1, "active": True})

            # Sort components
            components.sort(key=lambda x: x.get('order', 99))

            # Load builder config
            builder_config_path = self.build_prompt_dir / "builder_config.json"
            builder_config = {}
            if builder_config_path.exists():
                with open(builder_config_path, 'r', encoding='utf-8') as f:
                    builder_config = json.load(f)

            self._send_json({
                "components": components,
                "builder_config": builder_config
            })

        elif path.startswith("/api/component/"):
            # Fetch details for a specific component
            comp_name = path.split("/")[-1]
            data = self._get_component_data(comp_name)
            self._send_json(data)

        elif path == "/api/master_prompt":
            master_prompt_path = self.build_prompt_dir / "master_prompt.txt"
            content = ""
            if master_prompt_path.exists():
                content = master_prompt_path.read_text(encoding='utf-8')
            self._send_json({"content": content})

        else:
            self.send_error(404, "API Endpoint Not Found")

    def handle_api_post(self, path):
        data = self._read_json_body()

        if path == "/api/save_component":
            self._save_component(data)
            self._send_json({"status": "success"})

        elif path == "/api/update_components_order":
            # data should be list of components
            components_path = self.build_prompt_dir / "components.json"
            with open(components_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self._send_json({"status": "success"})

        elif path == "/api/rebuild_master":
            # Trigger rebuild in the app
            # Thread-safety: snapshot_loader operations should be safe or we rely on GIL
            result = self.app.snapshot_loader.build_master_prompt_from_components()
            self._send_json({"status": "success", "content": result})

        elif path == "/api/lock_master":
            # Update builder_config.json
            builder_config_path = self.build_prompt_dir / "builder_config.json"
            config = {}
            if builder_config_path.exists():
                 with open(builder_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            config["master_prompt_locked"] = data.get("locked", False)

            with open(builder_config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            self._send_json({"status": "success"})

        elif path == "/api/delete_component":
            self._delete_component(data.get("name"))
            self._send_json({"status": "success"})

        else:
            self.send_error(404, "API Endpoint Not Found")

    def _get_component_data(self, comp_name):
        # RWI Special Case
        if comp_name == "RWI":
            config_path = self.build_prompt_dir / "rwi_config.json"
            intro_path = self.build_prompt_dir / "rwi_intro.txt"

            config = {}
            if config_path.exists():
                 with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            content = ""
            if intro_path.exists():
                content = intro_path.read_text(encoding='utf-8')

            return {
                "name": "RWI",
                "type": "rwi",
                "config": config,
                "content": content
            }

        # Generic/Standard Component
        comp_dir = self.build_prompt_dir / comp_name
        if not comp_dir.exists():
             # Return defaults for new component
             return {
                 "name": comp_name,
                 "type": "generic",
                 "config": {},
                 "content": ""
             }

        config_path = comp_dir / "config.json"
        config = {}
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

        # Detect specific types based on structure or name
        if comp_name == "personality":
             # Personality has 'traits' in config
             return {
                 "name": comp_name,
                 "type": "personality",
                 "config": config,
                 "content": "" # Content is generated from traits usually
             }

        if comp_name == "jobs":
             return {
                 "name": comp_name,
                 "type": "jobs",
                 "config": config,
                 "content": ""
             }

        if comp_name == "oss_tools":
             return {
                 "name": comp_name,
                 "type": "oss_tools",
                 "config": config,
                 "content": ""
             }

        # Generic
        content_file = config.get("content_file", f"{comp_name}.txt")
        content_path = comp_dir / content_file
        content = ""
        if content_path.exists():
            content = content_path.read_text(encoding='utf-8')

        return {
            "name": comp_name,
            "type": "generic",
            "config": config,
            "content": content
        }

    def _save_component(self, data):
        name = data.get("name")
        comp_type = data.get("type", "generic")
        config = data.get("config", {})
        content = data.get("content", "")

        if name == "RWI":
            config_path = self.build_prompt_dir / "rwi_config.json"
            intro_path = self.build_prompt_dir / "rwi_intro.txt"

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            intro_path.write_text(content, encoding='utf-8')
            return

        comp_dir = self.build_prompt_dir / name
        comp_dir.mkdir(exist_ok=True, parents=True)

        # Save Config
        config_path = comp_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        # Save Content (if generic)
        if comp_type == "generic":
            content_file = config.get("content_file", f"{name}.txt")
            content_path = comp_dir / content_file
            content_path.write_text(content, encoding='utf-8')

        elif comp_type == "personality":
            # For personality, we also regenerate the output file based on traits
            traits = config.get("traits", [])
            output_filename = config.get("output_file", "personality.txt")
            output_path = comp_dir / output_filename
            output_parts = [f'"{t["name"]} = {t["value"]:04d}"\n"{t["instructions"]}"' for t in traits]
            output_path.write_text("\n\n".join(output_parts), encoding='utf-8')

    def _delete_component(self, comp_name):
        import shutil
        if not comp_name or comp_name == "RWI": return

        # Remove from components.json
        components_path = self.build_prompt_dir / "components.json"
        components = []
        if components_path.exists():
            with open(components_path, 'r', encoding='utf-8') as f:
                components = json.load(f)

        components = [c for c in components if c.get("name") != comp_name]

        with open(components_path, 'w', encoding='utf-8') as f:
            json.dump(components, f, indent=2)

        # Delete directory
        comp_dir = self.build_prompt_dir / comp_name
        if comp_dir.exists() and comp_dir.is_dir():
            shutil.rmtree(comp_dir)
