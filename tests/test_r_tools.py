"""
r_tools 合约测试 — 验证 R 代码生成器输出正确性。
不需要 Watcher 运行，纯字符串断言。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from r_tools import get_variables_r, geo_meta_r, quick_degs_r


def test_get_variables_r_contains_ls():
    """get_variables_r 应包含 ls() 遍历变量的代码"""
    code = get_variables_r()
    assert "ls(all.names=TRUE)" in code
    assert "class(val)" in code


def test_geo_meta_r_contains_schema_check():
    """geo_meta_r 应包含列名查看 + 分组分布（含 table()）"""
    code = geo_meta_r("GSE1009")
    assert "colnames(pd)" in code, f"Should check columns: {code[:80]}"
    assert "table(" in code, f"Should check group distribution: {code[:80]}"
    assert "getGEO" in code


def test_quick_degs_r_contains_limma_method():
    """quick_degs_r 应包含 limma 关键步骤"""
    code = quick_degs_r("GSE55235", "disease state:ch1", "RA", "ND")
    assert "lmFit" in code
    assert "eBayes" in code
    assert "topTable" in code
    assert "adj.P.Val < 0.05" in code
    assert "logFC > 1" in code or "logFC >1" in code


def test_quick_degs_r_preserves_group_param():
    """quick_degs_r 应正确插值分组参数"""
    code = quick_degs_r("GSE123", "source_name", "cancer", "normal")
    assert '"GSE123"' in code or "'GSE123'" in code
    assert "cancer" in code
    assert "normal" in code
