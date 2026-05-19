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
