# mcp-bio: AI-Powered GEO Analysis Agent

*[中文版](#中文版) | [English](#english)*

An AI agent built with [aisdk](https://github.com/YuLab-SMU/aisdk) that autonomously runs GEO differential expression analysis, collaborating with you through a shared board via MCP protocol.

**Dual-loop architecture**: The Agent is the worker. You are the overseer.

---

## 中文版

让 aisdk Agent 通过 MCP 协议与 TUI 协作，自动跑 GEO 差异分析。

### 快速开始

```bash
git clone https://github.com/zhiyuchen1101/mcp-bio.git
cd mcp-bio
bash setup.sh              # 一键安装 R/Python 依赖
# 编辑 .env 填入 API Key
```

启动 Agent：

```r
source("src/rstudio_watcher.R")  # 项目根目录下运行
```

此窗口保持运行。在 DeepSeek TUI 里派任务。

### 使用

```
board_init: "分析 GSE1919 OA vs Normal"
board_read_log                 # 看实时进度
board_check_help               # 看 Agent 是否求助
board_respond 1 L2 "用 colnames() 查列名"  # 给指导
```

结果在 `plots/`，DEG 数据在 R session 变量里。

### 工具一览

| 工具 | 用途 |
|------|------|
| `board_init` | 派发分析任务 |
| `board_read_log` | 查看实时进度 |
| `board_check_help` | 查看 Agent 求助 |
| `board_respond` | 回复 Agent 求助 |
| `board_optimize` | 任务后优化建议 |
| `r_execute` | 直接在 R session 跑代码 |
| `r_get_variables` | 列出 R 变量 |
| `r_plot_show` | 打开图片 |
| `bio_geo_meta` | 查看 GEO 元数据 |
| `bio_quick_degs` | 快速 limma |

### 架构

```
TUI ←→ Board (JSON) ←→ Watcher (R Agent)
 ↓                        ↓
Socket :19886 ←─ 同步通道 ── httpuv
```

- **Board**: 异步协作协议
- **Socket**: 同步通道，直接跑 R 代码
- **Verifier**: 自动校验结果

### 安装依赖

**R**: `dotenv, jsonlite, ggplot2, ggsci, ggrepel, httpuv, httr, GEOquery, limma`（CRAN）+ `aisdk`（[r-universe](https://yulab-smu.r-universe.dev)）

**Python**: `pip3 install -r requirements.txt`

### 设计原则

- **Deep Module**: Board 6 方法管理 14 字段
- **薄壳不挟持**: board_api 是纯路由
- **纯函数模块**: Verifier + ErrorTracker 零 I/O
- **协议版本化**: `_protocol_version: "1.0"`

---

## English

### Quick Start

```bash
git clone https://github.com/zhiyuchen1101/mcp-bio.git
cd mcp-bio
bash setup.sh
# Edit .env with your API key
```

```r
source("src/rstudio_watcher.R")
```

Assign tasks through any MCP-compatible client.

### Usage

```
board_init "Analyze GSE1919 OA vs Normal"
board_read_log
board_check_help
board_respond 1 L2 "Check columns with colnames()"
```

Results: plots in `plots/`, DEG data in R session variables.

### MCP Client Setup

**DeepSeek TUI**: Auto-registered.  
**Claude Code**: Add to `.claude/mcp.json`.  
**Codex**: Add to `.codex/config.toml`.

### Dependencies

**R**: `dotenv, jsonlite, ggplot2, ggsci, ggrepel, httpuv, httr, GEOquery, limma` (CRAN) + `aisdk` ([r-universe](https://yulab-smu.r-universe.dev))  
**Python**: `pip3 install -r requirements.txt`

### Design Principles

- **Deep Module**: Board manages 14 fields through 6 methods
- **Thin Shell**: `board_api.py` is pure routing
- **Pure Functions**: Verifier + ErrorTracker, zero I/O
- **Protocol Versioning**: `_protocol_version: "1.0"`

## License

MIT
