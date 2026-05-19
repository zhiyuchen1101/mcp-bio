"""
R 进程管理 — 启动/停止/监控 Watcher 和辅助服务。

不依赖 MCP、不依赖 FastMCP。由 r_session_bridge 包装为 MCP 工具。
"""
import os
import socket
import time
import atexit
import subprocess
from config import BOARD_API_PORT, R_SOCKET_PORT


# ── Board API ──

_board_api_proc = None


def ensure_board_api(project_dir: str):
    """确保 Board API 在运行。已运行则跳过。"""
    global _board_api_proc

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_open = s.connect_ex(("localhost", BOARD_API_PORT)) == 0
    s.close()
    if port_open:
        return

    api_path = os.path.join(project_dir, "board_api.py")
    _board_api_proc = subprocess.Popen(
        ["python3", api_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    for _ in range(10):
        time.sleep(0.3)
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ready = s2.connect_ex(("localhost", BOARD_API_PORT)) == 0
        s2.close()
        if ready:
            break

    def _cleanup():
        if _board_api_proc and _board_api_proc.poll() is None:
            _board_api_proc.terminate()
            _board_api_proc.wait(timeout=3)

    atexit.register(_cleanup)


# ── Watcher ──

_watcher_process = None


def start_watcher(project_dir: str, r_lib: str) -> str:
    """启动 headless R Watcher。等端口就绪后返回状态字符串。"""
    global _watcher_process

    if _watcher_process is not None and _watcher_process.poll() is None:
        return f"Watcher already running (PID: {_watcher_process.pid})"

    watcher_path = os.path.join(project_dir, "src", "rstudio_watcher.R")
    env = os.environ.copy()
    env["https_proxy"] = "http://127.0.0.1:7897"
    env["http_proxy"] = "http://127.0.0.1:7897"

    err_log = os.path.join(project_dir, "watcher_stderr.log")
    out_log = os.path.join(project_dir, "watcher_stdout.log")
    out_fh = open(out_log, "w")
    err_fh = open(err_log, "w")

    _watcher_process = subprocess.Popen(
        ["R", "--no-save", "--no-restore", "--slave", "-e",
         f'.libPaths(c("{r_lib}", .libPaths())); source("{watcher_path}")'],
        stdout=out_fh, stderr=err_fh,
        cwd=project_dir,
        env=env,
    )

    r_port = int(os.environ.get("R_SOCKET_PORT", R_SOCKET_PORT))
    for _ in range(30):
        time.sleep(1)
        if _watcher_process.poll() is not None:
            err_tail = ""
            try:
                with open(err_log) as f:
                    lines = f.readlines()
                    err_tail = "".join(lines[-3:])
            except Exception:
                pass
            return f"Watcher died (exit {_watcher_process.returncode}): {err_tail}"
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ready = s.connect_ex(("localhost", r_port)) == 0
        s.close()
        if ready:
            return f"Watcher started (PID: {_watcher_process.pid}, port {r_port} ready)"
    return f"Watcher started but port {r_port} not ready after 30s"


def watcher_status() -> str:
    """检查 Watcher 是否在运行。"""
    global _watcher_process
    if _watcher_process is None:
        return "Watcher not started. Use r_start_watcher."
    poll = _watcher_process.poll()
    if poll is None:
        return f"Watcher running (PID: {_watcher_process.pid})"
    return f"Watcher stopped (exit code: {poll})"


def stop_watcher() -> str:
    """停止 Watcher。"""
    global _watcher_process
    if _watcher_process is None:
        return "No watcher to stop."
    _watcher_process.terminate()
    try:
        _watcher_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _watcher_process.kill()
    _watcher_process = None
    return "Watcher stopped."



