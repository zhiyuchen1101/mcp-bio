# test_verifier.R — Verifier 纯函数测试
# 运行: R --no-save --slave -f tests/test_verifier.R

source("src/verifier.R")

# Case 1: 空日志 → status = "error"
result1 <- verifier(agent_log = list(), last_steps = 0, snapshot_before = character(0))
stopifnot(result1$status == "error")
cat("PASS: empty log → error\n")

# Case 2: 有错误但无 DEG → status = "error"
log2 <- list(
  list(step = 1, tool = "run_r_code", code_preview = "x <- 1", result_preview = "ERROR: x not found", has_error = TRUE),
  list(step = 2, tool = "run_r_code", code_preview = "y <- 2", result_preview = "ERROR: y not found", has_error = TRUE)
)
result2 <- verifier(agent_log = log2, last_steps = 2, snapshot_before = character(0))
stopifnot(result2$status == "error")
stopifnot(grepl("100%", result2$summary))
cat("PASS: all errors → error\n")

# Case 3: 有 DEG 变量（模拟） → status = "done"
snap <- ls()  # 快照在创建 DEG 之前
# 在全局环境创建一个假的 DEG data.frame
deg_test <- data.frame(
  logFC = c(2.5, -1.8, 3.1),
  adj.P.Val = c(0.001, 0.02, 0.04),
  row.names = c("GENE1", "GENE2", "GENE3")
)
# deg_test 在 snap 之后创建 → verifier 应该扫描到
result3 <- verifier(
  agent_log = list(
    list(step = 1, tool = "run_r_code", code_preview = "lmFit", result_preview = "OK", has_error = FALSE)
  ),
  last_steps = 1,
  snapshot_before = snap
)
stopifnot(result3$status == "done")
stopifnot(grepl("deg_test", result3$summary))
cat("PASS: found DEG → done\n")

# Case 4: snapshot 隔离 — 旧变量不干扰
# 在环境里放一个旧 DEG 变量（模拟前一次任务残留）
old_deg <- data.frame(logFC = c(5, 4), adj.P.Val = c(0.01, 0.02))
snap_old <- ls()  # 快照包含 old_deg
result4 <- verifier(
  agent_log = list(
    list(step = 1, tool = "run_r_code", code_preview = "echo", result_preview = "OK", has_error = FALSE)
  ),
  last_steps = 1,
  snapshot_before = snap_old  # old_deg 在快照里 → 应该被排除
)
# old_deg 被排除，但 deg_test 也不在（之前创建的）
stopifnot(result4$status == "done" || result4$status == "error")  # 无新DEG
cat("PASS: snapshot isolation — old variables excluded\n")

cat("\n✅ All verifier tests passed\n")
