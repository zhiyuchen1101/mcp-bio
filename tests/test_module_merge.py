# RED: bio_geo_meta + bio_quick_degs 合并测试
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from r_tools import geo_meta_r, quick_degs_r

def test_combined_flow():
    """合并后的 auto_degs 应返回 metadata + DEG 结果"""
    # 模拟: 自动查列名找分组列
    meta_code = geo_meta_r("GSE175735")
    assert "pData" in meta_code or "colnames" in meta_code.lower() or "table" in meta_code.lower()
    
    # 模拟: 自动跑 DEG
    degs_code = quick_degs_r("GSE175735", "treatment:ch1", "Hyperhomocysteinemia", "control")
    assert "lmFit" in degs_code
    assert "topTable" in degs_code
    assert "last_degs" in degs_code

if __name__ == "__main__":
    test_combined_flow()
    print("PASS")
