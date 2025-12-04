import http.server
import socketserver
import json
import os
import threading
import urllib.parse
import traceback
from datetime import datetime

# Set the module root directory
MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))

class JobManagerServerHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        # Serve static files from the module directory
        super().__init__(*args, directory=MODULE_ROOT, **kwargs)

    def _set_headers(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def _error(self, message, code=400):
        print(f"JobManager Server Error: {message}")
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))

    def do_GET(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path_parts = parsed_path.path.strip('/').split('/')

            if path_parts[0] == 'api':
                if len(path_parts) > 1:
                    if path_parts[1] == 'jobs':
                        self.handle_get_jobs()
                    elif path_parts[1] == 'schedules':
                        self.handle_get_schedules()
                    elif path_parts[1] == 'cycles':
                        self.handle_get_cycles()
                    else:
                        self._error("Endpoint not found", 404)
                else:
                    self._error("Endpoint incomplete", 404)
                return

            super().do_GET()
        except Exception:
            traceback.print_exc()
            self._error("Internal Server Error", 500)

    def do_POST(self):
        try:
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

                if path_parts[1] == 'job' and len(path_parts) > 2:
                    self.handle_save_job(path_parts[2], data)
                elif path_parts[1] == 'schedule':
                    self.handle_add_schedule(data)
                elif path_parts[1] == 'cycle' and len(path_parts) > 2:
                    self.handle_save_cycle(path_parts[2], data)
                elif path_parts[1] == 'run_job' and len(path_parts) > 2:
                    self.handle_run_job(path_parts[2])
                elif path_parts[1] == 'pin_job':
                    self.handle_pin_job(data)
                else:
                    self._error("Endpoint not found", 404)
                return

            self._error("Method not allowed", 405)
        except Exception:
            traceback.print_exc()
            self._error("Internal Server Error", 500)

    def do_DELETE(self):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path_parts = parsed_path.path.strip('/').split('/')

            if path_parts[0] == 'api':
                if path_parts[1] == 'job' and len(path_parts) > 2:
                    self.handle_delete_job(path_parts[2])
                elif path_parts[1] == 'schedule' and len(path_parts) > 2:
                    self.handle_delete_schedule(path_parts[2])
                elif path_parts[1] == 'cycle' and len(path_parts) > 2:
                    self.handle_delete_cycle(path_parts[2])
                else:
                    self._error("Endpoint not found", 404)
                return

            self._error("Method not allowed", 405)
        except Exception:
            traceback.print_exc()
            self._error("Internal Server Error", 500)

    # --- Handlers ---

    def handle_get_jobs(self):
        try:
            # Access managers via app instance
            jobs = self.server.app.automation_controller.job_definitions
            active_jobs = self.server.app.get_active_jobs() # New method on app

            # Merge pinned status
            response_jobs = {}
            for name, data in jobs.items():
                job_resp = data.copy()
                job_resp['pinned'] = (name in active_jobs)
                response_jobs[name] = job_resp

            self._set_headers()
            self.wfile.write(json.dumps(response_jobs).encode('utf-8'))
        except Exception as e:
            traceback.print_exc()
            self._error(str(e), 500)

    def handle_save_job(self, name, data):
        try:
            instructions = data.get('instructions', '')
            trigger = data.get('trigger', '')
            self.server.app.automation_controller.save_job_definition(name, instructions, trigger)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_delete_job(self, name):
        try:
            # Check if pinned
            active_jobs = self.server.app.get_active_jobs()
            if name in active_jobs:
                self._error("Cannot delete a pinned job", 403)
                return

            self.server.app.automation_controller.delete_job_definition(name)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_run_job(self, name):
        try:
            # Execute on main thread
            self.server.app.after(0, lambda: self.server.app.run_selected_job_from_web(name))
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'triggered'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_pin_job(self, data):
        try:
            name = data.get('name')
            if not name:
                self._error("Job name required")
                return

            # Toggle pin
            # We need to know current state to toggle, or just call toggle.
            # Let's assume toggle.

            # Schedule on main thread to ensure thread safety with snapshot loader
            self.server.app.after(0, lambda: self.server.app.toggle_job_pin(name))

            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_get_schedules(self):
        try:
            schedules = self.server.app.scheduler_manager.get_all_schedules()
            schedules_data = [
                {
                    "id": s.id,
                    "job_name": s.job_name,
                    "scheduled_datetime": s.scheduled_datetime.isoformat(),
                    "created_at": s.created_at.isoformat()
                }
                for s in schedules
            ]
            self._set_headers()
            self.wfile.write(json.dumps(schedules_data).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_add_schedule(self, data):
        try:
            job_name = data.get('job_name')
            dt_iso = data.get('scheduled_datetime')
            if not job_name or not dt_iso:
                self._error("Missing job_name or scheduled_datetime")
                return

            dt = datetime.fromisoformat(dt_iso.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)

            self.server.app.scheduler_manager.add_schedule(job_name, dt)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_delete_schedule(self, schedule_id):
        try:
            self.server.app.scheduler_manager.delete_schedule(schedule_id)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_get_cycles(self):
        try:
            cycles = self.server.app.cycle_manager.get_cycles()
            self._set_headers()
            self.wfile.write(json.dumps(cycles).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_save_cycle(self, name, data):
        try:
            triggers = data.get('triggers', [])
            if name not in self.server.app.cycle_manager.get_cycles():
                self.server.app.cycle_manager.create_cycle(name)
            self.server.app.cycle_manager.update_cycle_triggers(name, triggers)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_delete_cycle(self, name):
        try:
            self.server.app.cycle_manager.delete_cycle(name)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)


class JobManagerServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    def __init__(self, port, app_instance):
        self.app = app_instance
        super().__init__(("", port), JobManagerServerHandler)

def start_server(port, app_instance):
    server = JobManagerServer(port, app_instance)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server
