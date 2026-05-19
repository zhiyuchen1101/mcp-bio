#!/bin/bash
# setup.sh — mcp-bio 一键安装
# 用法: bash setup.sh
# 原则: 一行命令，内部全自动。缺什么装什么，有就跳过。

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step()  { echo -e "${GREEN}═══ $1 ${NC}"; }
warn()  { echo -e "${YELLOW} ⚠  $1 ${NC}"; }
err()   { echo -e "${RED} ✗  $1 ${NC}"; }
ok()    { echo -e " ${GREEN}✓${NC} $1"; }

# ═════════════════════════════════════════
# 1. 环境检测（只做一次，不重复检查）
# ═════════════════════════════════════════
step "环境检测"

# R
R_BIN=$(which R 2>/dev/null || echo "")
if [ -z "$R_BIN" ]; then
    err "未安装 R。请先安装: brew install r (macOS) / apt install r-base (Linux)"
    exit 1
fi
ok "R: $(R --version | head -1)"

# Python
PYTHON_BIN=$(which python3 2>/dev/null || echo "")
if [ -z "$PYTHON_BIN" ]; then
    err "未安装 Python3"
    exit 1
fi
ok "Python: $(python3 --version)"

# ═════════════════════════════════════════
# 2. 代理检测
# ═════════════════════════════════════════
if curl -s --max-time 3 https://cloud.r-project.org > /dev/null 2>&1; then
    ok "网络直连正常"
elif [ -n "$https_proxy" ]; then
    ok "代理模式: $https_proxy"
else
    warn "无法访问外网。如需代理: export https_proxy=http://127.0.0.1:7897"
    warn "然后重新运行: bash setup.sh"
    exit 1
fi

# ═════════════════════════════════════════
# 3. R 包安装
# ═════════════════════════════════════════
step "R 包"

install_r_pkg() {
    local pkg=$1
    local repo=$2
    if R --slave -e "require('$pkg', quietly=TRUE)" 2>/dev/null; then
        ok "$pkg (已有)"
    else
        echo -n "  安装 $pkg ... "
        R --slave -e "install.packages('$pkg', repos='$repo', quiet=TRUE)" 2>/dev/null && ok "$pkg" || { err "$pkg 安装失败"; return 1; }
    fi
}

# CRAN 包
CRAN_REPO="https://cloud.r-project.org"
for pkg in dotenv jsonlite ggplot2 ggsci ggrepel httpuv httr GEOquery limma; do
    install_r_pkg "$pkg" "$CRAN_REPO"
done

# aisdk — 不在 CRAN，在 r-universe
install_r_pkg "aisdk" "https://yulab-smu.r-universe.dev"

# ═════════════════════════════════════════
# 4. Python 包安装
# ═════════════════════════════════════════
step "Python 包"

if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt --quiet 2>/dev/null && ok "requirements.txt" || err "pip 安装失败"
else
    warn "未找到 requirements.txt，已跳过"
fi

# ═════════════════════════════════════════
# 5. 配置文件
# ═════════════════════════════════════════
step "配置"

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        ok ".env 已创建（请编辑填入 API Key）"
    else
        cat > .env << 'EOF'
# 填入你的 DeepSeek API Key
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
EOF
        ok ".env 已创建（请编辑填入 API Key）"
    fi
else
    ok ".env 已存在，跳过"
fi

# ═════════════════════════════════════════
# 完成
# ═════════════════════════════════════════
echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  安装完成${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo "  下一步："
echo "  1. 编辑 .env 文件，填入你的 API Key"
echo "  2. 终端安装脚本已配好。你只需在 R 里跑："
echo ""
echo "     source('src/rstudio_watcher.R')"
echo ""
echo "     Agent 会在后台等待 TUI 派发任务。"
