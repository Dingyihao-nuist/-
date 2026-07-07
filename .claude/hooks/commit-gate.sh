#!/usr/bin/env bash
# commit-gate.sh — PreToolUse hook for git commit quality gate
# 拦截 git commit 命令，检查质量门禁 marker 文件
# 通过则放行（exit 0），不通过则阻止（exit 1）

set -euo pipefail

ARTIFACTS_DIR=".claude/artifacts"
TEST_RESULT="${ARTIFACTS_DIR}/test-result.json"
QUALITY_RESULT="${ARTIFACTS_DIR}/quality-result.json"
FRESHNESS_SECONDS=300  # 5 分钟

# ============================================================
# 解析 Hook 输入
# ============================================================
INPUT=$(cat 2>/dev/null || echo "{}")

# 提取 bash 命令
COMMAND=$(echo "$INPUT" | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except:
    print('')
" 2>/dev/null || echo "")

# ============================================================
# 判断是否为 git commit
# ============================================================
if ! echo "$COMMAND" | grep -qE '\bgit\b.*\bcommit\b'; then
    exit 0  # 非 git commit，放行
fi

# ============================================================
# 检查 marker 文件是否存在
# ============================================================
missing_files=""
for f in "$TEST_RESULT" "$QUALITY_RESULT"; do
    if [ ! -f "$f" ]; then
        missing_files="${missing_files}$(basename "$f") "
    fi
done

if [ -n "$missing_files" ]; then
    echo '{"continue": false, "stopReason": "质量门禁未通过: 缺少标记文件 '"$missing_files"'。请先运行 /gitcommit 进行质量检查。"}'
    exit 0
fi

# ============================================================
# 辅助函数：从 JSON 提取字段
# ============================================================
get_field() {
    local file="$1"
    local field="$2"
    python -c "
import json
with open('$file') as f:
    data = json.load(f)
print(data.get('$field', ''))
" 2>/dev/null || echo ""
}

# ============================================================
# 检查时效性
# ============================================================
NOW=$(date +%s)
for f in "$TEST_RESULT" "$QUALITY_RESULT"; do
    ts=$(get_field "$f" "timestamp")
    if [ -z "$ts" ]; then
        echo '{"continue": false, "stopReason": "质量门禁未通过: 标记文件缺少 timestamp 字段。请重新运行 /gitcommit。"}'
        exit 0
    fi

    # 尝试解析 ISO 8601 时间戳
    ts_epoch=$(date -d "$ts" +%s 2>/dev/null || echo "0")
    if [ "$ts_epoch" = "0" ]; then
        # date -d 可能不支持 ISO 格式，跳过时效性检查
        continue
    fi

    age=$(( NOW - ts_epoch ))
    if [ "$age" -gt "$FRESHNESS_SECONDS" ]; then
        age_min=$(( age / 60 ))
        echo "{\"continue\": false, \"stopReason\": \"质量门禁结果已过期 (${age_min}分钟前)。请重新运行 /gitcommit。\"}"
        exit 0
    fi
done

# ============================================================
# 判断 pass/fail
# ============================================================
TEST_STATUS=$(get_field "$TEST_RESULT" "status")
QUALITY_STATUS=$(get_field "$QUALITY_RESULT" "status")

if [ "$TEST_STATUS" = "pass" ] && [ "$QUALITY_STATUS" = "pass" ]; then
    echo '{"continue": true}'
    exit 0
else
    QUALITY_SCORE=$(get_field "$QUALITY_RESULT" "overall_score")
    echo "{\"continue\": false, \"stopReason\": \"质量门禁未通过 — 测试: ${TEST_STATUS:-unknown}, 质量评分: ${QUALITY_SCORE:-N/A}。请运行 /gitcommit 查看详情。\"}"
    exit 0
fi
