# verifier.R — Verifier 纯函数
# 
# 输入: agent_log (list), last_steps (int), snapshot_before (character vector)
# 输出: list(summary = "...", status = "done"|"error")
#
# snapshot_before 用于隔离变量扫描：只检查 Agent 执行后新创建的变量。
# 主循环在 agent$run() 前记录 ls()，传给 verifier。

verifier <- function(agent_log, last_steps, snapshot_before = character(0)) {
  summary_parts <- c()

  # ── 错误分析 ──
  if (length(agent_log) > 0) {
    errors <- Filter(function(e) isTRUE(e$has_error), agent_log)
    total <- length(agent_log)
    err_n <- length(errors)
    err_rate <- round(100 * err_n / max(total, 1))
    summary_parts <- c(summary_parts, sprintf("步骤 %d | 错误 %d (%d%%)", total, err_n, err_rate))

    if (err_n > 0) {
      err_msgs <- sapply(errors, function(e) substr(e$result_preview, 1, 60))
      err_freq <- table(err_msgs)
      top_err <- names(sort(err_freq, decreasing = TRUE))[1]
      summary_parts <- c(summary_parts, sprintf("重复错误: %s (%dx)", top_err, err_freq[top_err]))
    }

    code_snippets <- sapply(agent_log, function(e) e$code_preview)
    has_analysis <- any(grepl("lmFit|prcomp|getGEO|DESeq|limma|enrich", code_snippets))
    if (!has_analysis) {
      summary_parts <- c(summary_parts, "无分析方法执行记录")
    }
  }

  # ── 步数检测 ──
  if (length(agent_log) >= 30 || (!is.null(last_steps) && last_steps >= 30)) {
    summary_parts <- c(summary_parts, "步数用满(>=12) — 可能未完成")
  }

  # ── DEG 变量扫描（仅扫描 snapshot 后的新变量）──
  stats <- c()
  tryCatch({
    all_vars <- ls(envir = .GlobalEnv)
    # 只检查 Agent 执行后新创建的变量
    if (length(snapshot_before) > 0) {
      new_vars <- setdiff(all_vars, snapshot_before)
    } else {
      new_vars <- all_vars  # 兼容无快照的调用
    }
    for (vname in new_vars) {
      obj <- get(vname, envir = .GlobalEnv)
      if (!is.data.frame(obj)) next
      cn <- colnames(obj)
      if (!("logFC" %in% cn && "adj.P.Val" %in% cn)) next
      sig <- obj[obj$adj.P.Val < 0.05, ]
      if (nrow(sig) == 0) next
      stats <- c(stats, sprintf("差异基因(%s): %d up / %d down / %d total sig",
        vname, sum(sig$logFC > 0), sum(sig$logFC < 0), nrow(sig)))
      stats <- c(stats, sprintf("logFC 范围: [%.2f, %.2f]",
        min(sig$logFC), max(sig$logFC)))
      break  # 只取第一个匹配的 DEG 结果
    }
  }, error = function(e) NULL)

  if (length(stats) > 0) {
    summary_parts <- c(summary_parts, paste(stats, collapse = "; "))
  }

  # ── 状态判定 ──
  summary <- paste(summary_parts, collapse = "; ")
  has_deg <- length(stats) > 0

  if (has_deg) {
    status <- "done"
  } else if (length(agent_log) == 0 || all(sapply(agent_log, function(e) isTRUE(e$has_error)))) {
    status <- "error"
  } else {
    status <- "done"
  }

  list(summary = summary, status = status, deg_stats = stats)
}
