# RED: gsea_r 加 rank_by 参数测试
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from r_tools import gsea_r

def test_gsea_r_default_logFC():
    """默认 rank_by='logFC' 用 degs$logFC"""
    code = gsea_r()
    assert "logFC" in code, "default should use logFC"
    assert "ranked <- degs$logFC" in code or "logFC" in code

def test_gsea_r_rank_by_F():
    """rank_by='F' 用 fit$F"""
    code = gsea_r(rank_by="F")
    assert "$F" in code and "is.numeric" in code, "should rank by F-statistic"
    assert "F.p.value" not in code.split("#")[0]

def test_gsea_r_rank_by_logFC_explicit():
    """显式 rank_by='logFC'"""
    code = gsea_r(rank_by="logFC")
    assert "logFC" in code

def test_gsea_r_both_modes_save_to_same_variable():
    """不管 rank_by 是什么，结果都存 last_gsea"""
    for mode in ["logFC", "F"]:
        code = gsea_r(rank_by=mode)
        assert "last_gsea" in code

if __name__ == "__main__":
    test_gsea_r_default_logFC()
    test_gsea_r_rank_by_F()
    test_gsea_r_rank_by_logFC_explicit()
    test_gsea_r_both_modes_save_to_same_variable()
    print("PASS")