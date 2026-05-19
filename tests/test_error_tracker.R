# test_error_tracker.R — ErrorTracker 纯函数测试
# 运行: R --no-save --slave -f tests/test_error_tracker.R

source("src/error_tracker.R")

# ── error_category ──
cat("── error_category ──\n")
stopifnot(error_category("ERROR: unexpected symbol") == "syntax")
stopifnot(error_category("ERROR: unexpected '}'") == "syntax")
stopifnot(error_category("ERROR: undefined columns selected") == "column")
stopifnot(error_category("ERROR: subscript out of bounds") == "column")
stopifnot(error_category("ERROR: there is no package called 'xyz'") == "package")
stopifnot(error_category("ERROR: could not find function 'foo'") == "package")
stopifnot(error_category("ERROR: something else") == "generic")
cat("PASS\n")

# ── error_threshold ──
cat("── error_threshold ──\n")
stopifnot(error_threshold("syntax") == 1)
stopifnot(error_threshold("column") == 1)
stopifnot(error_threshold("package") == 2)
stopifnot(error_threshold("generic") == 3)
cat("PASS\n")

# ── should_escalate ──
cat("── should_escalate ──\n")

# 语法错误：第 2 次升级
h1 <- c("ERROR: unexpected symbol")
stopifnot(!should_escalate(h1, 1))
h1b <- c("ERROR: unexpected symbol", "ERROR: unexpected symbol")
stopifnot(should_escalate(h1b, 1))
cat("  syntax: 2nd triggers ✓\n")

# 列错误：第 2 次升级
h2 <- c("ERROR: undefined columns selected", "ERROR: undefined columns selected")
stopifnot(should_escalate(h2, 1))
cat("  column: 2nd triggers ✓\n")

# 泛型错误：第 4 次升级（同一前缀）
h3 <- c("ERROR: something wrong", "ERROR: something wrong", "ERROR: something wrong")
stopifnot(!should_escalate(h3, 3))
h3b <- c("ERROR: something wrong", "ERROR: something wrong", "ERROR: something wrong", "ERROR: something wrong")
stopifnot(should_escalate(h3b, 3))
cat("  generic: 4th triggers ✓\n")

# 不同前缀的错误不累积
h4 <- c("ERROR: foo failed", "ERROR: bar failed")
stopifnot(!should_escalate(h4, 1))
cat("  different errors: no false escalation ✓\n")

cat("\n✅ All pure-function tests passed\n")
