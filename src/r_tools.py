"""
R 分析工具 — 纯 R 代码生成器

生成可在 Watcher R session 中执行的 R 代码字符串。
不依赖 MCP、不依赖 FastMCP、纯字符串拼接。
"""


def get_variables_r() -> str:
    """生成列出所有 R 变量的代码"""
    return r"""
for (v in ls(all.names=TRUE)) {
  val <- get(v, envir=.GlobalEnv)
  cat(v, ":", class(val)[1])
  if (is.vector(val) || is.factor(val)) cat(" [len=", length(val), "]", sep="")
  if (is.data.frame(val)) cat(" [", nrow(val), "x", ncol(val), "]", sep="")
  cat("\n")
}
"""


def geo_meta_r(gse_id: str) -> str:
    """生成获取 GEO 数据集元数据的 R 代码，含列名和分组分布"""
    return f"""
library(GEOquery)
gse <- getGEO("{gse_id}", GSEMatrix=TRUE, getGPL=FALSE)
eset <- gse[[1]]
cat("Series:", "{gse_id}\\n")
cat("Samples:", ncol(exprs(eset)), "\\n")
cat("Probes:", nrow(exprs(eset)), "\\n")
pd <- pData(eset)
cat("Phenotype columns:\\n")
for (cn in colnames(pd)) {{
  vals <- unique(pd[[cn]])
  if (length(vals) <= 20) {{
    cat("  ", cn, ": ", paste(head(vals, 10), collapse=", "), "\\n", sep="")
    cat("    (table: ", paste(names(table(vals)), collapse=", "), ")\\n", sep="")
  }} else {{
    cat("  ", cn, ": [", length(vals), " unique values]\\n", sep="")
  }}
}}
"""


def auto_degs_r(gse_id: str, case: str = "", control: str = "") -> str:
    """一键 DEG：自动探测分组列并跑 limma。case/control 可为空（Agent 自行判断）。"""
    return f"""
suppressPackageStartupMessages({{library(GEOquery); library(limma)}})
eset <- getGEO("{gse_id}", GSEMatrix=TRUE, getGPL=FALSE)[[1]]
expr <- exprs(eset); pd <- pData(eset)
cat("Samples:", ncol(expr), "\\n")

# 自动找分组列
target_col <- NULL; case_val <- NULL; ctrl_val <- NULL
""" + (f"""
for(cn in colnames(pd)) {{
  vals <- as.character(pd[[cn]])
  if(any(grepl("{case}", vals, ignore.case=TRUE)) && any(grepl("{control}", vals, ignore.case=TRUE))) {{
    target_col <- cn; case_val <- grep("{case}", unique(vals), value=TRUE, ignore.case=TRUE)[1]
    ctrl_val <- grep("{control}", unique(vals), value=TRUE, ignore.case=TRUE)[1]
    break
  }}
}}
""" if case else """
for(cn in colnames(pd)) {{
  uv <- unique(as.character(pd[[cn]])); if(length(uv)==2) {{target_col<-cn; case_val<-uv[1]; ctrl_val<-uv[2]; break}}
}}
""") + f"""
if(is.null(target_col)) stop("Cannot auto-detect group column")
cat("Auto-detected:", target_col, "(", case_val, "vs", ctrl_val, ")\\n")

group <- factor(pd[[target_col]], levels=c(ctrl_val, case_val))
design <- model.matrix(~group); fit <- lmFit(expr, design); fit <- eBayes(fit)
tt <- topTable(fit, coef=2, number=Inf, adjust.method="BH")
cat("Sig adjP<0.05:", sum(tt$adj.P.Val<0.05), "\\n")
cat("Sig+|logFC|>1:", sum(tt$adj.P.Val<0.05 & abs(tt$logFC)>1),
    "(up:", sum(tt$adj.P.Val<0.05 & tt$logFC>1),
    "down:", sum(tt$adj.P.Val<0.05 & tt$logFC< -1), ")\\n")
assign("last_degs", tt, envir=.GlobalEnv)
assign("last_gse_id", "{gse_id}", envir=.GlobalEnv)
cat("Saved to last_degs\\n")
"""


def quick_degs_r(gse_id: str, group_col: str, case: str, control: str) -> str:
    """生成 limma 差异表达分析的 R 代码"""
    return f"""
library(GEOquery)
library(limma)

gse <- getGEO("{gse_id}", GSEMatrix=TRUE, getGPL=FALSE)
eset <- gse[[1]]
exprs_mat <- exprs(eset)

# 构建分组
groups <- factor(pData(eset)[, "{group_col}"])
design <- model.matrix(~ 0 + groups)
colnames(design) <- levels(groups)

# limma
fit <- lmFit(exprs_mat, design)
contrast <- makeContrasts({case} - {control}, levels=design)
fit2 <- contrasts.fit(fit, contrast)
fit2 <- eBayes(fit2)

degs <- topTable(fit2, number=Inf, adjust.method="BH")
up <- sum(degs$adj.P.Val < 0.05 & degs$logFC > 1)
down <- sum(degs$adj.P.Val < 0.05 & degs$logFC < -1)

cat("{case} vs {control}:\\n")
cat("  Up-regulated (adj.P<0.05, logFC>1):", up, "\\n")
cat("  Down-regulated (adj.P<0.05, logFC<-1):", down, "\\n")
cat("\\n  Top 10 up:\\n")
up_genes <- head(rownames(degs)[degs$adj.P.Val < 0.05 & degs$logFC > 1], 10)
cat(paste(up_genes, collapse=", "), "\\n")

# 存到 session 变量
assign("last_degs", degs, envir=.GlobalEnv)
assign("last_gse_id", "{gse_id}", envir=.GlobalEnv)
cat("\\nResults saved to 'last_degs' variable\\n")
"""


def gsea_r(gene_set: str = "KEGG") -> str:
    """GSEA 基因集富集分析——全基因排序，不卡阈值。使用 session 中的 last_degs。"""
    return f"""
suppressPackageStartupMessages({{
  library(clusterProfiler)
  library(org.Hs.eg.db)
  library(enrichplot)
}})

# 取 last_degs
degs <- NULL
for(vn in ls(envir=.GlobalEnv)) {{
  obj <- get(vn, envir=.GlobalEnv)
  if(is.data.frame(obj) && "logFC" %in% colnames(obj) && "adj.P.Val" %in% colnames(obj)) {{
    degs <- obj; cat("Using:", vn, "(", nrow(degs), "rows)\\n"); break
  }}
}}
if(is.null(degs)) stop("No DEG found. Run limma first.")

# 全基因排序（不卡阈值！）
ranked <- degs$logFC
names(ranked) <- rownames(degs)
ranked <- sort(ranked, decreasing=TRUE)
cat("Ranked genes:", length(ranked), "range:", round(range(ranked),2), "\\n")

# 基因 ID 转换（自动适配 Affymetrix / Illumina / SYMBOL）
probes <- names(ranked)
entrez <- suppressMessages(tryCatch(
  bitr(probes, fromType="SYMBOL", toType="ENTREZID", OrgDb="org.Hs.eg.db"),
  error=function(e) NULL
))
if(is.null(entrez) || (is.data.frame(entrez) && nrow(entrez) < 100)) {{
  cat("Probe IDs detected, fetching platform annotation...\\n")
  gse_id <- if(exists("last_gse_id", envir=.GlobalEnv)) get("last_gse_id", envir=.GlobalEnv) else NULL
  if(!is.null(gse_id)) {{
    eset <- getGEO(gse_id, GSEMatrix=TRUE, getGPL=FALSE)[[1]]
    gpl_id <- eset@annotation
    gpl <- getGEO(gpl_id, destdir=tempdir())
    gpl_table <- Table(gpl)
    sym_col <- grep("symbol|gene|ILMN_Gene", colnames(gpl_table), ignore.case=TRUE, value=TRUE)[1]
    if(!is.null(sym_col)) {{
      mapped <- gpl_table[match(probes, gpl_table$ID), ]
      symbols <- as.character(mapped[[sym_col]])
      names(symbols) <- as.character(probes)
      symbols <- symbols[!is.na(symbols) & symbols != ""]
      cat("Mapped", length(symbols), "probes to symbols\\n")
      entrez <- suppressMessages(bitr(symbols, fromType="SYMBOL", toType="ENTREZID", OrgDb="org.Hs.eg.db"))
    }}
  }}
}}
if(is.data.frame(entrez) && nrow(entrez) > 0) {{
  # 取每个 SYMBOL 的第一个 ENTREZID（去重）
  entrez <- entrez[!duplicated(entrez$SYMBOL), ]
  rn <- ranked[entrez$SYMBOL]
  names(rn) <- entrez$ENTREZID
  cat("Mapped to ENTREZ:", length(rn), "genes\\n")

  # GSEA
  set.seed(42)
  result <- gseKEGG(rn, organism="hsa", pvalueCutoff=0.25, minGSSize=10, maxGSSize=500)
  if(nrow(result) > 0) {{
    cat("\\n=== Top 20 GSEA KEGG Pathways ===\\n")
    res_df <- result@result
    res_df <- res_df[order(res_df$p.adjust), ]
    print(head(res_df[,c("Description","NES","p.adjust","qvalue")], 20))
  }} else {{
    cat("No pathways enriched (p<0.25)\\n")
  }}
  assign("last_gsea", result, envir=.GlobalEnv)
  cat("\\nSaved to last_gsea\\n")
}} else {{
  cat("No ENTREZ mapping found. Check probe ID format.\\n")
}}
"""


def kegg_enrich_r() -> str:
    """对当前 session 中的 DEG 结果做 KEGG/GO 富集分析"""
    return """
suppressPackageStartupMessages({
  library(clusterProfiler)
  library(org.Hs.eg.db)
})

# 取最近的 DEG 结果
degs <- NULL
for(vn in ls(envir=.GlobalEnv)) {
  obj <- get(vn, envir=.GlobalEnv)
  if(is.data.frame(obj) && "logFC" %in% colnames(obj) && "adj.P.Val" %in% colnames(obj)) {
    degs <- obj
    cat("Using DEGs from:", vn, "(", nrow(degs), "rows)\\n")
    break
  }
}
if(is.null(degs)) stop("No DEG data found in session. Run limma first.")

# 筛选 |logFC|>1
if("P.Value" %in% colnames(degs)) {
  degs_filt <- degs[degs$adj.P.Val < 0.05 & abs(degs$logFC) > 1, ]
} else {
  degs_filt <- degs
}
cat("Filtered DEGs:", nrow(degs_filt), "(up:", sum(degs_filt$logFC>1), "down:", sum(degs_filt$logFC< -1), ")\\n")

# 基因ID转换（尝试 SYMBOL → ENTREZID）
probes <- rownames(degs_filt)
entrez <- suppressMessages(bitr(probes, fromType="SYMBOL", toType="ENTREZID", OrgDb="org.Hs.eg.db"))
if(nrow(entrez) == 0) {
  # 尝试获取平台注释
  cat("Probe IDs detected, fetching platform annotation...\\n")
  gse_id <- if(exists("last_gse_id")) get("last_gse_id") else NULL
  if(!is.null(gse_id)) {
    eset <- getGEO(gse_id, GSEMatrix=TRUE, getGPL=FALSE)[[1]]
    gpl_id <- eset@annotation
    gpl <- getGEO(gpl_id, destdir=tempdir())
    gpl_table <- Table(gpl)
    symbol_col <- grep("symbol|gene", colnames(gpl_table), ignore.case=TRUE, value=TRUE)[1]
    if(!is.null(symbol_col)) {
      mapped <- gpl_table[gpl_table$ID %in% probes, ]
      symbols <- unique(mapped[[symbol_col]])
      symbols <- symbols[!is.na(symbols) & symbols != ""]
      entrez <- suppressMessages(bitr(symbols, fromType="SYMBOL", toType="ENTREZID", OrgDb="org.Hs.eg.db"))
    }
  }
}
cat("Entrez IDs:", nrow(entrez), "\\n\\n")

# KEGG
cat("=== KEGG Enrichment ===\\n")
kk <- enrichKEGG(entrez$ENTREZID, organism="hsa", pvalueCutoff=0.05)
cat(nrow(kk), "pathways enriched\\n\\n")
if(nrow(kk) > 0) print(head(kk@result[,c("Description","p.adjust","Count")], 20))

# GO
cat("\\n=== GO BP (top 10) ===\\n")
go_bp <- enrichGO(entrez$ENTREZID, OrgDb="org.Hs.eg.db", ont="BP", pvalueCutoff=0.05)
if(nrow(go_bp) > 0) print(head(go_bp@result[,c("Description","p.adjust","Count")], 10))

cat("\\nResults saved to: last_kegg, last_go\\n")
assign("last_kegg", kk, envir=.GlobalEnv)
assign("last_go", go_bp, envir=.GlobalEnv)
"""