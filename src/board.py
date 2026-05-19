"""
Board — 协作黑板状态机（deep module）

职责：task_board.json 的唯一写者。管理状态转换、求助队列、Agent 执行日志、讨论记录。
HTTP API (board_api.py) 和 MCP tools (r_session_bridge.py) 都通过 Board 读写黑板。
"""
import json
import os
import time
from datetime import datetime

# ── 状态常量（唯一权威定义，watcher.R 注释同步）──
STATUS_IDLE = "idle"              # 无任务
STATUS_WORKING = "working"        # Agent 执行中 / 新任务
STATUS_BLOCKED = "blocked"        # 求助升级，等待 TUI 回复
STATUS_DISCUSSING = "discussing"  # Agent 发起讨论，等待 TUI
STATUS_VERIFYING = "verifying"    # Worker 完成，Verifier 检查中
STATUS_DONE = "done"              # 分析完成
STATUS_ERROR = "error"            # 分析失败


class Board:
    """协作黑板。唯一写者。"""

    def __init__(self, board_path: str = None):
        if board_path is None:
            project_dir = os.environ.get("MCP_PROJECT_DIR", os.getcwd())
            board_path = os.path.join(project_dir, "task_board.json")
        self._board_path = board_path
        # ── 核心状态 ──
        self._status = "idle"
        self._current_task = ""
        self._session_id = ""
        self._context = {}
        # ── 协作 ──
        self._help_requests = []
        self._help_responses = []
        self._discussion = []
        # ── 执行锁 ──
        self._agent_status = "idle"
        # ── Agent 输出 ──
        self._agent_log = []
        self._last_result = ""
        self._last_steps = 0
        self._worker_result = {}
        # ── Verifier ──
        self._verifier_summary = ""

    # ── 属性 ──

    @property
    def status(self) -> str:
        return self._status

    @property
    def current_task(self) -> str:
        return self._current_task

    @property
    def context(self) -> dict:
        return self._context

    @property
    def help_requests(self) -> list:
        return self._help_requests

    @property
    def help_responses(self) -> list:
        return self._help_responses

    @property
    def agent_status(self) -> str:
        return self._agent_status

    @property
    def agent_log(self) -> list:
        return self._agent_log

    @property
    def discussion(self) -> list:
        return self._discussion

    @property
    def verifier_summary(self) -> str:
        return self._verifier_summary

    # ── 核心操作 ──

    def init(self, task: str, context: dict = None):
        """初始化新任务。agent_status=running 时拒绝。"""
        if self._agent_status == "running":
            raise RuntimeError("Agent is running, cannot init new task")

        self._current_task = task
        self._session_id = f"{task}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._context = context or {}
        self._status = "working"
        self._agent_status = "idle"
        self._help_requests = []
        self._help_responses = []
        self._discussion = []
        self._agent_log = []
        self._last_result = ""
        self._last_steps = 0
        self._worker_result = {}
        self._verifier_summary = ""
        self._flush()

    def check(self) -> list:
        """返回待处理的求助列表。"""
        return [r for r in self._help_requests if r.get("status") == "pending"]

    def respond(self, help_id: int, level: str, response: str):
        """响应求助。不改变 status——恢复由 Watcher 驱动。"""
        resp_entry = {
            "id": len(self._help_responses) + 1,
            "to_help_id": help_id,
            "level": level,
            "response": response,
            "timestamp": datetime.now().isoformat(),
        }
        self._help_responses.append(resp_entry)
        for r in self._help_requests:
            if r.get("id") == help_id:
                r["status"] = "resolved"
        self._flush()

    def set_agent_running(self):
        self._agent_status = "running"

    def set_agent_idle(self):
        self._agent_status = "idle"

    def update_fields(self, data: dict):
        """从 dict 更新 Board 字段（供 Watcher 通过 board_api 写入）。
        
        安全更新：只写入 Board 已知的字段，忽略未知 key。
        """
        known = {
            "status", "current_task", "session_id", "context",
            "help_requests", "help_responses", "discussion",
            "agent_status", "agent_log",
            "last_result", "last_steps", "worker_result",
            "verifier_summary",
        }
        for key, val in data.items():
            if key in known:
                setattr(self, f"_{key}", val)
        self._flush()

    def read_full(self) -> dict:
        """返回完整 Board 状态（供 GET /board 和调试）。"""
        return {
            "_protocol_version": "1.0",
            "status": self._status,
            "current_task": self._current_task,
            "session_id": self._session_id,
            "context": self._context,
            "help_requests": self._help_requests,
            "help_responses": self._help_responses,
            "discussion": self._discussion,
            "agent_status": self._agent_status,
            "agent_log": self._agent_log,
            "last_result": self._last_result,
            "last_steps": self._last_steps,
            "worker_result": self._worker_result,
            "verifier_summary": self._verifier_summary,
            "_updated_at": time.time(),
        }

    def flush(self):
        """公开 flush（供 board_api 调用）。"""
        self._flush()

    # ── handle_* 方法：参数提取 + 响应组装都在 Board，薄壳只转发 ──

    def handle_init(self, body: dict) -> dict:
        """接收 HTTP body dict，提取参数，初始化，返回响应 dict"""
        self.init(task=body.get("task", ""), context=body.get("context", {}))
        return {"status": self._status, "current_task": self._current_task,
                "agent_status": self._agent_status}

    def handle_respond(self, body: dict) -> dict:
        """接收 HTTP body dict，提取参数，响应求助，返回响应 dict"""
        self.respond(
            help_id=body.get("help_id", 0),
            level=body.get("level", "L1"),
            response=body.get("response", ""),
        )
        return {"status": self._status}

    def handle_update(self, body: dict) -> dict:
        """接收 HTTP body dict，更新字段，返回响应 dict"""
        self.update_fields(body)
        return {"status": self._status, "agent_status": self._agent_status,
                "verifier_summary": self._verifier_summary}

    def handle_check(self) -> dict:
        """返回待处理求助列表"""
        return {"pending": self.check()}

    def _flush(self):
        with open(self._board_path, "w") as f:
            json.dump(self.read_full(), f, indent=2, ensure_ascii=False)


# ── 模块级单例 ──
_board_instance = None


def get_board(board_path: str = None) -> Board:
    global _board_instance
    if _board_instance is None:
        _board_instance = Board(board_path)
    return _board_instance


def reset_board():
    global _board_instance
    _board_instance = None
