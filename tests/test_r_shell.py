# RED: r_shell — 子进程 R 执行测试
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from r_shell import r_exec_shell


def test_shell_executes_sleep_without_502():
    """15s sleep 在 shell 通道不应超时，且不依赖 HTTP"""
    result = r_exec_shell("Sys.sleep(15); cat('DONE')", timeout=30)
    assert "DONE" in result["output"], f"Expected DONE, got: {result}"
    assert result["return_code"] == 0
    assert 14 < result["elapsed"] < 17, f"Expected ~15s, got {result['elapsed']:.1f}s"
    assert "SESSION_DIED" not in result["output"]


def test_shell_handles_r_error():
    """R 代码错误时返回 error 字段，不抛异常"""
    result = r_exec_shell("stop('intentional')", timeout=10)
    assert result["return_code"] != 0
    assert result["error"] is not None or "Error" in result["output"]


def test_shell_timeout():
    """超时的 R 代码被正常捕获"""
    result = r_exec_shell("Sys.sleep(30)", timeout=2)
    assert "timeout" in result.get("error", "").lower()
    assert result["return_code"] == -1


def test_shell_parallel_execution():
    """两个独立 R 进程并发执行，总时长 ≈ max 而非 sum"""
    import concurrent.futures
    t0 = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(r_exec_shell, "Sys.sleep(8); cat('A')", 20)
        f2 = ex.submit(r_exec_shell, "Sys.sleep(8); cat('B')", 20)
        r1 = f1.result()
        r2 = f2.result()
    elapsed = time.time() - t0
    assert "A" in r1["output"]
    assert "B" in r2["output"]
    assert elapsed < 12, f"Parallel should take ~8s, took {elapsed:.1f}s"


def test_shell_handles_large_output():
    """大输出不会被截断"""
    code = """
x <- rnorm(10000)
cat(paste(x, collapse=','))
"""
    result = r_exec_shell(code, timeout=10)
    assert len(result["output"]) > 1000
    assert result["return_code"] == 0


if __name__ == "__main__":
    print("Test 1: Sleep without 502...")
    test_shell_executes_sleep_without_502()
    print("  PASS")

    print("Test 2: R error handling...")
    test_shell_handles_r_error()
    print("  PASS")

    print("Test 3: Timeout handling...")
    test_shell_timeout()
    print("  PASS")

    print("Test 4: Parallel execution...")
    test_shell_parallel_execution()
    print("  PASS")

    print("Test 5: Large output...")
    test_shell_handles_large_output()
    print("  PASS")

    print("\nALL TESTS PASSED")
