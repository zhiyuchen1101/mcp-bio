"""
Board HTTP API — 纯路由薄壳。每个 endpoint 一行，参数提取和响应组装全在 Board 里。
"""
import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
from board import get_board
from config import BOARD_API_PORT


class BoardHandler(BaseHTTPRequestHandler):
    _board = None  # 延迟注入，可测试

    def _send(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _read(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _board_inst(self):
        if BoardHandler._board is None:
            BoardHandler._board = get_board()
        return BoardHandler._board

    def do_GET(self):
        b = self._board_inst()
        if self.path == "/board":
            self._send(b.read_full())
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        b = self._board_inst()
        body = self._read()
        handlers = {
            "/board/init":    lambda: b.handle_init(body),
            "/board/respond": lambda: b.handle_respond(body),
            "/board/update":  lambda: b.handle_update(body),
            "/board/check":   lambda: b.handle_check(),
        }
        handler = handlers.get(self.path)
        if handler:
            self._send(handler())
        else:
            self._send({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


def start():
    server = HTTPServer(("127.0.0.1", BOARD_API_PORT), BoardHandler)
    print(f"Board API: http://localhost:{BOARD_API_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    start()
