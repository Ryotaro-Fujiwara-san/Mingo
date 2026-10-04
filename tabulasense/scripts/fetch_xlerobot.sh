#!/usr/bin/env bash
# XLeRobot の MuJoCo モデル（simulation/mujoco）だけを sparse checkout で取得する。
# 再現性のためコミットを固定している。更新するときは XLEROBOT_REF を書き換える。
set -euo pipefail

XLEROBOT_REPO="${XLEROBOT_REPO:-https://github.com/Vector-Wangel/XLeRobot.git}"
XLEROBOT_REF="${XLEROBOT_REF:-749abc837d5d771f26aeff961009c290e574b024}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/third_party/XLeRobot"

if [ ! -d "$DEST/.git" ]; then
  git clone --filter=blob:none --no-checkout "$XLEROBOT_REPO" "$DEST"
  git -C "$DEST" sparse-checkout set simulation/mujoco
fi
git -C "$DEST" fetch --depth 1 origin "$XLEROBOT_REF"
git -C "$DEST" checkout --quiet FETCH_HEAD

echo "XLeRobot MuJoCo model: $DEST/simulation/mujoco/xlerobot.xml"
