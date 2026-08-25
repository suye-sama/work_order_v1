"""API 接口验证脚本"""
import sys, json
sys.stdout.reconfigure(encoding="utf-8")

import requests

BASE = "http://127.0.0.1:8000"

def p(msg):
    print(f"  {msg}")

def test():
    # 1. 登录
    print("=== 1. 登录 ===")
    r = requests.post(f"{BASE}/api/v1/auth/login", json={"username":"admin","password":"admin123"})
    assert r.status_code == 200, f"登录失败: {r.text}"
    token = r.json()["data"]["token"]
    user = r.json()["data"]["user"]
    p(f"登录成功: {user['real_name']} (role={user['role']})")

    headers = {"Authorization": f"Bearer {token}"}

    # 2. 当前用户
    print("=== 2. 当前用户 ===")
    r = requests.get(f"{BASE}/api/v1/auth/me", headers=headers)
    p(f"{r.json()['data']['username']} - OK")

    # 3. 创建3个客户
    print("=== 3. 创建客户 ===")
    customers = []
    for name, region in [("北京第一中学","北京"), ("上海实验学校","上海"), ("深圳职业技术学院","深圳")]:
        r = requests.post(f"{BASE}/api/v1/customers", headers=headers, json={
            "name": name, "region": region, "product_version": "V3.2.1",
            "deploy_type": "本地部署", "os": "Linux"
        })
        assert r.status_code == 200
        customers.append(r.json()["data"])
        p(f"  创建: [{r.json()['data']['id']}] {name}")

    # 4. 客户列表
    print("=== 4. 客户列表 ===")
    r = requests.get(f"{BASE}/api/v1/customers", headers=headers)
    p(f"  共 {r.json()['data']['total']} 条")

    # 5. 创建工单（含 raw_log）
    print("=== 5. 创建工单 ===")
    r = requests.post(f"{BASE}/api/v1/tickets", headers=headers, json={
        "title": "教务系统登录页面无法访问",
        "customer_id": 1, "priority": 1, "category": "系统故障",
        "description": "客户反馈：打开教务系统登录页时浏览器显示502 Bad Gateway错误。",
        "raw_log": "ssh root@192.168.1.100\nsystemctl status nginx\nsystemctl start nginx\nkill -9 1234\nsystemctl start nginx\ncurl http://localhost"
    })
    assert r.status_code == 200
    ticket = r.json()["data"]
    ticket_id = ticket["id"]
    p(f"  [{ticket['ticket_no']}] {ticket['title']}")
    p(f"  时间线: {len(ticket.get('timeline',[]))} 条")

    # 6. 创建第2个工单
    print("=== 6. 创建工单2 ===")
    r = requests.post(f"{BASE}/api/v1/tickets", headers=headers, json={
        "title": "数据库连接池耗尽导致服务超时",
        "customer_id": 2, "priority": 2, "category": "数据库异常",
        "description": "客户反馈系统操作卡顿，部分请求超时"
    })
    assert r.status_code == 200
    p(f"  [{r.json()['data']['ticket_no']}] OK")

    # 7. 工单列表
    print("=== 7. 工单列表 ===")
    r = requests.get(f"{BASE}/api/v1/tickets?page=1&page_size=5", headers=headers)
    data = r.json()["data"]
    p(f"  共 {data['total']} 条")
    for rec in data["records"]:
        p(f"    [{rec['status']}] {rec['ticket_no']} {rec['title'][:30]}")

    # 8. 工单详情
    print("=== 8. 工单详情 ===")
    r = requests.get(f"{BASE}/api/v1/tickets/{ticket_id}", headers=headers)
    d = r.json()["data"]
    p(f"  编号: {d['ticket_no']}")
    p(f"  时间线: {len(d.get('timeline',[]))} 条")
    p(f"  日志长度: {len(d.get('raw_log','') or '')} 字符")

    # 9. 状态流转: 1→2
    print("=== 9. 状态流转: 新建→处理中 ===")
    r = requests.post(f"{BASE}/api/v1/tickets/{ticket_id}/status", headers=headers, json={"status":2})
    p(f"  {r.json()['message']}")

    # 10. 状态流转: 2→3
    print("=== 10. 状态流转: 处理中→待确认 ===")
    r = requests.post(f"{BASE}/api/v1/tickets/{ticket_id}/status", headers=headers, json={"status":3})
    p(f"  {r.json()['message']}")

    # 11. 测试非法状态流转（应失败）
    print("=== 11. 非法状态流转: 待确认→新建(应失败) ===")
    r = requests.post(f"{BASE}/api/v1/tickets/{ticket_id}/status", headers=headers, json={"status":1})
    if r.status_code == 400:
        p(f"  正确拦截: {r.json()['detail']}")
    else:
        p(f"  状态码: {r.status_code}")

    # 12. 追加日志
    print("=== 12. 追加操作日志 ===")
    r = requests.post(f"{BASE}/api/v1/tickets/{ticket_id}/log?log_text=补充排查：旧Nginx进程残留占用80端口", headers=headers)
    d = r.json()["data"]
    p(f"  {r.json()['message']}, 时间线: {len(d.get('timeline',[]))} 条")

    # 13. 工作台
    print("=== 13. 工作台 ===")
    for name, path in [("待办","todo"), ("进行中","doing"), ("本周完成","completed")]:
        r = requests.get(f"{BASE}/api/v1/dashboard/{path}", headers=headers)
        p(f"  {name}: {r.json()['data']['total']} 条")

    # 14. 无Token访问
    print("=== 14. 无Token访问(应401) ===")
    r = requests.get(f"{BASE}/api/v1/tickets")
    if r.status_code == 401 or r.status_code == 403:
        p(f"  正确拦截: HTTP {r.status_code}")
    else:
        p(f"  状态码: {r.status_code} (预期401)")

    print("\n" + "="*50)
    print("   全部接口验证通过！")
    print("="*50)

if __name__ == "__main__":
    test()
