#!/bin/bash
# 旅行规划 MCP 工具安装脚本
# 运行前请先填写下方的 API Key

set -e

# ─────────────────────────────
# 1. 安装 uv（Python包管理器）
# ─────────────────────────────
echo ">>> 安装 uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zprofile 2>/dev/null || source ~/.zshrc 2>/dev/null || true
export PATH="$HOME/.cargo/bin:$PATH"

# ─────────────────────────────
# 2. 安装 xhs-mcp
# ─────────────────────────────
echo ">>> 安装 xhs-mcp..."
# 方案A：从PyPI安装（推荐）
uv tool install xhs-mcp

# 如果上面失败，用方案B：
# pip3 install xhs-mcp

echo ""
echo "✅ xhs-mcp 安装完成"
echo ""
echo "⚠️  接下来需要配置小红书Cookie："
echo "   1. 浏览器打开 xiaohongshu.com 并登录"
echo "   2. F12 → Network → 刷新页面"
echo "   3. 找到任意请求 → Headers → 复制 Cookie 字段值"
echo "   4. 将Cookie填入 mcp_config.json 的 XHS_COOKIE 处"
echo ""
