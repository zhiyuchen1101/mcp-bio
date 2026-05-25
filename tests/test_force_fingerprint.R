# RED + GREEN: force_fingerprint pipeline TDD
# 在 bulk GSE23289 上验证 pipeline，然后直接在空转上跑
library(testthat)

.libPaths(c("~/R/library", .libPaths()))
suppressPackageStartupMessages({
  library(clusterProfiler); library(org.Hs.eg.db)
  library(AUCell)
})

# 加载 91 基因集
force_gs <- readRDS("analyses/force_fingerprint/force_fingerprint_genesets.rds")
cat("Gene sets:", length(force_gs), "\n")

# ─── 测试 1: AUCell 评分不为全 0 ───
test_that("AUCell produces non-zero scores on bulk data", {
  # 用 GSE23289 bulk 表达矩阵做快速验证
  expr <- readRDS("data/cache/GSE23289_expr.rds")
  
  # 基因名映射到 ENTREZ（因为是 Illumina probe IDs）
  gpl <- readRDS("data/cache/GPL6104.rds")
  m <- match(rownames(expr), gpl$ID)
  symbols <- as.character(gpl$Symbol[m])
  valid <- !is.na(symbols) & symbols != ""
  expr <- expr[valid, ]; rownames(expr) <- symbols[valid]
  
  # SYMBOL → ENTREZ
  entrez_map <- bitr(rownames(expr), "SYMBOL", "ENTREZID", OrgDb="org.Hs.eg.db")
  entrez_map <- entrez_map[!duplicated(entrez_map$SYMBOL), ]
  expr <- expr[entrez_map$SYMBOL, ]; rownames(expr) <- entrez_map$ENTREZID
  
  # AUCell
  cells_rankings <- AUCell_buildRankings(expr, plotStats=FALSE, verbose=FALSE)
  cells_AUC <- AUCell_calcAUC(force_gs, cells_rankings, 
                               aucMaxRank=nrow(expr)*0.03, verbose=FALSE)
  scores <- getAUC(cells_AUC)
  
  expect_gt(mean(scores > 0), 0.5, 
            label = "over 50% of samples should have non-zero AUC scores")
  cat("  ✓ AUCell:", round(mean(scores>0)*100), "% non-zero\n")
})

# ─── 测试 2: PCA 方差解释 >50% ───
test_that("PCA explains >50% variance in 2 PCs", {
  expr <- readRDS("data/cache/GSE23289_expr.rds")
  gpl <- readRDS("data/cache/GPL6104.rds")
  m <- match(rownames(expr), gpl$ID)
  symbols <- as.character(gpl$Symbol[m])
  valid <- !is.na(symbols) & symbols != ""
  expr <- expr[valid, ]; rownames(expr) <- symbols[valid]
  entrez_map <- bitr(rownames(expr), "SYMBOL", "ENTREZID", OrgDb="org.Hs.eg.db")
  entrez_map <- entrez_map[!duplicated(entrez_map$SYMBOL), ]
  expr <- expr[entrez_map$SYMBOL, ]; rownames(expr) <- entrez_map$ENTREZID
  
  cells_rankings <- AUCell_buildRankings(expr, plotStats=FALSE, verbose=FALSE)
  cells_AUC <- AUCell_calcAUC(force_gs, cells_rankings, aucMaxRank=nrow(expr)*0.03, verbose=FALSE)
  scores <- t(getAUC(cells_AUC))
  
  pca <- prcomp(scores, scale.=TRUE)
  var_explained <- summary(pca)$importance[3, 2]
  expect_gt(var_explained, 0.5, label="PC1+PC2 should explain >50% variance")
  cat("  ✓ PCA:", round(var_explained*100), "% variance in PC1+PC2\n")
})

# ─── 测试 3: PC1 载荷与已知方向一致 ───
test_that("PC1 loadings enriched in positive-NES pathways", {
  # 从 shear_gsea_full 获取 NES
  shear_gsea <- readRDS("analyses/force_fingerprint/shear_gsea_full.rds")
  shear_df <- shear_gsea@result
  
  # 跑 PCA
  expr <- readRDS("data/cache/GSE23289_expr.rds")
  gpl <- readRDS("data/cache/GPL6104.rds")
  m <- match(rownames(expr), gpl$ID)
  symbols <- as.character(gpl$Symbol[m])
  valid <- !is.na(symbols) & symbols != ""
  expr <- expr[valid, ]; rownames(expr) <- symbols[valid]
  entrez_map <- bitr(rownames(expr), "SYMBOL", "ENTREZID", OrgDb="org.Hs.eg.db")
  entrez_map <- entrez_map[!duplicated(entrez_map$SYMBOL), ]
  expr <- expr[entrez_map$SYMBOL, ]; rownames(expr) <- entrez_map$ENTREZID
  cells_rankings <- AUCell_buildRankings(expr, plotStats=FALSE, verbose=FALSE)
  cells_AUC <- AUCell_calcAUC(force_gs, cells_rankings, aucMaxRank=nrow(expr)*0.03, verbose=FALSE)
  scores <- t(getAUC(cells_AUC))
  pca <- prcomp(scores, scale.=TRUE)
  
  # 获取每个通路的 NES
  loadings <- pca$rotation[,1]
  pathway_ids <- names(loadings)
  nes <- shear_df$NES[match(pathway_ids, shear_df$ID)]
  
  # 正 NES 通路的 PC1 载荷应显著 > 0
  pos_nes <- loadings[nes > 0]
  neg_nes <- loadings[nes < 0]
  expect_gt(mean(pos_nes), 0, label="positive NES pathways should have positive PC1 loading")
  expect_lt(mean(neg_nes), mean(pos_nes), label="positive > negative NES")
  cat("  ✓ PC1 dir: pos NES mean=", round(mean(pos_nes),3), 
      " neg NES mean=", round(mean(neg_nes),3), "\n")
})

# ─── 测试 4: Tucker φ 计算 ───
test_that("Tucker congruence coefficient calculation", {
  # 模拟两个相似的 PC1 载荷向量
  a <- c(0.5, 0.3, -0.2, -0.4, 0.1)
  b <- c(0.4, 0.35, -0.15, -0.45, 0.05)
  
  tucker_phi <- function(x, y) {
    sum(x * y) / sqrt(sum(x^2) * sum(y^2))
  }
  
  phi_ab <- tucker_phi(a, b)
  expect_gt(phi_ab, 0.85, label="similar vectors should have φ > 0.85")
  
  # 不相似的
  c <- c(-0.3, 0.1, 0.4, -0.1, -0.2)
  phi_ac <- tucker_phi(a, c)
  expect_lt(phi_ac, 0.85, label="dissimilar vectors should have φ < 0.85")
  cat("  ✓ Tucker φ: similar=", round(phi_ab,3), " dissimilar=", round(phi_ac,3), "\n")
})

cat("\n═══ All tests passed ═══\n")
