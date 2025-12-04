import http.server
import socketserver
import json
import os
import threading
import urllib.parse
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
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}).encode('utf-8'))

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path_parts = parsed_path.path.strip('/').split('/')

        if path_parts[0] == 'api':
            if path_parts[1] == 'jobs':
                self.handle_get_jobs()
            elif path_parts[1] == 'schedules':
                self.handle_get_schedules()
            elif path_parts[1] == 'cycles':
                self.handle_get_cycles()
            else:
                self._error("Endpoint not found", 404)
            return

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

            if path_parts[1] == 'job' and len(path_parts) > 2:
                self.handle_save_job(path_parts[2], data)
            elif path_parts[1] == 'schedule':
                self.handle_add_schedule(data)
            elif path_parts[1] == 'cycle' and len(path_parts) > 2:
                self.handle_save_cycle(path_parts[2], data)
            elif path_parts[1] == 'run_job' and len(path_parts) > 2:
                self.handle_run_job(path_parts[2])
            elif path_parts[1] == 'run_reflection':
                self.handle_run_reflection(data)
            else:
                self._error("Endpoint not found", 404)
            return

        self._error("Method not allowed", 405)

    def do_DELETE(self):
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

    # --- Handlers ---

    def handle_get_jobs(self):
        try:
            # Refresh jobs from disk to ensure we have latest
            # But AutomationController might not have a public reload method exposed easily.
            # Assuming the controller state is reasonably up to date or we can access definitions directly.
            # AutomationController loads on init. To reload, we might need a method on it.
            # For now, let's assume definitions are current.
            jobs = self.server.automation_controller.job_definitions
            self._set_headers()
            self.wfile.write(json.dumps(jobs).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_save_job(self, name, data):
        try:
            instructions = data.get('instructions', '')
            trigger = data.get('trigger', '')
            self.server.automation_controller.save_job_definition(name, instructions, trigger)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_delete_job(self, name):
        try:
            self.server.automation_controller.delete_job_definition(name)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_run_job(self, name):
        if self.server.run_job_callback:
            try:
                self.server.run_job_callback(name)
                self._set_headers()
                self.wfile.write(json.dumps({'status': 'triggered'}).encode('utf-8'))
            except Exception as e:
                self._error(str(e), 500)
        else:
            self._error("Run callback not configured", 500)

    def handle_get_schedules(self):
        try:
            schedules = self.server.scheduler_manager.get_all_schedules()
            # Convert objects to dicts
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

            # Parse ISO string to datetime
            dt = datetime.fromisoformat(dt_iso.replace('Z', '+00:00'))

            # Note: scheduler_manager.add_schedule takes a timezone-naive or aware datetime.
            # Usually naive for local time is easier if the system assumes local.
            # Python's datetime.fromisoformat might return aware if timezone info is present.
            # Lyrn seems to use local time (datetime.now()).
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None) # Strip timezone for simplicity if app uses local

            self.server.scheduler_manager.add_schedule(job_name, dt)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_delete_schedule(self, schedule_id):
        try:
            self.server.scheduler_manager.delete_schedule(schedule_id)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_get_cycles(self):
        try:
            cycles = self.server.cycle_manager.get_cycles()
            self._set_headers()
            self.wfile.write(json.dumps(cycles).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_save_cycle(self, name, data):
        try:
            # data.triggers is expected
            triggers = data.get('triggers', [])

            # Check if cycle exists, if not create
            if name not in self.server.cycle_manager.get_cycles():
                self.server.cycle_manager.create_cycle(name)

            # Update triggers
            self.server.cycle_manager.update_cycle_triggers(name, triggers)

            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_delete_cycle(self, name):
        try:
            self.server.cycle_manager.delete_cycle(name)
            self._set_headers()
            self.wfile.write(json.dumps({'status': 'ok'}).encode('utf-8'))
        except Exception as e:
            self._error(str(e), 500)

    def handle_run_reflection(self, data):
        if self.server.run_reflection_callback:
            try:
                self.server.run_reflection_callback(data)
                self._set_headers()
                self.wfile.write(json.dumps({'status': 'queued'}).encode('utf-8'))
            except Exception as e:
                self._error(str(e), 500)
        else:
            self._error("Reflection callback not configured", 500)


class JobManagerServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    def __init__(self, port, automation_controller, scheduler_manager, cycle_manager, run_job_callback, run_reflection_callback):
        self.automation_controller = automation_controller
        self.scheduler_manager = scheduler_manager
        self.cycle_manager = cycle_manager
        self.run_job_callback = run_job_callback
        self.run_reflection_callback = run_reflection_callback
        super().__init__(("", port), JobManagerServerHandler)

def start_server(port, automation_controller, scheduler_manager, cycle_manager, run_job_callback, run_reflection_callback):
    server = JobManagerServer(port, automation_controller, scheduler_manager, cycle_manager, run_job_callback, run_reflection_callback)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server
