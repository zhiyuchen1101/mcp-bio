# RED: GSEA 工具测试
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from r_tools import gsea_r

def test_gsea_uses_ranked_list():
    """GSEA 应使用全基因排序（不卡阈值）"""
    code = gsea_r()
    assert "logFC" in code, "should rank by logFC"
    assert "gseKEGG" in code or "GSEA" in code, "should call GSEA function"
    assert "last_degs" in code, "should use existing DEG result"

def test_gsea_saves_result():
    """GSEA 结果应存到 last_gsea"""
    code = gsea_r()
    assert "last_gsea" in code

def test_gsea_no_cutoff():
    """GSEA 不应卡 adj.P 阈值"""
    code = gsea_r()
    # 不应过滤 p 值
    assert "adj.P.Val < 0.05" not in code.split("#")[0]  # 不在非注释行

if __name__ == "__main__":
    test_gsea_uses_ranked_list()
    test_gsea_saves_result()
    test_gsea_no_cutoff()
    print("PASS")
