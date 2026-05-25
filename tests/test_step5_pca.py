# RED: PCA + ABC 验证测试
# 在 bulk 数据上验证 PCA 是否恢复已知的力指纹方向
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

def test_pca_recovers_shear_direction():
    """
    用 GSE23289 的 bulk DEG 跑 PCA:
    91 条 Shear 独有通路的得分矩阵 → PCA
    PC1 载荷应偏向正 NES 通路（保护方向）
    PC2 载荷应偏向负 NES 通路（静息方向）
    """
    # 从 Step 2 已知:
    # 正 NES 通路 = 高剪上调（保护）: ER加工, MAPK, 矿物吸收...
    # 负 NES 通路 = 高剪下调（静息）: 核糖体, 氧化磷酸化, DNA复制...
    pass  # 需要 bulk 通路得分矩阵——Step 2 已有 GSEA 结果

def test_pca_variance_explained():
    """PC1 + PC2 应解释 >50% 的总方差（二维够了的判据）"""
    pass

def test_pca_without_abc_fails():
    """
    不用 ABC 预选的 91 条通路（用全部 165 条）:
    PC1/PC2 的方差解释比例应显著降低 —— 
    因为包含非力学通路（Hcy 也有信号的）稀释了力信号
    """
    pass

if __name__ == "__main__":
    print("RED: 测试框架就位。需要 bulk 通路得分矩阵来运行。")
    print("测试逻辑:")
    print("  1. PC1 载荷在正 NES 通路上显著 > 0")
    print("  2. PC2 载荷在负 NES 通路上显著 < 0")  
    print("  3. PC1+PC2 > 50% 方差解释")
    print("  4. ABC 预选提升方差解释比例")
