"""
r_shell — 通过独立 Rscript 进程执行 R 代码

替代 RBridge HTTP socket 用于重操作（GEO下载、GSEA、包安装等）。
毫秒级查询仍走 socket。
"""
import subprocess
import tempfile
import os
import time


def r_exec_shell(code: str, timeout: int = 300, r_lib: str = None) -> dict:
    """
    将 R 代码写入临时文件，通过 Rscript 子进程执行。

    返回:
        {"output": str, "error": str or None, "return_code": int, "elapsed": float}
    """
    lib_paths = f'.libPaths(c("{r_lib or os.path.expanduser("~/R/library")}", .libPaths()))'
    wrapper = f"""
{lib_paths}
{code}
"""

    fd, script_path = tempfile.mkstemp(suffix=".R", prefix="r_shell_")
    with os.fdopen(fd, 'w') as f:
        f.write(wrapper)

    t0 = time.time()
    try:
        proc = subprocess.run(
            ["Rscript", "--no-save", "--no-restore", script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - t0
        output = proc.stdout
        error = proc.stderr if proc.stderr else None
        if proc.returncode != 0 and not error:
            error = f"Rscript exit code {proc.returncode}"
        return {
            "output": output,
            "error": error,
            "return_code": proc.returncode,
            "elapsed": elapsed,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        return {
            "output": "",
            "error": f"R code exceeded {timeout}s timeout",
            "return_code": -1,
            "elapsed": elapsed,
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "output": "",
            "error": str(e),
            "return_code": -1,
            "elapsed": elapsed,
        }
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
