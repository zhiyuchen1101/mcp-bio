"""
Board 模块测试
"""
from board import Board


def test_board_init_creates_working_status():
    board = Board()
    board.init(task="GSE55235 差异分析", context={"group_col": "tissue:ch1"})
    assert board.status == "working"
    assert board.current_task == "GSE55235 差异分析"
    assert board.help_requests == []
    assert board.help_responses == []


def test_board_respond_resolves_help_does_not_change_status():
    """respond 标记求助已处理但不改 status——恢复由 Watcher 驱动"""
    board = Board(board_path="/tmp/test_board_respond.json")
    board._help_requests = [
        {"id": 1, "level": "L1", "question": "列名是什么？", "status": "pending"}
    ]
    board._status = "blocked"
    board.respond(help_id=1, level="L1", response="用 tissue:ch1")
    assert board.status == "blocked"  # 不改 status
    assert board.help_requests[0]["status"] == "resolved"
    assert len(board.help_responses) == 1


def test_board_check_help_returns_pending():
    board = Board(board_path="/tmp/test_board_check.json")
    board._help_requests = [
        {"id": 1, "level": "L1", "question": "列名？", "status": "pending"},
        {"id": 2, "level": "L2", "question": "方向？", "status": "resolved"},
    ]
    pending = board.check()
    assert len(pending) == 1
    assert pending[0]["id"] == 1


def test_board_check_empty_when_all_resolved():
    board = Board(board_path="/tmp/test_board_check2.json")
    board._help_requests = [
        {"id": 1, "level": "L1", "question": "列名？", "status": "resolved"},
    ]
    assert board.check() == []


def test_board_auto_flush_persists_to_file():
    """验证 init() 自动 flush 到文件"""
    board = Board(board_path="/tmp/test_board_flush.json")
    board.init(task="自动持久化测试", context={"key": "value"})
    import json
    with open("/tmp/test_board_flush.json") as f:
        data = json.load(f)
    assert data["status"] == "working"
    assert data["current_task"] == "自动持久化测试"
    assert data["context"]["key"] == "value"


def test_board_agent_lock_blocks_concurrent_init():
    board = Board(board_path="/tmp/test_board_agent_lock.json")
    board.init(task="任务1")
    board._agent_status = "running"
    raised = False
    try:
        board.init(task="任务2")
    except RuntimeError:
        raised = True
    assert raised, "agent running 时 init 应该抛 RuntimeError"


def test_handle_init_returns_correct_response():
    """handle_init 应提取参数 + 返回标准响应 dict"""
    board = Board(board_path="/tmp/test_handle.json")
    result = board.handle_init({"task": "handle test", "context": {"key": "val"}})
    assert result["status"] == "working"
    assert result["current_task"] == "handle test"
    assert result["agent_status"] == "idle"


def test_handle_update_returns_correct_response():
    """handle_update 应更新字段 + 返回标准响应 dict"""
    board = Board(board_path="/tmp/test_handle2.json")
    board.handle_init({"task": "pre"})
    result = board.handle_update({"verifier_summary": "test passed", "status": "done"})
    assert result["status"] == "done"
    assert result["verifier_summary"] == "test passed"
