import os
import platform
import subprocess
import time
import asyncio
import json
import struct
from typing import Optional, Dict
from pathlib import Path
from fastapi import WebSocket, WebSocketDisconnect

from services.claude import claude_run_manager
import core.state as state

if platform.system() != "Windows":
    import pty
    import termios
    import fcntl

class WebTerminalSession:
    def __init__(self, session_id: str, cwd: Optional[str] = None):
        self.id = session_id
        self.created_at = time.time()
        self.cwd = cwd
        self.cols = 80
        self.rows = 24
        self.process = None
        self.master_fd = None
        self.os_type = platform.system()
        self.loop = asyncio.get_running_loop()
        self.history = []
        self.subscribers: set[WebSocket] = set()
        self.reader_task = None
        self.closed = False
        self._start()

    def _start(self):
        if self.os_type == "Windows":
            self.process = subprocess.Popen(
                ["cmd.exe"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                shell=False,
                cwd=self.cwd
            )
            self.reader_task = asyncio.create_task(self._read_loop())
        else:
            self.closed = True
            self.history.append("Internal Error: WebTerminalSession used on Linux. Use LocalPTYSession.\r\n")

    async def _read_loop(self):
        while not self.closed:
            data = await self._read_output()
            if not data:
                break
            try:
                text = data.decode(errors="replace")
                self.history.append(text)
                if len(self.history) > 1000:
                     self.history = self.history[-1000:]
                await self._broadcast(text)
            except Exception as e:
                break
        if not self.closed:
             msg = "\r\n\x1b[1;31m[Process terminated]\x1b[0m\r\n"
             self.history.append(msg)
             await self._broadcast(msg)
        self.close()

    async def _broadcast(self, text: str):
        msg = json.dumps({"type": "output", "data": text})
        to_remove = []
        for ws in self.subscribers:
            try:
                await ws.send_text(msg)
            except:
                to_remove.append(ws)
        for ws in to_remove:
            self.subscribers.discard(ws)

    async def _read_output(self):
        if self.os_type == "Windows":
            return await self.loop.run_in_executor(None, self._read_windows)
        else:
            return await self.loop.run_in_executor(None, self._read_linux)

    def _read_windows(self):
        if self.process and self.process.stdout:
            return self.process.stdout.read(1024)
        return b""

    def _read_linux(self):
        if self.master_fd:
            try:
                return os.read(self.master_fd, 1024)
            except OSError:
                return b""
        return b""

    def write_input(self, data: str):
        if self.closed: return
        if self.os_type == "Windows":
            if self.process and self.process.stdin:
                try:
                    self.process.stdin.write(data.encode())
                    self.process.stdin.flush()
                except: pass
        else:
            if self.master_fd:
                try:
                    os.write(self.master_fd, data.encode())
                except: pass

    def resize(self, cols, rows):
        self.cols = cols
        self.rows = rows
        if self.os_type != "Windows" and self.master_fd is not None:
            try:
                winsize = struct.pack("HHHH", rows, cols, 0, 0)
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            except: pass

    def close(self):
        self.closed = True
        if self.process:
            self.process.terminate()
        if self.os_type != "Windows" and self.master_fd:
            try: os.close(self.master_fd)
            except: pass


class LocalPTYSession(WebTerminalSession):
    def _start(self):
        if self.os_type == "Windows":
            self.closed = True
            self.history.append("Local PTY mode is not supported on Windows.\r\n")
            return

        shell = os.environ.get("SHELL", "/bin/bash")
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        claude_bin = claude_run_manager._resolve_claude_binary()
        if claude_bin:
            env["LYRN_CLAUDE_BIN"] = claude_bin
            bin_dir = str(Path(claude_bin).parent)
            path_val = env.get("PATH", "")
            if bin_dir not in path_val.split(os.pathsep):
                env["PATH"] = bin_dir + (os.pathsep + path_val if path_val else "")

        # Set Anthropic Proxy Environment Variables
        # Attempt to read port from port.txt + 1
        default_port = 8001
        try:
            if os.path.exists("port.txt"):
                with open("port.txt", "r") as f:
                    val = f.read().strip()
                    if val.isdigit():
                        default_port = int(val) + 1
        except:
            pass

        host = os.environ.get("LCC_HOST", "127.0.0.1")
        port = os.environ.get("LCC_PORT", str(default_port))
        base_url = f"http://{host}:{port}"

        env["ANTHROPIC_BASE_URL"] = base_url
        env["ANTHROPIC_AUTH_TOKEN"] = "lyrn"
        env["ANTHROPIC_API_KEY"] = ""
        env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"


        try:
            pid, master_fd = pty.fork()
            if pid == 0:
                if self.cwd:
                    try: os.chdir(self.cwd)
                    except: pass
                try:
                    os.execve(shell, [shell], env)
                except Exception as e:
                    os._exit(1)
            else:
                self.pid = pid
                self.master_fd = master_fd
                self.reader_task = asyncio.create_task(self._read_loop())
        except Exception as e:
            self.history.append(f"Error: Failed to start PTY. {str(e)}\r\n")
            self.close()

    def close(self):
        self.closed = True
        if hasattr(self, 'pid') and self.pid:
            try:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, os.WNOHANG)
            except: pass
        if self.master_fd:
            try: os.close(self.master_fd)
            except: pass

terminal_sessions: Dict[str, WebTerminalSession] = {}
terminal_sessions_lock = asyncio.Lock()

async def get_or_create_terminal_session(sid: str, cwd: Optional[str]) -> WebTerminalSession:
    async with terminal_sessions_lock:
        existing = terminal_sessions.get(sid)
        if existing and not getattr(existing, "closed", True):
            return existing

        if platform.system() == "Windows":
            session = WebTerminalSession(sid, cwd=cwd)
        else:
            session = LocalPTYSession(sid, cwd=cwd)
        terminal_sessions[sid] = session
        return session

async def maybe_cleanup_terminal_session(sid: str):
    await asyncio.sleep(15)
    async with terminal_sessions_lock:
        session = terminal_sessions.get(sid)
        if not session:
            return
        if session.subscribers:
            return
        try:
            session.close()
        finally:
            terminal_sessions.pop(sid, None)
