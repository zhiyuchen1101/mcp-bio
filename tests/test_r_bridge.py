"""
R_Bridge 模块测试 — socket 模式
需要 Watcher 的 httpuv 在 19886 端口运行。
"""
import os
from r_bridge import RBridge

# 默认连 Watcher 的 R socket
R_PORT = int(os.environ.get("R_SOCKET_PORT", 19886))


def test_r_bridge_execute_returns_output():
    """socket 模式：执行 R 代码返回输出"""
    bridge = RBridge(connect_port=R_PORT)
    result = bridge.execute("print(2+2)")
    assert "[1] 4" in result["output"], f"Expected '[1] 4', got: {result['output']}"
    assert result["session_alive"] is True


def test_r_bridge_get_vars_lists_variables():
    """socket 模式：变量持久化"""
    bridge = RBridge(connect_port=R_PORT)
    bridge.execute("x_test_vars <- 42")
    vars_output = bridge.get_vars()
    assert "x_test_vars" in vars_output


def test_r_bridge_timeout_returns_signal():
    """socket 模式：超时返回 TIMEOUT"""
    bridge = RBridge(connect_port=R_PORT)
    result = bridge.execute("Sys.sleep(10)", timeout=2)
    assert result["output"] == "TIMEOUT", f"Expected TIMEOUT, got: {result}"


def test_r_bridge_detects_dead_session():
    """socket 模式：连不存在的端口返回 SESSION_DIED"""
    bridge = RBridge(connect_port=19999)  # 不存在的端口
    result = bridge.execute("print(1)")
    assert result["session_alive"] is False
    assert "SESSION_DIED" in result["output"]


def test_r_bridge_socket_mode_only():
    """验证 RBridge 只接受 connect_port 参数（不再有无连接模式）"""
    # 无 connect_port 应该报错
    try:
        RBridge()
        assert False, "RBridge() without connect_port should raise"
    except (TypeError, ValueError, RuntimeError):
        pass  # expected
