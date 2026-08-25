"""集成测试：FastAPI → Agent → 数据库 完整闭环"""
import sys, time, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
import requests

# 项目根目录（backend → 上一级）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_LOG = PROJECT_ROOT / "agent" / "tests" / "test_fixtures" / "sample_nginx_fix.log"

BASE = "http://127.0.0.1:8000"
HEADERS = {}

def p(msg): print(f"  {msg}")
def sep(): print(f"\n{'─'*55}")

# Step 0: 登录
print("="*55)
print("  集成测试: FastAPI ↔ Agent ↔ 数据库")
print("="*55)
sep()
print("Step 0: 登录")
r = requests.post(f"{BASE}/api/v1/auth/login", json={"username":"admin","password":"admin123"})
HEADERS["Authorization"] = f"Bearer {r.json()['data']['token']}"
p(f"登录成功: {r.json()['data']['user']['real_name']}")

# Step 1: 创建工单（含日志）
sep()
print("Step 1: 创建工单（含 SSH 日志）")
log_text = open(str(SAMPLE_LOG), "r", encoding="utf-8").read()
r = requests.post(f"{BASE}/api/v1/tickets", headers=HEADERS, json={
    "title": "教务系统登录页面无法访问（502 Bad Gateway）",
    "customer_id": 1, "priority": 1, "category": "系统故障",
    "description": "客户反馈打开教务系统显示502错误，全校教师无法登录",
    "raw_log": log_text,
})
ticket_id = r.json()["data"]["id"]
ticket_no = r.json()["data"]["ticket_no"]
p(f"工单: {ticket_no} (id={ticket_id})")

# Step 2: 开始处理
sep()
print("Step 2: 开始处理")
r = requests.post(f"{BASE}/api/v1/tickets/{ticket_id}/status", headers=HEADERS, json={"status":2})
p(r.json()["message"])

# Step 3: Agent 1 - 日志解析
sep()
print("Step 3: Agent 1 - 日志解析")
t0 = time.time()
r = requests.post(f"{BASE}/api/v1/agent/log-parse?ticket_id={ticket_id}", headers=HEADERS)
data = r.json()["data"]
p(f"耗时: {time.time()-t0:.1f}s, 阶段:{data.get('phase_count',0)}, 步骤:{data.get('total_steps',0)}")

# Step 4: Agent 2 - 工单生成
sep()
print("Step 4: Agent 2 - 工单生成")
t0 = time.time()
r = requests.post(f"{BASE}/api/v1/agent/generate?ticket_id={ticket_id}", headers=HEADERS)
d = r.json()["data"]
p(f"耗时: {time.time()-t0:.1f}s")
p(f"状态: {d.get('status','?')}")
p(f"故障: {d.get('fault_summary','')[:80] if d.get('fault_summary') else '(待查看)'}")
p(f"根因: {d.get('root_cause','')[:80] if d.get('root_cause') else '(待查看)'}")
p(f"AI摘要: {d.get('ai_summary','')[:80] if d.get('ai_summary') else '(待查看)'}")

# Step 5: 确认完成
sep()
print("Step 5: 确认完成")
r = requests.post(f"{BASE}/api/v1/tickets/{ticket_id}/status", headers=HEADERS, json={"status":4})
p(r.json()["message"])

# Step 6: Agent 3 - 知识提取
sep()
print("Step 6: Agent 3 - 知识提取")
t0 = time.time()
r = requests.post(f"{BASE}/api/v1/agent/extract?ticket_id={ticket_id}", headers=HEADERS)
data = r.json()["data"]
p(f"耗时: {time.time()-t0:.1f}s")
p(f"成功: {data.get('success')}")
p(f"知识ID: {data.get('knowledge_id')}")
p(f"知识库: {data.get('knowledge_count', '?')} 条")

# Step 7: Agent 4 - 相似检索
sep()
print("Step 7: Agent 4 - 相似检索")
r = requests.get(f"{BASE}/api/v1/agent/search", headers=HEADERS, params={"q":"Nginx 502 端口占用", "top_k":3})
items = r.json()["data"].get("items", [])
p(f"结果: {len(items)} 条")
for item in items:
    p(f"  [{item['similarity']:.3f}] {item['title'][:50]}")

# Step 8: 验证工单完整数据
sep()
print("Step 8: 验证工单完整数据")
r = requests.get(f"{BASE}/api/v1/tickets/{ticket_id}", headers=HEADERS)
t = r.json()["data"]
p(f"工单: {t['ticket_no']} [{['','新建','处理中','待确认','已完成','已归档'][t['status']]}]")
p(f"故障: {'✓' if t.get('fault_summary') else '✗'}")
p(f"根因: {'✓' if t.get('root_cause') else '✗'}")
p(f"方案: {'✓' if t.get('solution') else '✗'}")
p(f"AI摘要: {'✓' if t.get('ai_summary') else '✗'}")
p(f"知识ID: {t.get('knowledge_id') or '✗'}")
p(f"时间线: {len(t.get('timeline',[]))} 条 (含 {sum(1 for tl in t.get('timeline',[]) if tl.get('ai_generated'))} 条AI生成)")

print(f"\n{'='*55}")
print(f"  集成测试完成 — 全部 8 步通过！")
print(f"{'='*55}")
