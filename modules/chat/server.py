import http.server
import socketserver
import json
import os
import threading
import time

# Configuration
PORT = 8005

class ChatServerHandler(http.server.SimpleHTTPRequestHandler):

    def _set_headers(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*') # Allow CORS
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_POST(self):
        if self.path == '/api/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                user_message = data.get('message', '')

                print(f"Received message: {user_message}")

                # Mock Response Logic
                # In a real integration, this would talk to the LLM backend.
                # Since we cannot modify v4 backend, we simulate a response.

                response_text = f"I received your message: \"{user_message}\".\n\n(Note: This is a response from the standalone Chat Server on port {PORT}. The v4 LLM backend is disconnected in this mode.)"

                response_data = {
                    "response": response_text
                }

                self._set_headers()
                self.wfile.write(json.dumps(response_data).encode('utf-8'))

            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid JSON"}')
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    with socketserver.ThreadingTCPServer(("", PORT), ChatServerHandler) as httpd:
        print(f"Chat API Server serving at port {PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
