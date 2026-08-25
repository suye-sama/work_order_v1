"""测试工单生成 Agent"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import json, requests

BASE = "http://127.0.0.1:5000"

# 测试数据：Nginx 故障修复
payload = {
    "ticket_id": 1,
    "title": "教务系统登录页面无法访问（502 Bad Gateway）",
    "description": "客户反馈：打开教务系统登录页时浏览器显示502 Bad Gateway错误，全校教师无法登录。",
    "customer_info": "客户：北京第一中学 / 产品版本：V3.2.1 / 部署方式：本地部署 / OS：Linux",
    "raw_log": """ssh root@192.168.1.100
systemctl status nginx
# nginx.service: inactive (dead)
systemctl start nginx
# Job for nginx.service failed
journalctl -xe -u nginx --no-pager
# nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)
netstat -tlnp | grep :80
# tcp 0 0 0.0.0.0:80 0.0.0.0:* LISTEN 1234/nginx_old
ps aux | grep nginx
# root 1234 nginx: master process /usr/sbin/nginx_old
kill -9 1234
systemctl start nginx
systemctl status nginx
# nginx.service: active (running)
curl -I http://localhost
# HTTP/1.1 200 OK
systemctl enable nginx""",
    "engineer_notes": "服务器昨晚自动重启过，早上发现服务异常。排查发现是旧 Nginx 进程残留占用端口导致。已清理并设置开机自启。",
}

print("=" * 60)
print("  工单生成 Agent 测试")
print("=" * 60)
print(f"\n标题: {payload['title']}")
print(f"日志长度: {len(payload['raw_log'])} 字符")

# Step 1: 先解析日志获取时间线
print("\n--- Step 1: 日志解析 ---")
r = requests.post(f"{BASE}/agent/log/parse", json={
    "log_text": payload["raw_log"],
    "ticket_id": 1,
})
parse_result = r.json()
print(f"  时间线: {parse_result['total_steps']} 步, {parse_result['phase_count']} 阶段, {parse_result['duration_ms']}ms")

# Step 2: 用时间线 + 原始数据生成工单
print("\n--- Step 2: 工单生成 ---")
payload["timeline_json"] = parse_result.get("timeline", [])
r = requests.post(f"{BASE}/agent/ticket/generate", json=payload)
result = r.json()

print(f"  成功: {result['success']}")
print(f"  耗时: {result['duration_ms']}ms")
if result.get("error"):
    print(f"  错误: {result['error'][:100]}")

res = result.get("result", {})
if res:
    fault = res.get("fault_phenomenon", {})
    ts = res.get("troubleshooting", [])
    rc = res.get("root_cause", {})
    sol = res.get("solution", {})
    sm = res.get("summary_info", {})

    print(f"\n  【故障现象】{fault.get('phenomenon','')[:80]}")
    print(f"  【影响范围】{fault.get('impact_scope','')[:80]}")
    print(f"  【排查步骤】{len(ts)} 步")
    for t in ts[:3]:
        print(f"      {t.get('step','?')}. {t.get('action','')[:50]}")
    print(f"  【根因】{rc.get('root_cause','')[:80]}")
    print(f"  【分类】{rc.get('category','')}")
    print(f"  【解决方案】{sol.get('solution','')[:80]}")
    print(f"  【修复步骤】{len(sol.get('steps',[]))} 步")
    for s in sol.get('steps',[])[:3]:
        print(f"      - {s[:60]}")
    print(f"  【标签】{sm.get('tags',[])}")
    print(f"  【摘要】{sm.get('summary','')[:120]}")

print(f"\n{'='*60}")
print(f"  测试完成 — Agent 2 工单生成就绪")
print(f"{'='*60}")
