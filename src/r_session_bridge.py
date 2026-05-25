"""
R Session MCP Bridge — MCP 薄壳

职责：暴露 MCP 工具给 TUI。R 代码生成委托 r_tools，进程管理委托 r_process。
Board 操作委托 board.py deep module。RBridge 委托 r_bridge.py。
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from r_bridge import RBridge
from r_shell import r_exec_shell
from board import get_board
from r_tools import get_variables_r, geo_meta_r, quick_degs_r, auto_degs_r, gsea_r, kegg_enrich_r
from r_process import ensure_board_api, start_watcher, watcher_status, stop_watcher
from config import R_SOCKET_PORT

mcp = FastMCP("R Session Bridge")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
R_LIB = os.path.expanduser("~/R/library")

# ── 启动 Board API ──
ensure_board_api(PROJECT_DIR)

# ── R Session（连 Watcher 的 httpuv）──
_r_bridge = None


def _get_bridge():
    global _r_bridge
    if _r_bridge is None:
        _r_bridge = RBridge(connect_port=R_SOCKET_PORT)
    return _r_bridge


def r_exec(code: str, timeout: int = 120) -> dict:
    bridge = _get_bridge()
    result = bridge.execute(code, timeout=timeout)
    return {
        "output": result.get("output", ""),
        "error": result.get("error"),
        "session_alive": result.get("session_alive", True),
    }


def r_shell_exec(code: str, timeout: int = 300) -> dict:
    """通过独立 Rscript 进程执行 R 代码——重操作专用。
    不依赖 HTTP socket，不触发 502。
    返回格式与 r_exec 兼容。
    """
    result = r_exec_shell(code, timeout=timeout, r_lib=R_LIB)
    return {
        "output": result.get("output", ""),
        "error": result.get("error"),
        "session_alive": True,  # 独立进程不维护 session 状态
    }


# ════════════════════════════════════════════
# MCP Tools
# ════════════════════════════════════════════

# ═══ 工具分层 ═══
# TUI 可直调（毫秒级）: board_*, r_get_variables, r_plot_show, r_watcher_*
# Agent 专用（分钟级）: bio_auto_degs, bio_gsea, bio_kegg_enrich, r_execute
# → 长工具走 Board dispatch（Watcher 异步执行），TUI 不直接调用


@mcp.tool()
def r_execute(code: str) -> str:
    """在持久 R session 中执行代码。变量在调用之间保持。"""
    result = r_exec(code)
    parts = []
    if result["output"]:
        parts.append(result["output"])
    if result["error"]:
        parts.append(f"[R Error] {result['error']}")
    if result.get("stderr"):
        parts.append(f"[stderr]\n{result['stderr']}")
    return "\n".join(parts) if parts else "(no output)"


@mcp.tool()
def r_get_variables() -> str:
    """列出持久 R session 中当前所有变量及其类型/大小。"""
    result = r_exec(get_variables_r())
    return result["output"] or "(empty environment)"


@mcp.tool()
def r_check_package(pkg: str) -> str:
    """检查 R 包是否已安装。"""
    result = r_exec(f'cat(requireNamespace("{pkg}", quietly=TRUE))')
    installed = result["output"] == "TRUE"
    return f"{pkg}: {'installed' if installed else 'NOT installed'}"


@mcp.tool()
def r_reset() -> str:
    """清空 R session 所有变量（通过 socket 执行 rm）。"""
    global _r_bridge
    _r_bridge = None
    r_exec("rm(list=ls(all.names=TRUE))", timeout=10)
    return "R session reset (variables cleared)."


@mcp.tool()
def r_plot_show(filepath: str) -> str:
    """用 macOS Preview 打开图片文件。生成 PNG 后调用此工具即可在桌面预览。"""
    import subprocess
    subprocess.run(["open", filepath], check=False)
    return f"Opened {filepath}"


# ── 生信快捷工具 ──

@mcp.tool()
def bio_geo_meta(gse_id: str) -> str:
    """获取 GEO 数据集的基本信息（样本数、分组、表型列）。"""
    result = r_exec(geo_meta_r(gse_id), timeout=120)
    return result["output"] or result.get("error", "(no output)")


@mcp.tool()
def bio_gsea(rank_by: str = "logFC") -> str:
    """
    GSEA 基因集富集分析（全基因排序，不卡阈值）。
    rank_by: "logFC" (两两比较, 默认) | "F" (ANOVA F-statistic 多组)
    基于当前 session 中的结果（需先跑 limma/ANOVA）。
    """
    result = r_shell_exec(gsea_r(rank_by), timeout=600)
    return result["output"] or result.get("error", "(no output)")


@mcp.tool()
def bio_auto_degs(gse_id: str, case: str = "", control: str = "") -> str:
    """
    一键差异表达：自动探测分组列 + 下载 GEO + limma。
    case/control 可为空（自动找第一组 2-level 列）。
    """
    result = r_shell_exec(auto_degs_r(gse_id, case, control), timeout=300)
    return result["output"] or result.get("error", "(no output)")


@mcp.tool()
def bio_quick_degs(gse_id: str, group_col: str, case: str, control: str) -> str:
    """
    快速差异表达分析（limma），返回 up/down 基因数。
    """
    result = r_exec(quick_degs_r(gse_id, group_col, case, control), timeout=180)
    return result["output"] or result.get("error", "(no output)")


@mcp.tool()
def bio_kegg_enrich() -> str:
    """
    KEGG/GO 富集分析。基于当前 session 中的 DEG 结果（需先跑 limma）。
    自动处理探针ID→Entrez转换。结果存入 last_kegg / last_go 变量。
    """
    # Note: 保留 socket —— 依赖 session 变量 (last_degs, last_gse_id)
    result = r_exec(kegg_enrich_r(), timeout=120)
    return result["output"] or result.get("error", "(no output)")


# ── 黑板系统 ──

@mcp.tool()
def board_init(task_name: str, context_json: str = "{}") -> str:
    """初始化协作黑板文件。"""
    board = get_board()
    ctx = json.loads(context_json) if context_json else {}
    board.init(task=task_name, context=ctx)
    return f"Board initialized for: {task_name}\nStatus: {board.status}"


@mcp.tool()
def board_check_help() -> str:
    """检查黑板是否有来自 aisdk 的未处理求助信号。"""
    board = get_board()
    pending = board.check()
    if not pending:
        return "(no pending help requests)"
    return json.dumps(pending, indent=2, ensure_ascii=False)


@mcp.tool()
def board_respond(help_id: int, level: str, response: str) -> str:
    """响应 aisdk 的求助。"""
    board = get_board()
    board.respond(help_id=help_id, level=level, response=response)
    return f"Response (level={level}) sent to help request #{help_id}. Agent can now continue."


@mcp.tool()
def board_read_log() -> str:
    """TUI 读取 agent 运行日志，查看实时进度。"""
    board = get_board()
    logs = board.agent_log
    if not logs:
        return "(no agent activity yet)"
    recent = logs[-20:]
    lines = []
    for e in recent:
        icon = "❌" if e.get("has_error") else "✅"
        lines.append(f"{icon} {e.get('tool','?')}: {e.get('result_preview','')[:100]}")
    log_text = "\n".join(lines)
    disc = board.discussion
    if disc:
        disc_lines = [f"[{d.get('from','?')}] {d.get('question','')[:150]}" for d in disc[-5:]]
        return log_text + "\n--- Discussion ---\n" + "\n".join(disc_lines)
    return log_text


@mcp.tool()
def board_optimize() -> str:
    """审查 agent 日志，总结错误模式和优化建议。"""
    board = get_board()
    logs = board.agent_log
    if not logs:
        return "(no logs to analyze)"

    errors = [e for e in logs if e.get("has_error")]
    hints = []
    error_msgs = [e.get("result_preview", "") for e in errors]
    if error_msgs:
        from collections import Counter
        error_counts = Counter(msg[:60] for msg in error_msgs)
        for msg, count in error_counts.most_common(3):
            if count >= 2:
                hints.append(f"重复错误({count}x): {msg}")

    total_steps = len(logs)
    error_rate = len(errors) / max(total_steps, 1)
    if error_rate > 0.3:
        hints.append(f"错误率 {error_rate:.0%} — 建议简化子任务或用 L3 直接给代码")
    elif error_rate == 0:
        hints.append("零错误 — 当前任务复杂度合适，可以加大步长")

    summary = "\n".join(hints) if hints else "(no issues found)"
    if board.context:
        board.context["optimization_hints"] = summary
    board.flush()
    return f"优化审查完成:\n{summary}"


# ── Watcher / Plot Server ──

@mcp.tool()
def r_start_watcher() -> str:
    """启动 headless R watcher 进程（后台监控黑板）。"""
    return start_watcher(os.path.dirname(PROJECT_DIR), R_LIB)


@mcp.tool()
def r_watcher_status() -> str:
    """检查 headless watcher 是否在运行。"""
    return watcher_status()


@mcp.tool()
def r_stop_watcher() -> str:
    """停止 headless watcher。"""
    return stop_watcher()


if __name__ == "__main__":
    mcp.run()
