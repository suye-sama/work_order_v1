"""端到端测试：日志解析 → 工单生成 → 知识提取 → 相似检索"""
import sys, time
sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（agent/tests → agent → 项目根）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from app.agents.process_recorder import parse_log
from app.agents.ticket_generator import generate_ticket
from app.agents.knowledge_extractor import extract_knowledge, search_knowledge

# 读取样本日志
log = open("tests/test_fixtures/sample_nginx_fix.log", "r", encoding="utf-8").read()
title = "教务系统登录页面无法访问（502 Bad Gateway）"
t1_total = time.time()

# ==== Agent 1: 日志解析 ====
print("=" * 65)
print("  Agent 1: 日志解析")
print("=" * 65)
t0 = time.time()
r1 = parse_log(log)
print(f"  {r1['total_steps']}步骤 {r1['phase_count']}阶段 {time.time()-t0:.1f}s")

# ==== Agent 2: 工单生成 ====
print("\n" + "=" * 65)
print("  Agent 2: 工单生成")
print("=" * 65)
t0 = time.time()
r2 = generate_ticket(
    title=title,
    description="客户反馈打开教务系统显示502错误，全校教师无法登录",
    customer_info="北京第一中学 / V3.2.1 / 本地部署 / Linux / PostgreSQL",
    timeline_json=r1.get("timeline", []),
    raw_log=log,
    engineer_notes="服务器昨晚自动重启，早上发现服务异常。旧Nginx进程残留占用端口。",
)
print(f"  成功: {r2['success']} 耗时: {time.time()-t0:.1f}s")
res = r2.get("result", {})
if isinstance(res, dict):
    rc = res.get("root_cause", {})
    if isinstance(rc, dict):
        print(f"  根因: {rc.get('root_cause', '')[:80]}")
    sm = res.get("summary_info", {})
    if isinstance(sm, dict):
        print(f"  标签: {sm.get('tags', [])}")

# ==== Agent 3: 知识提取 ====
print("\n" + "=" * 65)
print("  Agent 3: 知识提取")
print("=" * 65)
t0 = time.time()

# 从 Agent 2 的输出中提取数据
fp = res.get("fault_phenomenon", {}) if isinstance(res, dict) else {}
rc = res.get("root_cause", {}) if isinstance(res, dict) else {}
sol = res.get("solution", {}) if isinstance(res, dict) else {}
sm = res.get("summary_info", {}) if isinstance(res, dict) else {}

r3 = extract_knowledge(
    ticket_id=1,
    title=title,
    fault_phenomenon=fp,
    root_cause=rc,
    solution=sol,
    summary_info=sm,
    tags=sm.get("tags", []) if isinstance(sm, dict) else [],
    category=rc.get("category", "") if isinstance(rc, dict) else "系统故障",
)
print(f"  成功: {r3['success']} 耗时: {time.time()-t0:.1f}s")
print(f"  知识ID: {r3['knowledge_id']}")
print(f"  去重命中: {r3.get('dedup', False)}")
print(f"  知识库总数: {r3.get('knowledge_count', 0)}")
entry = r3.get("entry", {})
if isinstance(entry, dict):
    print(f"  条目标题: {entry.get('title', '')[:60]}")
    print(f"  难度: {entry.get('difficulty', '')}")

# ==== Agent 4: 相似检索 ====
print("\n" + "=" * 65)
print("  Agent 4: 相似检索")
print("=" * 65)
t0 = time.time()
r4 = search_knowledge("Nginx 502 端口占用 服务无法启动")
print(f"  查询耗时: {time.time()-t0:.1f}s")
print(f"  检索结果: {len(r4.get('items', []))} 条")
for item in r4.get("items", [])[:3]:
    print(f"    [{item.get('similarity', 0):.3f}] {item.get('title', '')[:50]}")

print(f"\n{'='*65}")
print(f"  全链路总耗时: {time.time()-t1_total:.1f}s")
print(f"{'='*65}")
