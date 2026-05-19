# mcp-bio: AI-Powered GEO Analysis Agent

An AI agent built with [aisdk](https://github.com/YuLab-SMU/aisdk) that autonomously runs GEO differential expression analysis, collaborating with you through a shared board via MCP protocol.

> **Dual-loop architecture**: The Agent is the worker (downloads data, runs limma, generates plots). You are the overseer (assign tasks, monitor progress, help when stuck).

## Quick Start

```bash
git clone https://github.com/zhiyuchen1101/mcp-bio.git
cd mcp-bio
bash setup.sh              # one-command install for R + Python deps
# Edit .env with your API key
```

Launch the Agent:

```r
# In the project root directory
source("src/rstudio_watcher.R")
```

Keep this window running. Assign tasks through any MCP-compatible client (DeepSeek TUI, Claude Code, Codex).

## Usage

```
board_init "Analyze GSE1919 OA vs Normal differential expression"
```

The Agent will:
1. Download GEO data
2. Inspect column names and group distributions (never guesses column names)
3. Log2-transform + limma analysis
4. Filter DEGs (adj.P.Val < 0.05, |logFC| > 1)
5. Auto-verify results with built-in Verifier
6. Request help via the Board when stuck

Monitor and assist:

```
board_read_log       # real-time progress
board_check_help     # see if Agent needs help
board_respond 1 L2 "Check columns with colnames()"   # give guidance
```

Results: plots in `plots/`, DEG data in R session variables.

## MCP Tools

| Tool | Description |
|------|-------------|
| `board_init` | Assign analysis task |
| `board_check_help` | Check pending help requests |
| `board_respond` | Respond to Agent help request |
| `board_read_log` | Read Agent execution log |
| `board_optimize` | Post-task optimization hints |
| `r_execute` | Execute R code in session |
| `r_get_variables` | List R session variables |
| `r_check_package` | Check R package installation |
| `r_plot_show` | Open plot with Preview |
| `bio_geo_meta` | Inspect GEO dataset metadata |
| `bio_quick_degs` | Quick limma DEG analysis |

## Architecture

```
You (MCP Client) ←→ Board (JSON) ←→ Watcher (R Agent)
       ↓                                  ↓
   Socket :19886 ←─── sync channel ───→ httpuv
```

- **Board**: Async collaboration protocol. Agent reads tasks, writes progress, requests help.
- **Socket**: Sync channel. Run R code directly to inspect Agent's data.
- **Verifier**: Auto-validates Agent output (error rate, DEG stats, snapshot isolation).

## Dependencies

### R
```r
install.packages(c("dotenv", "jsonlite", "ggplot2", "ggsci", "ggrepel",
                   "httpuv", "httr", "GEOquery", "limma"),
                 repos = "https://cloud.r-project.org")
install.packages("aisdk", repos = "https://yulab-smu.r-universe.dev")
```

### Python
```bash
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env`:

```bash
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.deepseek.com    # or https://api.openai.com/v1
OPENAI_MODEL=deepseek-chat                  # or gpt-4o
```

## MCP Client Setup

### DeepSeek TUI
Auto-registered when the project is open.

### Claude Code
```json
// .claude/mcp.json
{
  "mcpServers": {
    "mcp-bio": {
      "command": "python3",
      "args": ["src/r_session_bridge.py"],
      "cwd": "/path/to/mcp-bio"
    }
  }
}
```

### Codex
```toml
# .codex/config.toml
[mcp_servers.mcp-bio]
command = "python3 src/r_session_bridge.py"
```

## Design Principles

- **Deep Module**: Board manages 14 fields through 6 methods. Callers never touch JSON.
- **Thin Shell**: `board_api.py` is pure routing — 4 endpoints, one-liners.
- **Pure Functions**: Verifier and ErrorTracker are zero-I/O, independently testable.
- **Protocol Versioning**: `_protocol_version: "1.0"` in Board JSON for future compatibility.

## License

MIT
