#!/bin/zsh
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "正在启动中南知了本地AI刷题系统..."
echo "如需关闭，请在此终端按 Control+C。"
exec /usr/local/bin/python3 "$DIR/本地AI评分服务.py" --open
