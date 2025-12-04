import http.server
import socketserver
import json
import os
import threading
import urllib.parse
from pathlib import Path

PORT = 8000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.dirname(os.path.abspath(__file__)) # modules/rwi_builder
APP_ROOT = os.path.dirname(os.path.dirname(MODULE_ROOT)) # root of repo

class RWIServerHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        # Set the directory to serve static files from
        super().__init__(*args, directory=MODULE_ROOT, **kwargs)

    def _set_headers(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*') # Allow local dev
        self.end_headers()

    def _error(self, message, code=400):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')

        if path_parts[0] == 'api':
            # --- API Endpoints ---
            if path_parts[1] == 'components':
                self.handle_get_components()
            elif path_parts[1] == 'component' and len(path_parts) > 2:
                component_name = path_parts[2]
                self.handle_get_component(component_name)
            elif path_parts[1] == 'preview':
                self.handle_get_preview()
            elif path_parts[1] == 'settings':
                self.handle_get_settings()
            else:
                self._error("Endpoint not found", 404)
            return

        # Fallback to serving static files
        super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')

        if path_parts[0] == 'api':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except json.JSONDecodeError:
                self._error("Invalid JSON")
                return

            if path_parts[1] == 'components':
                self.handle_save_components_list(data)
            elif path_parts[1] == 'component' and len(path_parts) > 2:
                component_name = path_parts[2]
                self.handle_save_component(component_name, data)
            elif path_parts[1] == 'build':
                self.handle_build_prompt()
            elif path_parts[1] == 'settings':
                self.handle_save_settings(data)
            else:
                self._error("Endpoint not found", 404)
            return

        self._error("Method not allowed", 405)

    def do_DELETE(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')

        if path_parts[0] == 'api' and path_parts[1] == 'component' and len(path_parts) > 2:
            self.handle_delete_component(path_parts[2])
        else:
            self._error("Endpoint not found", 404)

    # --- Handlers ---

    def handle_get_components(self):
        components_path = os.path.join(APP_ROOT, "build_prompt", "components.json")
        try:
            if os.path.exists(components_path):
                with open(components_path, 'r', encoding='utf-8') as f:
                    components = json.load(f)
            else:
                components = []

            # Ensure RWI is present in the list even if not in file
            if not any(c['name'] == 'RWI' for c in components):
                components.insert(0, {"name": "RWI", "order": -1, "active": True})

            self._set_headers()
            self.wfile.write(json.dumps(components).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_save_components_list(self, data):
        # data should be the list of components
        components_path = os.path.join(APP_ROOT, "build_prompt", "components.json")
        try:
            # Filter out RWI if we don't want to save it explicitly, or keep it.
            # Usually RWI is implicit, but saving it is fine.
            with open(components_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_get_component(self, name):
        build_prompt_dir = os.path.join(APP_ROOT, "build_prompt")

        try:
            if name == "RWI":
                config_path = os.path.join(build_prompt_dir, "rwi_config.json")
                content_path = os.path.join(build_prompt_dir, "rwi_intro.txt")
            else:
                comp_dir = os.path.join(build_prompt_dir, name)
                config_path = os.path.join(comp_dir, "config.json")
                # Need to read config to find content file name, defaulting to name.txt
                if os.path.exists(config_path):
                     with open(config_path, 'r', encoding='utf-8') as f:
                        temp_config = json.load(f)
                        content_file = temp_config.get("content_file", f"{name}.txt")
                else:
                    content_file = f"{name}.txt"
                content_path = os.path.join(comp_dir, content_file)

            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            content = ""
            if os.path.exists(content_path):
                with open(content_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            self._set_headers()
            self.wfile.write(json.dumps({
                "name": name,
                "config": config,
                "content": content
            }).encode('utf-8'))

        except Exception as e:
            self._error(str(e), 500)

    def handle_save_component(self, name, data):
        build_prompt_dir = os.path.join(APP_ROOT, "build_prompt")

        try:
            config = data.get("config", {})
            content = data.get("content", "")

            if name == "RWI":
                config_path = os.path.join(build_prompt_dir, "rwi_config.json")
                content_path = os.path.join(build_prompt_dir, "rwi_intro.txt")
                # RWI doesn't need directory creation
            else:
                comp_dir = os.path.join(build_prompt_dir, name)
                os.makedirs(comp_dir, exist_ok=True)
                config_path = os.path.join(comp_dir, "config.json")

                # Determine content filename
                # If creating new, use name.txt. If existing, respect config.
                content_filename = f"{name}.txt"
                if os.path.exists(config_path):
                     with open(config_path, 'r', encoding='utf-8') as f:
                        old_config = json.load(f)
                        content_filename = old_config.get("content_file", content_filename)

                config["content_file"] = content_filename
                content_path = os.path.join(comp_dir, content_filename)

                # Ensure component is in components.json
                components_path = os.path.join(build_prompt_dir, "components.json")
                if os.path.exists(components_path):
                    with open(components_path, 'r', encoding='utf-8') as f:
                        components = json.load(f)
                else:
                    components = []

                if not any(c['name'] == name for c in components):
                    components.append({"name": name, "order": len(components), "active": True})
                    with open(components_path, 'w', encoding='utf-8') as f:
                        json.dump(components, f, indent=2)

            # Save Config
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)

            # Save Content
            with open(content_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))

        except Exception as e:
            self._error(str(e), 500)

    def handle_delete_component(self, name):
        if name == "RWI":
            self._error("Cannot delete RWI", 403)
            return

        build_prompt_dir = os.path.join(APP_ROOT, "build_prompt")
        components_path = os.path.join(build_prompt_dir, "components.json")
        comp_dir = os.path.join(build_prompt_dir, name)

        try:
            # Remove from json
            if os.path.exists(components_path):
                with open(components_path, 'r', encoding='utf-8') as f:
                    components = json.load(f)

                components = [c for c in components if c['name'] != name]

                with open(components_path, 'w', encoding='utf-8') as f:
                    json.dump(components, f, indent=2)

            # Remove directory
            if os.path.exists(comp_dir):
                import shutil
                shutil.rmtree(comp_dir)

            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_build_prompt(self):
        # We need to trigger the build logic.
        # Since this script runs in a separate thread/process potentially,
        # or we want to reuse the SnapshotLoader logic.
        # Ideally, we import SnapshotLoader.
        # But SnapshotLoader is in lyrn_sad_v4.2.7.py which is the main app.
        # It's cleaner to implement a standalone build function or import just that.
        # Given the file structure, importing from main script might be circular or messy if it runs GUI code on import.
        # So we will replicate the basic build logic here or allow the main app to pass a callback.

        # However, RWIServer is running inside the main app process (threaded).
        # So we can access the parent app's methods if we pass them.
        # But this Handler is instantiated per request by socketserver.
        # We can attach the build_callback to the server instance.

        if hasattr(self.server, 'build_callback'):
            try:
                self.server.build_callback()
                self._set_headers()
                self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
            except Exception as e:
                self._error(str(e), 500)
        else:
             self._error("Build callback not configured", 500)

    def handle_get_preview(self):
        # Return the content of master_prompt.txt
        master_path = os.path.join(APP_ROOT, "build_prompt", "master_prompt.txt")
        try:
            if os.path.exists(master_path):
                with open(master_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self._error("Master prompt not found", 404)
        except Exception as e:
            self._error(str(e), 500)

    def handle_get_settings(self):
        config_path = os.path.join(APP_ROOT, "build_prompt", "builder_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            self._set_headers()
            self.wfile.write(json.dumps(config).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_save_settings(self, data):
        config_path = os.path.join(APP_ROOT, "build_prompt", "builder_config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)
            else:
                current_config = {}

            current_config.update(data)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, indent=2)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)


class RWIServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    def __init__(self, port, build_callback):
        self.build_callback = build_callback
        super().__init__(("", port), RWIServerHandler)

def start_server(port=8000, build_callback=None):
    server = RWIServer(port, build_callback)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server
