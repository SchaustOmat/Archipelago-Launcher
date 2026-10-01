"""Receiver for Ship of Harkinian's "Sail" remote interface.

SoH connects as a TCP client to 127.0.0.1:43384 and sends NUL-terminated JSON. We only listen for
hook events: OnTransitionEnd / OnSceneInit tell us which scene (area or dungeon) Link is in.
"""
import json
import socket
import threading
import time

SAIL_HOST = "127.0.0.1"
SAIL_PORT = 43384


class SailServer:
    def __init__(self, port: int = SAIL_PORT):
        self.port = port
        self.scene: int | None = None
        self.scene_time = 0.0
        self.connected = False
        self.stopped = False
        self.sock = None

    def start(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.sock.bind((SAIL_HOST, self.port))
            self.sock.listen(2)
        except OSError:
            self.sock = None  # another launcher already listens; that one gets the events
            return False
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return True

    def stop(self):
        self.stopped = True
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass

    def _accept_loop(self):
        while not self.stopped:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _client(self, conn):
        self.connected = True
        buf = b""
        try:
            while not self.stopped:
                data = conn.recv(65536)
                if not data:
                    break
                buf += data
                while b"\0" in buf:
                    raw, buf = buf.split(b"\0", 1)
                    self._handle(raw)
        except OSError:
            pass
        finally:
            self.connected = False
            conn.close()

    def _handle(self, raw: bytes):
        try:
            msg = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            return
        hook = msg.get("hook") if isinstance(msg, dict) else None
        if not isinstance(hook, dict):
            return
        if hook.get("type") in ("OnTransitionEnd", "OnSceneInit") and "sceneNum" in hook:
            self.scene = int(hook["sceneNum"])
            self.scene_time = time.time()
        elif hook.get("type") == "OnExitGame":
            self.scene = None
