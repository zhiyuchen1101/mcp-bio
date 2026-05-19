"""
MCP 工具回归测试
需要 Watcher (:19886) 和 Board API (:19890) 运行。
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from r_session_bridge import (
    r_execute, r_get_variables, board_init, board_check_help,
    board_respond, board_read_log, board_optimize,
)
from board import get_board, reset_board

# 确保 Board 单例使用正确路径
reset_board()


def test_r_execute_basic():
    """r_execute 执行基本 R 代码"""
    result = r_execute("x <- 2+2; cat(x)")
    assert "4" in result, f"Expected 4, got: {result}"
    assert "ERROR" not in result.upper() or "[R Error]" not in result, f"Unexpected error: {result}"


def test_r_execute_error_handling():
    """r_execute 对 R 错误的处理 — stop() 的输出包含 ERROR:"""
    result = r_execute("stop('test error')")
    assert "ERROR" in result, f"Expected ERROR in output: {result}"


def test_r_get_variables():
    """r_get_variables 列出 session 变量"""
    r_execute("test_var_mcp <- 42")
    result = r_get_variables()
    assert "test_var_mcp" in result, f"Expected test_var_mcp in: {result}"


def test_board_init_and_read():
    """board_init 创建任务 → Board 状态 working"""
    result = board_init("MCP 回归测试", json.dumps({"purpose": "test"}))
    assert "Board initialized" in result, f"Expected init confirmation: {result}"
    
    b = get_board()
    assert b.status == "working", f"Expected working, got: {b.status}"
    assert "MCP 回归测试" in b.current_task


def test_board_check_help_empty():
    """board_check_help 无求助时返回 no pending"""
    result = board_check_help()
    assert "no pending" in result, f"Expected no pending, got: {result}"


def test_board_read_log_empty():
    """board_read_log 无日志时返回 no activity"""
    result = board_read_log()
    assert "no agent activity" in result, f"Expected no activity: {result}"


def test_board_respond():
    """board_respond 响应求助但不改 status——恢复由 Watcher 触发"""
    b = get_board()
    b._help_requests = [{"id": 1, "status": "pending", "question": "test?"}]
    b._status = "blocked"
    b.flush()
    
    result = board_respond(help_id=1, level="L1", response="用 tissue:ch1")
    assert "sent" in result, f"Expected sent: {result}"
    # respond 不改变 status——Watcher 自己检测 help_responses 并恢复
    assert b.status == "blocked", f"Expected blocked, got {b.status}"
    assert b.help_requests[0]["status"] == "resolved"


def test_board_optimize_with_logs():
    """board_optimize 分析有错误的日志"""
    b = get_board()
    b._agent_log = [
        {"tool": "run_r_code", "result_preview": "ERROR: x not found", "has_error": True},
        {"tool": "run_r_code", "result_preview": "ERROR: x not found", "has_error": True},
        {"tool": "run_r_code", "result_preview": "OK", "has_error": False},
    ]
    b.flush()
    
    result = board_optimize()
    assert "重复错误" in result, f"Expected repeated error detection: {result}"


def test_board_api_auto_started():
    """Board API 应在 MCP Server 导入时自动拉起"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("localhost", 19890))
    sock.close()
    assert result == 0, f"Board API port 19890 not reachable (code: {result})"


def test_r_start_watcher_waits_for_port():
    """r_start_watcher 返回时端口 19886 应已就绪"""
    import socket, time, subprocess
    from r_session_bridge import r_stop_watcher, r_start_watcher

    # 先杀外部启动的 Watcher
    subprocess.run(["pkill", "-f", "rstudio_watcher.R"], capture_output=True)
    time.sleep(1)

    # 启动
    result = r_start_watcher()
    assert "started" in result.lower(), f"Expected started: {result}"

    # 验证端口就绪
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_open = sock.connect_ex(("localhost", 19886)) == 0
    sock.close()
    assert port_open, f"Port 19886 not open after r_start_watcher returned: {result}"
