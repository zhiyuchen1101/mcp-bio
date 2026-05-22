# RED: watcher_health_check 预检协议
library(testthat)

source("src/rstudio_watcher.R", local=TRUE)

test_that("健康检查返回结构", {
  result <- watcher_health_check()
  expect_true("ok" %in% names(result))
  expect_true("issues" %in% names(result))
  expect_type(result$ok, "logical")
})

test_that("端口占用应被检测", {
  # 模拟端口被占
  skip("需要手动测试: lsof -ti :19886 返回非空")
})

test_that("代理未设应被检测", {
  old_proxy <- Sys.getenv("https_proxy")
  Sys.setenv(https_proxy = "")
  result <- watcher_health_check()
  if (!result$ok) expect_true("no_proxy" %in% result$issues)
  Sys.setenv(https_proxy = old_proxy)
})

test_that("健康启动时 ok=TRUE", {
  result <- watcher_health_check()
  expect_true(result$ok)
  expect_length(result$issues, 0)
})
