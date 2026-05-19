# RStudio Watcher — 文件黑板轮询 + aisdk agent 执行
# 用法: source("src/rstudio_watcher.R")  (项目根目录下)
#
# Board 合法状态值（与 board.py 常量同步）：
#   "idle"        — 无任务
#   "working"     — Agent 执行中 / 新任务
#   "blocked"     — 求助升级，等待 TUI 回复
#   "discussing"  — Agent 发起讨论，等待 TUI
#   "verifying"   — Worker 完成，Verifier 检查中
#   "done"        — 分析完成
#   "error"       — 分析失败

library(aisdk)
library(dotenv)
library(jsonlite)
library(ggplot2)
library(ggsci)
library(ggrepel)
library(httpuv)
library(httr)

# ── 项目根目录 ──
PROJECT_DIR <- Sys.getenv("MCP_PROJECT_DIR", unset = getwd())

# ── 拆出的独立模块 ──
source(file.path(PROJECT_DIR, "src/verifier.R"))
source(file.path(PROJECT_DIR, "src/error_tracker.R"))

# Board HTTP helpers — Watcher 通过 Board API 写黑板
board_post <- function(endpoint, body) {
    httr::POST(paste0("http://localhost:19890", endpoint), body = body, encode = "json")
}

load_dot_env(file.path(PROJECT_DIR, ".env"))

BOARD <- file.path(PROJECT_DIR, "task_board.json")

# ── 初始化 aisdk ──
provider <- create_openai(
  base_url = Sys.getenv("OPENAI_BASE_URL"),
  api_key  = Sys.getenv("OPENAI_API_KEY")
)
model <- provider$language_model(Sys.getenv("OPENAI_MODEL"))

# ── Tools ──
# recent_errors 状态由 r_tool 维护，error_tracker.R 提供纯函数判断
recent_errors <- character(0)

r_tool <- tool(
  name = "run_r_code",
  description = "Execute R code in the current RStudio session. Returns output. Auto-escalates to human overseer if same error repeats 3+ times.",
  execute = function(code) {
    out <- tryCatch(
      capture.output(eval(parse(text = code), envir = .GlobalEnv), type = "output"),
      error = function(e) paste("ERROR:", e$message)
    )
    result_str <- paste(out, collapse = "\n")
    
    # Auto-escalation: track error patterns
    err_msg <- if (grepl("ERROR:", result_str)) sub("ERROR: ", "", result_str) else ""
    
    if (nchar(err_msg) > 0) {
      # 维护错误历史（状态在 r_tool，纯函数在 error_tracker.R）
      recent_errors <<- c(recent_errors, err_msg)
      if (length(recent_errors) > 5)
        recent_errors <<- tail(recent_errors, 5)
      
      cat <- error_category(err_msg)
      thr <- error_threshold(cat)
      
      if (should_escalate(recent_errors, thr)) {
        # Auto-escalate to L2
        similar_count <- sum(grepl(substr(err_msg, 1, 30), recent_errors, fixed = TRUE))
        b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
        req <- list(
          id = length(b$help_requests) + 1L, level = "L2",
          question = paste("Repeated error (", similar_count, "x): ", err_msg, 
                          ". Should I try a different approach or can you help?", sep=""),
          status = "pending", timestamp = as.character(Sys.time())
        )
        b$help_requests <- c(b$help_requests, list(req))
        b$status <- "blocked"
        b$agent_log <- c(b$agent_log, list(list(
          step = length(b$agent_log) + 1L, tool = "auto_escalate",
          code_preview = "AUTO-ESCALATION",
          result_preview = paste("Repeated error", similar_count, "times:", substr(err_msg,1,100)),
          has_error = TRUE, timestamp = as.character(Sys.time())
        )))
        board_post("/board/update", b)
        
        result_str <- paste(result_str, 
          "\n\n[AUTO-ESCALATED to L2] This error occurred", similar_count, "times.",
          "\nHuman overseer notified. PAUSED - waiting for response.")
      }
    } else {
      # Success resets the counter
      recent_errors <<- character(0)
      
      # Log success to board
      tryCatch({
        b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
        b$agent_log <- c(b$agent_log, list(list(
          step = length(b$agent_log) + 1L,
          tool = "run_r_code",
          code_preview = substr(code, 1, 120),
          result_preview = substr(result_str, 1, 200),
          has_error = FALSE,
          timestamp = as.character(Sys.time())
        )))
        if (length(b$agent_log) > 50) b$agent_log <- tail(b$agent_log, 50)
        board_post("/board/update", b)
      }, error = function(e) NULL)
    }
    
    result_str
  }
)

board_tool <- tool(
  name = "read_task_board",
  description = "Read shared task board for context",
  execute = function() {
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    paste(capture.output(str(b)), collapse = "\n")
  }
)

help_L1 <- tool(
  name = "request_help_L1",
  description = "Request INFO from overseer. PAUSE after calling.",
  execute = function(question) {
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    req <- list(
      id = length(b$help_requests) + 1L, level = "L1",
      question = question, status = "pending",
      timestamp = as.character(Sys.time())
    )
    b$help_requests <- c(b$help_requests, list(req))
    b$status <- "blocked"
    board_post("/board/update", b)
    paste("L1 sent:", question, "\n[PAUSED]")
  }
)

help_L2 <- tool(
  name = "request_help_L2",
  description = "Request HEURISTIC guidance from overseer. PAUSE after.",
  execute = function(question, state) {
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    req <- list(
      id = length(b$help_requests) + 1L, level = "L2",
      question = question, context_snapshot = state,
      status = "pending", timestamp = as.character(Sys.time())
    )
    b$help_requests <- c(b$help_requests, list(req))
    b$status <- "blocked"
    board_post("/board/update", b)
    paste("L2 sent:", question, "\n[PAUSED]")
  }
)

FORMAT_RULES <- "

## 输出格式要求（重要）
- 每个主要步骤分两步：先 announce_step 说明要做什么 → 执行 → 再 announce_step(is_result=TRUE) 用 1-2 行中文总结结果
- 代码中的 cat() 输出要精简：只打印关键数字和结论，不要打印整个矩阵
- 包加载使用 suppressPackageStartupMessages(library(...))
- 不要打印整个 data.frame 或大向量，用 head() 或 [1:5] 截断

## 输出规则
- 每一步先用中文说明「我要做什么」
- 代码执行后，用中文解读关键结果
- 画图完成后，说明图的含义
- 最终用中文总结分析结果

## 环境
- RStudio Console 会实时显示你的代码和输出
- Plots 窗格自动渲染图形
- 用户可以随时在 Console 看到你的进度并介入"

COLLAB_PROMPT <- paste0(
  "你是运行在 RStudio 中的 R 生信分析助手。用户（TUI）通过 task_board.json 给你派发任务。\n\n",
  "## 数据预处理（重要）\n",
  "- 表达矩阵下载后先检查尺度：如果数值范围在百/千级别（非 log 尺度），用 `exprs <- log2(exprs + 1)` 做 log2 变换\n",
  "- limma 假设数据近似正态分布，非 log 数据会导致 logFC 异常大、假阳性\n\n",
  "## 输出要求（每次差异分析必做）\n",
  "- 差异分析完成后，自动画火山图并 ggsave 到 plots/ 目录\n",
  "- 差异分析完成后，自动画 top50 热图并 ggsave 到 plots/ 目录\n",
  "- 将 DEG 表格保存为 CSV 到项目根目录\n\n",
  "## 工作流程\n",
  "1. 首先调用 read_task_board 加载上下文（文件路径、列名、参数）\n",
  "2. **遇到新数据集时，先用 colnames(pData(eset)) 查看所有表型列名，再用 table() 查看每列分组分布，确认可用的对比组后再继续。绝不要猜测列名。**\n",
  "3. 调用 announce_step 宣布你要做什么（中文描述）\n",
  "4. 调用 run_r_code 执行 R 代码\n",
  "5. 遇到错误自己调试，但**同一错误消息出现 2 次后必须换思路**（同一代码产生同一错误 = 同一方法），不要重试相同代码。\n",
  "6. 需要确认细节时用 discuss_with_TUI 提问，然后等待回复\n",
  "7. 绝不要猜测列名或文件路径 —— 用 request_help 求助\n",
  FORMAT_RULES
)


announce_tool <- tool(
  name = "announce_step",
  description = "用中文宣布当前步骤和结果摘要，在执行代码前/后调用",
  execute = function(step_name, detail = "", is_result = FALSE) {
    if (is_result) {
      cat("  [OK] ", step_name, "\n", sep = "")
    } else {
      cat("\n--- ", step_name, " ---\n", sep = "")
    }
    if (nchar(detail) > 0) cat("     ", detail, "\n", sep = "")
    paste("步骤宣布:", step_name)
  }
)

discuss_tool <- tool(
  name = "discuss_with_TUI",
  description = "Discuss analysis direction with TUI in Chinese",
  execute = function(question, options = "") {
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    msg <- list(from = "aisdk", to = "TUI", question = question, options = options, timestamp = as.character(Sys.time()))
    b$discussion <- c(b$discussion, list(msg))
    b$status <- "discussing"
    board_post("/board/update", b)
    paste("Asked TUI:", question, "\n[waiting...]")
  }
)

agent <- create_agent(
  name = "RStudio_Agent",
  description = "运行在 RStudio 中的 R 生信分析助手，中文交互",
  system_prompt = COLLAB_PROMPT,
  model = model,
  tools = list(r_tool, board_tool, help_L1, help_L2, announce_tool, discuss_tool)
)

# ── Log helper ──
log_step <- function(step_num, tool_name, code_snip, result_snip, has_err) {
  tryCatch({
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    b$agent_log <- c(b$agent_log, list(list(
      step = step_num, tool = tool_name,
      code_preview = substr(code_snip, 1, 120),
      result_preview = substr(result_snip, 1, 200),
      has_error = has_err,
      timestamp = as.character(Sys.time())
    )))
    if (length(b$agent_log) > 50) b$agent_log <- tail(b$agent_log, 50)
    board_post("/board/update", b)
  }, error = function(e) NULL)
}

# ════════════════════════════════════════════
# 主循环
# ════════════════════════════════════════════

cat("\n🔍 RStudio Watcher 已启动\n")
cat("   监听黑板: ", BOARD, "\n")
cat("   按 ESC 或 Ctrl+C 停止\n")
cat("   等待 TUI 派发任务...\n\n")
# 启动 R socket 服务器（供 Bridge 连接，共享同一个 R Session）
tryCatch({
  httpuv::startServer("127.0.0.1", 19886, list(
    call = function(req) {
        body <- req$rook.input$read()
        req_json <- jsonlite::fromJSON(rawToChar(body))
        code <- req_json$code
        result <- tryCatch(
            capture.output(eval(parse(text=code), envir=.GlobalEnv)),
            error = function(e) paste("ERROR:", e$message)
        )
        list(status=200L, headers=list("Content-Type"="application/json"),
             body=jsonlite::toJSON(list(output=paste(result,collapse="\n")), auto_unbox=TRUE))
    }
  ))
  cat("   R socket server: http://localhost:19886\n")
}, error = function(e) {
  cat("   R socket server FAILED:", e$message, "\n")
})

last_task_id <- ""

while (TRUE) {
  httpuv::service(100)
  Sys.sleep(2)
  
  ok <- tryCatch({
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    
    # 只处理 TUI 新发的任务 (status = working, 新 task)
    task_id <- paste(b$current_task, b$session_id)
    if (b$status != "working" || task_id == last_task_id) next

    # 检查执行锁
    if (!is.null(b$agent_status) && b$agent_status == "running") {
      cat("[LOCKED] Agent 正在执行中，跳过
")
      next
    }
    b$agent_status <- "running"
    board_post("/board/update", b)
    
    # ═══ 新任务！═══
    last_task_id <<- task_id
    cat("\n═══════════════════════════════════\n")
    cat("[TUI]:", b$current_task, "\n")
    if (length(b$discussion) > 0) {
      last_disc <- b$discussion[[length(b$discussion)]]
      if (last_disc$from == "TUI") {
        cat("\n>>> TUI 回复:", last_disc$response, "\n")
      }
    }
    cat("═══════════════════════════════════\n\n")
    
    # 执行前记录变量快照（供 Verifier 隔离扫描）
    snap_before <- ls(envir = .GlobalEnv)
    
    # 执行
    # 抑制包加载噪音
    suppressPackageStartupMessages({
      result <- agent$run(b$current_task, max_steps = 30)
    })
    
    # Auto-retry: check for TUI responses (help or discussion)
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    retry_task <- NULL
    if (b$status == "blocked" && length(b$help_responses) > 0) {
      last_resp <- b$help_responses[[length(b$help_responses)]]
      cat("\n>>> TUI 回复求助: ", last_resp$response, "\n")
      retry_task <- paste(b$current_task, "。TUI 提示:", last_resp$response)
    } else if (b$status == "discussing" && length(b$discussion) > 1) {
      last_disc <- b$discussion[[length(b$discussion)]]
      if (!is.null(last_disc$from) && last_disc$from == "TUI") {
        cat("\n>>> TUI 回复讨论: ", last_disc$response, "\n")
        retry_task <- paste(b$current_task, "。TUI 回复:", last_disc$response)
      }
    }
    if (!is.null(retry_task)) {
      b$status <- "working"
      board_post("/board/update", b)
      cat("\n[RETRY] 用 TUI 指导重试...\n")
      suppressPackageStartupMessages({
        result <- agent$run(retry_task, max_steps = 8)
      })
    }
    
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    b$last_result <- result$text
    b$last_steps <- result$steps
    b$status <- "verifying"  # → Verifier
    b$worker_result <- list(steps = result$steps, text = result$text)
    board_post("/board/update", b)
    
    cat("\n[OK] Worker 完成 (", result$steps, "步)\n", sep = "")
    cat(result$text, "\n\n")
    
    
    # ═══════════════════════════════════════
    # Verifier — 独立模块 verifier.R
    # ═══════════════════════════════════════
    b <- jsonlite::fromJSON(BOARD, simplifyVector = FALSE)
    verdict <- verifier(b$agent_log, result$steps, snap_before)
    b$verifier_summary <- verdict$summary
    b$status <- verdict$status
    b$agent_status <- "idle"

    cat("  [Verifier] ", verdict$summary, "\n")
    board_post("/board/update", b)
    
    # Leader Auto-Fix removed
    # Leader Auto-Fix removed
    
  }, error = function(e) {
    cat("⚠️  Watcher error:", e$message, "\n")
  })
}
