# mcp-bio：AI 驱动的生信分析协作框架

让 aisdk Agent 和 DeepSeek TUI 通过一块黑板协作，自动跑 GEO 差异分析。

> **内外双循环**：Agent 是实干家（下载数据、跑 limma、画图），TUI 是兄长（派任务、看进度、卡住时给方向）。

## 快速开始

```bash
git clone https://github.com/YOUR_USER/mcp-bio.git
cd mcp-bio
bash setup.sh              # 一键安装 R/Python 依赖
# 编辑 .env 填入你的 API Key
```

启动 Watcher（Agent 后台进程）：

```r
# 在项目根目录下运行
source("src/rstudio_watcher.R")
```

然后打开 DeepSeek TUI，Agent 会自动等待任务。

## 使用

在 TUI 里派发一个分析任务：

```
board_init: "分析 GSE1919 的 OA vs Normal 差异表达"
```

Agent 会自动：
1. 下载 GEO 数据
2. 查看列名和分组分布（不会猜列名）
3. log2 变换 + limma 差异分析
4. 筛选 adj.P.Val < 0.05 且 |logFC| > 1 的 DEG
5. Verifier 自动校验结果
6. 遇到问题会通过 Board 求助

查看结果：

```
board_read_log       # 看实时进度
board_optimize       # 任务完成后的优化建议
r_get_variables      # 查看 R session 里的 DEG 变量
```

生成的图在 `plots/` 目录下。

## MCP 工具一览

| 工具 | 用途 |
|------|------|
| `board_init(task, context)` | 派发分析任务 |
| `board_check_help` | 查看 Agent 求助 |
| `board_respond(help_id, level, response)` | 回复 Agent 求助 |
| `board_read_log` | 查看实时进度 |
| `board_optimize` | 任务后优化建议 |
| `r_execute(code)` | 直接在 R session 跑代码 |
| `r_get_variables` | 列出 R 变量 |
| `r_check_package(pkg)` | 检查 R 包 |
| `r_plot_show(path)` | 打开图片 |
| `bio_geo_meta(gse_id)` | 查看 GEO 元数据 |
| `bio_quick_degs(gse_id, group, case, control)` | 快速 limma 分析 |
| `r_start_watcher` / `r_watcher_status` / `r_stop_watcher` | 管理 Watcher 进程 |

## 架构

```
TUI (DeepSeek) ←→ Board (JSON) ←→ Watcher (R Agent)
    ↓                                    ↓
  Socket 19886 ←──────── 同步通道 ────→ httpuv
```

- **Board**：异步协作协议。Agent 读任务、写进度、求助、汇报结果
- **Socket**：同步通道。TUI 直接跑 R 代码查看 Agent 的数据
- **Verifier**：自动校验 Agent 输出（错误率、DEG 统计、快照隔离）

## 安装依赖

### R 包

```r
install.packages(c("dotenv", "jsonlite", "ggplot2", "ggsci", "ggrepel",
                   "httpuv", "httr", "GEOquery", "limma"),
                 repos = "https://cloud.r-project.org")

# aisdk 在 r-universe
install.packages("aisdk", repos = "https://yulab-smu.r-universe.dev")
```

### Python 包

```bash
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API Key：

```bash
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
```

## 项目结构

```
src/
├── board.py            # Board 状态机 (deep module)
├── board_api.py        # Board HTTP API (薄壳路由)
├── r_bridge.py         # R socket 客户端
├── r_tools.py          # R 代码生成器
├── r_process.py        # 子进程管理
├── r_session_bridge.py # MCP 工具薄壳
├── verifier.R          # Verifier 纯函数
├── error_tracker.R     # ErrorTracker 纯函数
└── rstudio_watcher.R   # Watcher 主文件
tests/
├── test_board.py       # Board 状态机测试
├── test_r_tools.py     # R 代码合约测试
├── test_r_bridge.py    # Socket 测试
├── test_mcp_tools.py   # MCP 工具测试
├── test_verifier.R     # Verifier 测试
└── test_error_tracker.R# ErrorTracker 测试
```

## 开发原则

- **Deep Module**：窄接口，深实现。Board 6 个方法管理全部状态
- **薄壳不挟持逻辑**：board_api.py 是纯路由，参数提取在 Board 里
- **纯函数模块**：Verifier 和 ErrorTracker 零 I/O，可独立测试
- **协议版本化**：`_protocol_version: "1.0"` 写入 Board，防未来不兼容

## License

MIT
