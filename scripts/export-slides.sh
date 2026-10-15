#!/usr/bin/env bash
# 講師用。各回のスライド（sessionNN/slidesNN.md）をPDFにする。
#
# 初回の準備（Codespaces / devcontainer のターミナルで）:
#   sudo apt-get update && sudo apt-get install -y chromium fonts-noto-cjk
#   source /usr/local/share/nvm/nvm.sh && nvm install --lts
#   npm install --prefix .slide-tools @marp-team/marp-cli
#
# 実行: bash scripts/export-slides.sh            # 全部
#       bash scripts/export-slides.sh 03 05      # 第3回と第5回だけ
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f /usr/local/share/nvm/nvm.sh ]; then
  # shellcheck disable=SC1091
  source /usr/local/share/nvm/nvm.sh >/dev/null
fi
export CHROME_PATH="${CHROME_PATH:-/usr/bin/chromium}"
export CHROME_NO_SANDBOX="${CHROME_NO_SANDBOX:-true}"
MARP="${MARP_COMMAND:-.slide-tools/node_modules/.bin/marp}"

if [ $# -gt 0 ]; then
  sessions=("$@")
else
  sessions=(01 02 03 04 05 06 07 08)
fi

for n in "${sessions[@]}"; do
  src="session${n}/slides${n}.md"
  "$MARP" "$src" --pdf --allow-local-files -o "${src%.md}.pdf"
done
