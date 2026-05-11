#!/usr/bin/env bash
# ────────────────────────────────────────────────────
# 法律知识库 Agent 演示脚本
# ────────────────────────────────────────────────────
# 用法: bash demo.sh
# 依赖: curl, python3, jq (可选)
# ────────────────────────────────────────────────────

BASE="http://localhost:8888/api/v1"
TOKEN=""

echo "╔═══════════════════════════════════════════════╗"
echo "║   法律咨询 Agent 系统演示                      ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

# ── 1. 登录 ──────────────────────────────────────────
echo "━━━ 1. 登录 ━━━"
LOGIN_RESP=$(curl -s -X POST "$BASE/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@legalbot.com","password":"admin123456"}')
TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ 登录失败:"
  echo "$LOGIN_RESP" | python3 -m json.tool
  exit 1
fi
echo "✅ 登录成功 (admin)"
echo ""

# ── 2. 查看当前配置 ───────────────────────────────────
echo "━━━ 2. Agent 配置 ─━━"
curl -s "$BASE/settings/agent" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys,json
cfg = json.load(sys.stdin)['data']
print(f'  knowledge enabled: {bool(cfg[\"active_knowledge_ids\"])}')
print(f'  tool ids: {cfg[\"active_tool_ids\"]}')
"
echo ""

# ── 3. 创建会话 ──────────────────────────────────────
echo "━━━ 3. 创建会话 ━━━"
SESSION_RESP=$(curl -s -X POST "$BASE/chat/sessions" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"演示会话"}')
SID=$(echo "$SESSION_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null)
echo "✅ 会话 ID: $SID"
echo ""

# ── 4. 测试场景 ──────────────────────────────────────
echo "━━━ 4. 测试场景 ━━━"

questions=(
  "公司拖欠我工资三个月了，我该怎么维权？能拿到什么赔偿？"
  "上班路上发生交通事故算工伤吗？怎么申请工伤认定？"
  "离婚冷静期是多久？夫妻共同财产怎么分割？"
  "在小区被邻居的狗咬伤了，能要求赔偿吗？"
)

for q in "${questions[@]}"; do
  echo ""
  echo "─────────────────────────────────────────────"
  echo "📝 提问: $q"
  echo "─────────────────────────────────────────────"

  RESP=$(curl -s -X POST "$BASE/chat/ask" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d "{\"session_id\": \"$SID\", \"content\": \"$q\"}")

  ANSWER=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('answer','NO ANSWER')[:600])" 2>/dev/null)
  SOURCES=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('data',{}).get('sources',[]), ensure_ascii=False))" 2>/dev/null)

  echo "💬 回答:"
  echo "$ANSWER"
  echo ""
  echo "🔧 工具调用: $SOURCES"
  echo ""
done

echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║   演示完成                                      ║"
echo "╚═══════════════════════════════════════════════╝"
