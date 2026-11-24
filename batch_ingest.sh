#!/bin/bash
# FGO 从者批量摄入脚本
# 用法: ./batch_ingest.sh [start_index] [count]
#   默认: 从 0 开始，处理 5 个

START=${1:-0}
COUNT=${2:-5}
WIKI="$HOME/fgo-wiki"
LIST="/tmp/fgo_servant_list.json"

# 下载列表（如果不存在）
if [ ! -f "$LIST" ]; then
    echo "下载从者列表..."
    curl -s --max-time 60 "https://api.atlasacademy.io/export/CN/basic_servant.json" -o "$LIST"
    echo "完成: $(python3 -c "import json;print(len(json.load(open('$LIST'))))") 个从者"
fi

# 提取 ID 列表
IDS=$(python3 -c "
import json
data = json.load(open('$LIST'))
ids = [s['id'] for s in data]
print(' '.join(str(i) for i in ids[$START:$START+$COUNT]))
")

TOTAL=0
FAILED=0

for id in $IDS; do
    TOTAL=$((TOTAL + 1))
    echo "[$TOTAL/$COUNT] 处理从者 ID=$id..."

    RAW="$WIKI/raw/servants/${id}.json"

    # 下载 JSON
    if ! curl -s --max-time 30 "https://api.atlasacademy.io/nice/CN/servant/${id}?lore=true" -o "$RAW.tmp" 2>/dev/null; then
        echo "  CN 失败，尝试 JP..."
        curl -s --max-time 30 "https://api.atlasacademy.io/nice/JP/servant/${id}?lore=true" -o "$RAW.tmp"
    fi

    # 验证 JSON
    if ! python3 -c "json.load(open('$RAW.tmp'))" 2>/dev/null; then
        echo "  ✗ JSON 无效，跳过"
        FAILED=$((FAILED + 1))
        rm -f "$RAW.tmp"
        continue
    fi

    mv "$RAW.tmp" "$RAW"

    # 生成 Markdown
    python3 "$WIKI/generate.py" "$id" && echo "  ✓ 完成" || {
        echo "  ✗ 生成失败"
        FAILED=$((FAILED + 1))
    }
    sleep 0.3  # 避免 API 限流
done

echo "---"
echo "处理完成: 成功 $((TOTAL - FAILED)) / 失败 $FAILED"
