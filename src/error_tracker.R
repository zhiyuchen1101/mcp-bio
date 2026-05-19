# error_tracker.R — 三个纯函数，零状态
#
# 使用方式（在 r_tool 里）：
#   cat    <- error_category(err_msg)         # "syntax"|"column"|"package"|"generic"
#   thr    <- error_threshold(cat)             # 1|2|3
#   recent <- c(recent, err_msg)               # 状态由 r_tool 维护
#   if (should_escalate(recent, thr)) { ... }  # 判断是否升级
#
# 不要：et <- create_error_tracker() —— 那是旧版有状态设计。

# ── 纯函数 1: 错误分类 ──

error_category <- function(msg) {
  if (grepl("unexpected|parse|syntax|unexpected symbol|unexpected '}'|unexpected input", msg)) {
    return("syntax")
  }
  if (grepl("undefined columns|subscript|dimensions|non-numeric", msg)) {
    return("column")
  }
  if (grepl("there is no package|could not find function|not found", msg)) {
    return("package")
  }
  "generic"
}

# ── 纯函数 2: 升级阈值 ──

error_threshold <- function(category) {
  switch(category,
    syntax  = 1,
    column  = 1,
    package = 2,
    3  # generic
  )
}

# ── 纯函数 3: 判断是否升级（基于 30-字符前缀匹配）──

should_escalate <- function(history, threshold) {
  if (length(history) == 0) return(FALSE)
  last <- history[length(history)]
  prefix <- substr(last, 1, 30)
  similar <- sum(grepl(prefix, history, fixed = TRUE))
  similar > threshold
}
