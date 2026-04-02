#!/bin/bash
# ==========================================
#  QDII基金监控系统 - Agent 环境初始化脚本
# ==========================================
# 用途：每个 Agent 会话开始时运行，快速恢复开发环境
# 用法：bash init.sh

set -e

echo "=========================================="
echo "  QDII基金监控系统 - Agent 环境初始化"
echo "=========================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 检测 Python 命令
PYTHON_CMD=python
if command -v python3 &>/dev/null; then
  PYTHON_CMD=python3
fi

echo ""
echo "[1/6] 当前目录: $PROJECT_DIR"

echo ""
echo "[2/6] Git 状态:"
git status --short 2>/dev/null || echo "  (无 git 变更)"

echo ""
echo "[3/6] 最近 10 条 commit:"
git log --oneline -10 2>/dev/null || echo "  (无 commit 历史)"

echo ""
echo "[4/6] 功能完成进度:"
if [ -f "feature_list.json" ]; then
  TOTAL=$($PYTHON_CMD -c "import json; f=open('feature_list.json', encoding='utf-8'); d=json.load(f); print(len(d['features']))" 2>/dev/null || echo "?")
  PASSED=$($PYTHON_CMD -c "import json; f=open('feature_list.json', encoding='utf-8'); d=json.load(f); print(sum(1 for x in d['features'] if x['passes']))" 2>/dev/null || echo "0")
  echo "  总计: $TOTAL 个功能"
  echo "  已完成: $PASSED 个"
  echo "  剩余: $((TOTAL - PASSED)) 个"

  echo ""
  echo "  未完成的功能:"
  $PYTHON_CMD -c "
import json
with open('feature_list.json', encoding='utf-8') as f:
    d = json.load(f)
for feat in sorted(d['features'], key=lambda x: x['priority']):
    if not feat['passes']:
        print(f\"    [{feat['id']}] P{feat['priority']} ({feat['category']}): {feat['description']}\")
" 2>/dev/null || echo "    (解析失败)"
else
  echo "  (feature_list.json 不存在)"
fi

echo ""
echo "[5/6] Python 环境检查:"
if [ -n "$PYTHON_CMD" ]; then
  echo "  Python: $(${PYTHON_CMD} --version 2>&1)"
  if [ -f "requirements.txt" ]; then
    echo "  requirements.txt: 存在"
  fi
  echo "  Playwright: $(pip show playwright 2>/dev/null | grep Version | awk '{print $2}' || echo '未安装')"
fi

echo ""
echo "[6/6] 项目关键文件检查:"
for f in "main.py" "apps/app_factory.py" "apps/spider/fetcher.py" "apps/notify/notification_service.py" "web_ui/templates/index_new.html" "config/settings.py"; do
  if [ -f "$f" ]; then
    echo "  $f: ✓"
  else
    echo "  $f: ✗ (缺失)"
  fi
done

echo ""
echo "=========================================="
echo "  初始化完成"
echo "=========================================="
echo ""
echo "下一步操作:"
echo "  1. bash init.sh（已在上面执行）"
echo "  2. 阅读 progress.txt 了解已完成的工作"
echo "  3. 从 feature_list.json 中选择 priority 最小的未完成功能开始"
echo "  4. 完成功能后更新 feature_list.json 中的 passes: false → true"
echo "  5. git commit 提交更改 + git push"
echo "  6. 更新 progress.txt 记录本次会话的工作"
echo ""
