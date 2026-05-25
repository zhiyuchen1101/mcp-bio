"""
R_Bridge — 通过 httpuv socket 连接 Watcher 的持久 R Session

单一职责：发送 R 代码到 httpuv 服务器，返回输出/超时/崩溃信号。
"""
import json
import threading
import urllib.request


class RBridge:
    """通过 HTTP socket 连接 Watcher 的 R Session。"""

    def __init__(self, connect_port: int):
        self._connect_port = connect_port
        self._lock = threading.Lock()

    def execute(self, code: str, timeout: int = 120) -> dict:
        with self._lock:
            return self._execute(code, timeout)

    def _execute(self, code: str, timeout: int) -> dict:
        try:
            req_data = json.dumps({"code": code}).encode()
            req = urllib.request.Request(
                f"http://localhost:{self._connect_port}",
                data=req_data,
                headers={"Content-Type": "application/json", "Connection": "close"},
            )
            resp = urllib.request.urlopen(req, timeout=timeout)
            resp_data = json.loads(resp.read().decode())
            return {
                "output": resp_data.get("output", ""),
                "error": resp_data.get("error"),
                "session_alive": True,
            }
        except Exception as e:
            err_str = str(e)
            if "timed out" in err_str.lower():
                return {
                    "output": "TIMEOUT",
                    "error": f"R code exceeded {timeout}s timeout",
                    "session_alive": True,
                }
            return {
                "output": "SESSION_DIED",
                "error": str(e),
                "session_alive": False,
            }

    def get_vars(self) -> str:
        result = self.execute("print(ls(all.names=TRUE))")
        return result["output"]

    def close(self):
        pass  # socket 模式无需显式关闭
