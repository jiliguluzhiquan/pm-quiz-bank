#!/bin/zsh
set -eu
DIR="$(cd "$(dirname "$0")" && pwd)"
/usr/local/bin/python3 "$DIR/source/configure_ai.py" || true
echo ""
read "reply?按回车关闭配置窗口… "
