"""
初始化示例数据 — 生成 50 条售后工单（学校场景为主）

运行方式：
  cd backend
  python seed_data.py

自动清除旧测试数据 → 创建客户 → 创建用户 → 生成 50 条工单
"""
import sys
import os
from datetime import datetime, timedelta
import random

# 确保 backend 在 path 中
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, create_tables
from app.models import User, Customer, CustomerContact, Ticket, TicketTimeline
from app.services.auth_service import hash_password

# ============================================================
# 1. 创建表
# ============================================================
print("创建数据库表 ...")
create_tables()

db = SessionLocal()

# ============================================================
# 2. 清理旧测试数据
# ============================================================
print("清理旧测试数据 ...")
db.query(TicketTimeline).delete()
db.query(Ticket).delete()
db.query(CustomerContact).delete()
db.query(Customer).delete()
db.query(User).filter(User.username.notin_(["admin", "engineer"])).delete()
db.commit()

# ============================================================
# 3. 创建用户
# ============================================================
print("创建用户 ...")

# 主用户（已存在则跳过）
existing = db.query(User).filter(User.username == "admin").first()
if not existing:
    db.add(User(username="admin", password_hash=hash_password("admin123"), real_name="系统管理员", role=1))
existing = db.query(User).filter(User.username == "engineer").first()
if not existing:
    db.add(User(username="engineer", password_hash=hash_password("engineer123"), real_name="张工", role=3))

# 额外工程师
engineers_data = [
    {"username": "li_wei", "real_name": "李伟", "role": 3},
    {"username": "wang_fang", "real_name": "王芳", "role": 3},
    {"username": "zhao_qiang", "real_name": "赵强", "role": 3},
    {"username": "sun_ming", "real_name": "孙明", "role": 3},
    {"username": "chen_li", "real_name": "陈丽", "role": 2},
]
for e in engineers_data:
    if not db.query(User).filter(User.username == e["username"]).first():
        db.add(User(username=e["username"], password_hash=hash_password("123456"), real_name=e["real_name"], role=e["role"], phone=f"138{random.randint(10000000,99999999)}"))
db.commit()

# 加载用户 ID
admin_id = db.query(User).filter(User.username == "admin").first().id
engineer_ids = [u.id for u in db.query(User).filter(User.role.in_([2, 3])).all()]
if not engineer_ids:
    engineer_ids = [admin_id]

# ============================================================
# 4. 创建学校客户
# ============================================================
print("创建客户 ...")

schools = [
    {"name": "北京市第一中学", "region": "华北", "product_version": "教务系统 V3.2.0", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0", "description": "完全中学，在校师生约3000人"},
    {"name": "上海市浦东新区实验小学", "region": "华东", "product_version": "教务系统 V3.2.1", "deploy_type": "云端部署", "os": "Linux Ubuntu 20.04", "db_type": "PostgreSQL 14", "description": "区重点小学，48个教学班"},
    {"name": "广州市天河中学", "region": "华南", "product_version": "教务系统 V3.1.8", "deploy_type": "本地部署", "os": "Linux CentOS 8", "db_type": "MySQL 5.7", "description": "省级示范高中"},
    {"name": "成都市第七中学", "region": "西南", "product_version": "教务系统 V3.2.0", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0", "description": "全国知名重点中学"},
    {"name": "武汉市实验学校", "region": "华中", "product_version": "教务系统 V3.2.1", "deploy_type": "云端部署", "os": "Linux Ubuntu 22.04", "db_type": "PostgreSQL 15", "description": "九年一贯制实验学校"},
    {"name": "南京市金陵中学", "region": "华东", "product_version": "教务系统 V3.2.0", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0", "description": "百年名校，省级重点"},
    {"name": "西安交通大学附属中学", "region": "西北", "product_version": "教务系统 V3.1.9", "deploy_type": "云端部署", "os": "Linux Ubuntu 20.04", "db_type": "PostgreSQL 14", "description": "大学附中，信息化建设领先"},
    {"name": "深圳实验学校", "region": "华南", "product_version": "教务系统 V3.2.2", "deploy_type": "本地部署", "os": "Linux CentOS 8", "db_type": "MySQL 8.0", "description": "深圳重点学校，智慧校园标杆"},
    {"name": "浙江杭州学军中学", "region": "华东", "product_version": "教务系统 V3.2.1", "deploy_type": "云端部署", "os": "Linux Ubuntu 22.04", "db_type": "PostgreSQL 15", "description": "省一级重点中学"},
    {"name": "山东师范大学附属中学", "region": "华东", "product_version": "教务系统 V3.2.0", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0", "description": "省级规范化学校"},
    {"name": "东北师范大学附属中学", "region": "东北", "product_version": "教务系统 V3.2.1", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0", "description": "教育部直属中学"},
    {"name": "重庆巴蜀中学", "region": "西南", "product_version": "教务系统 V3.1.8", "deploy_type": "云端部署", "os": "Linux Ubuntu 20.04", "db_type": "PostgreSQL 14", "description": "重庆市重点中学"},
]

customer_ids = []
for s in schools:
    c = Customer(**s)
    db.add(c)
    db.flush()
    customer_ids.append(c.id)
    # 添加联系人
    contact_names = [("信息中心-王老师", True), ("教务处-李老师", False)]
    for cn, is_p in contact_names:
        db.add(CustomerContact(
            customer_id=c.id,
            name=cn,
            phone=f"139{random.randint(10000000,99999999)}",
            email=f"contact{c.id}@school.edu.cn",
            position="信息中心主任" if is_p else "教务干事",
            is_primary=is_p,
        ))
db.commit()

# ============================================================
# 5. 工单数据模板
# ============================================================

base_date = datetime(2026, 3, 1, 9, 0, 0)

# ---------- 日志模板 ----------
LOG_TEMPLATES = {
    "nginx_502": """[root@school-server ~]# systemctl status nginx
● nginx.service - The nginx HTTP and reverse proxy server
   Loaded: loaded (/usr/lib/systemd/system/nginx.service; enabled)
   Active: inactive (dead) since Mon 2026-06-10 08:30:15 CST

[root@school-server ~]# systemctl start nginx
Job for nginx.service failed because the control process exited with error code.
See "systemctl status nginx.service" and "journalctl -xe" for details.

[root@school-server ~]# journalctl -xe -u nginx
Jun 10 08:30:15 school-server nginx[1823]: bind() to 0.0.0.0:80 failed (98: Address already in use)
Jun 10 08:30:15 school-server nginx[1823]: bind() to 0.0.0.0:443 failed (98: Address already in use)

[root@school-server ~]# netstat -tlnp | grep -E ':80|:443'
tcp   0   0 0.0.0.0:80    0.0.0.0:*   LISTEN   1024/nginx_old
tcp   0   0 0.0.0.0:443   0.0.0.0:*   LISTEN   1024/nginx_old

[root@school-server ~]# ps aux | grep nginx_old
root  1024  0.0  0.1  45876  2048 ?  Ss   Jun09  0:02 nginx_old: master process

[root@school-server ~]# kill -9 1024

[root@school-server ~]# systemctl start nginx
[root@school-server ~]# systemctl status nginx
● nginx.service - The nginx HTTP and reverse proxy server
   Active: active (running) since Mon 2026-06-10 08:35:22 CST

[root@school-server ~]# systemctl enable nginx
Created symlink /etc/systemd/system/multi-user.target.wants/nginx.service

[root@school-server ~]# curl -I http://localhost
HTTP/1.1 200 OK
Server: nginx/1.24.0""",

    "db_connect_fail": """[root@app-server ~]# mysql -u root -p
Enter password:
ERROR 1040 (HY000): Too many connections

[root@app-server ~]# mysqladmin -u root -p status
Uptime: 1209600  Threads: 151  Questions: 8923451  Slow queries: 23  Opens: 452
Max used connections: 150 (limit: 150)

[root@app-server ~]# mysql -u root -p -e "SHOW PROCESSLIST;"
+-------+------+-----------+---------+---------+------+-------+------------------+
| Id    | User | Host      | db      | Command | Time | State | Info             |
+-------+------+-----------+---------+---------+------+-------+------------------+
| 12345 | app  | localhost | edu_db  | Sleep   | 7200 |       | NULL             |
| 12346 | app  | localhost | edu_db  | Sleep   | 7150 |       | NULL             |
| ...   | ...  | ...       | ...     | Sleep   | ...  |       | ...              |
+-------+------+-----------+---------+---------+------+-------+------------------+
150 rows

[root@app-server ~]# mysql -u root -p -e "SET GLOBAL max_connections = 500;"
Query OK, 0 rows affected (0.00 sec)

[root@app-server ~]# mysql -u root -p -e "SET GLOBAL wait_timeout = 300;"
Query OK, 0 rows affected (0.00 sec)

[root@app-server ~]# mysql -u root -p -e "SHOW VARIABLES LIKE 'max_connections';"
+-----------------+-------+
| Variable_name   | Value |
+-----------------+-------+
| max_connections | 500   |
+-----------------+-------+

[root@app-server ~]# systemctl restart tomcat
[root@app-server ~]# curl -I http://localhost:8080/edu/login
HTTP/1.1 200 OK""",

    "disk_full": """[root@data-server ~]# df -h
Filesystem   Size  Used Avail Use% Mounted on
/dev/sda1    100G   96G     0 100% /
/dev/sdb1    500G  200G   300G  40% /data

[root@data-server ~]# du -sh /var/log/*
128M  /var/log/messages
1.2G  /var/log/journal
45G   /var/log/nginx
28G   /var/log/tomcat

[root@data-server ~]# ls -lhS /var/log/nginx/ | head -5
-rw-r--r-- 1 nginx nginx 22G Jun 08 10:00 access.log
-rw-r--r-- 1 nginx nginx 18G Jun 08 10:00 access.log.1
-rw-r--r-- 1 nginx nginx  5G Jun 01 00:00 error.log

[root@data-server ~]# cat > /etc/logrotate.d/nginx-custom << 'EOF'
/var/log/nginx/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    sharedscripts
    postrotate
        /usr/sbin/nginx -s reopen
    endscript
}
EOF

[root@data-server ~]# logrotate -f /etc/logrotate.d/nginx-custom
[root@data-server ~]# rm -f /var/log/nginx/access.log.1

[root@data-server ~]# df -h /
Filesystem   Size  Used Avail Use% Mounted on
/dev/sda1    100G   51G   49G  51% /""",

    "cert_expired": """[root@web-server ~]# curl -Iv https://edu.school.edu.cn 2>&1 | grep -E 'expire|certificate|SSL'
* SSL certificate problem: certificate has expired
* expire date: Jun  1 00:00:00 2026 GMT

[root@web-server ~]# openssl x509 -enddate -noout -in /etc/nginx/ssl/school.crt
notAfter=Jun  1 00:00:00 2026 GMT

[root@web-server ~]# certbot certonly --webroot -w /usr/share/nginx/html -d edu.school.edu.cn
Saving debug log to /var/log/letsencrypt/letsencrypt.log
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/edu.school.edu.cn/fullchain.pem

[root@web-server ~]# cp /etc/letsencrypt/live/edu.school.edu.cn/fullchain.pem /etc/nginx/ssl/school.crt
[root@web-server ~]# cp /etc/letsencrypt/live/edu.school.edu.cn/privkey.pem /etc/nginx/ssl/school.key
[root@web-server ~]# nginx -t && systemctl reload nginx

[root@web-server ~]# curl -I https://edu.school.edu.cn
HTTP/2 200""",

    "slow_query": """[root@db-server ~]# mysqladmin -u root -p processlist | head -20
| 4521 | app  | localhost | edu_db | Query   | 38  | Sending data | SELECT * FROM score WHERE term='202601' AND class_id IN (SELECT id FROM class WHERE grade='高三') ORDER BY total_score DESC |
| 4523 | app  | localhost | edu_db | Query   | 42  | Creating index | CREATE INDEX idx_score_term ON score(term, class_id, total_score) |

[root@db-server ~]# mysql -u root -p -e "EXPLAIN SELECT * FROM score WHERE term='202601' AND class_id IN (1,2,3,4,5,6,7,8);"
+----+-------------+-------+------+---------------+------+---------+------+--------+-------------+
| id | select_type | table | type | possible_keys | key  | key_len | ref  | rows   | Extra       |
+----+-------------+-------+------+---------------+------+---------+------+--------+-------------+
|  1 | SIMPLE      | score | ALL  | NULL          | NULL | NULL    | NULL | 500000 | Using where |
+----+-------------+-------+------+---------------+------+---------+------+--------+-------------+

[root@db-server ~]# mysql -u root -p -e "CREATE INDEX idx_score_term_class ON score(term, class_id);"
[root@db-server ~]# mysql -u root -p -e "ANALYZE TABLE score;"

[root@db-server ~]# mysql -u root -p -e "EXPLAIN SELECT * FROM score WHERE term='202601' AND class_id=3;"
+----+-------------+-------+------+----------------------+----------------------+---------+-------+------+-------+
| id | select_type | table | type | possible_keys        | key                  | key_len | ref   | rows | Extra |
+----+-------------+-------+------+----------------------+----------------------+---------+-------+------+-------+
|  1 | SIMPLE      | score | ref  | idx_score_term_class | idx_score_term_class | 34      | const | 1200 |       |
+----+-------------+-------+------+----------------------+----------------------+---------+-------+------+-------+"""
}

# ---------- 工单场景 ----------
TICKETS = [
    # ===== 状态 4-5（已完成/已归档）：30 条 =====
    # --- 系统故障类 (10条) ---
    {"title": "教务系统登录页报502错误，无法访问", "category": "系统故障", "status": 5,
     "desc": "周一上午8:30，全校教师反映登录教务系统时页面显示502 Bad Gateway，无法正常进入系统。正值期末考试周，教师需紧急录入成绩。",
     "log": "nginx_502",
     "resolution": "旧版nginx进程残留占用80/443端口导致新版nginx无法启动。强制终止旧进程后重启nginx服务恢复正常。"},
    {"title": "选课系统高峰期崩溃，学生无法选课", "category": "系统故障", "status": 5,
     "desc": "每学期选课开放首日上午10:00，系统并发骤增至2000+，Tomcat线程池耗尽，大量学生反馈页面白屏或504超时。",
     "log": "slow_query",
     "resolution": "临时扩容Tomcat线程池maxThreads从200→500，数据库连接池从150→300。后续增加Redis缓存选课数据，减少DB直连。"},
    {"title": "学校官网SSL证书过期，浏览器提示不安全", "category": "系统故障", "status": 5,
     "desc": "家长反映访问学校官网时浏览器提示「您的连接不是私密连接」，证书已过期2天，影响学校形象和招生宣传。",
     "log": "cert_expired",
     "resolution": "使用Let's Encrypt重新签发SSL证书，配置自动续期crontab，设置证书到期前30天邮件告警。"},
    {"title": "服务器磁盘空间耗尽，应用日志报错", "category": "系统故障", "status": 5,
     "desc": "教务系统突然无法登录，后端日志提示'No space left on device'。检查发现系统盘使用率100%。",
     "log": "disk_full",
     "resolution": "清理nginx和tomcat历史日志释放45GB空间，配置logrotate自动轮转，设置磁盘使用率>85%告警。"},
    {"title": "数据库连接池耗尽，应用请求超时", "category": "数据库异常", "status": 5,
     "desc": "下午14:30，教务系统所有页面报'数据库连接失败'。排查发现数据库连接数达到上限150，大量Sleep连接未释放。",
     "log": "db_connect_fail",
     "resolution": "调大max_connections至500，设置wait_timeout=300秒自动回收空闲连接。修复应用层连接未正确关闭的代码缺陷。"},
    {"title": "期末考试周成绩导入Excel功能报错", "category": "功能BUG", "status": 4,
     "desc": "教师批量导入期末成绩Excel时系统报'java.lang.OutOfMemoryError: Java heap space'，单次导入学生数超过3000人。",
     "log": "",
     "resolution": "优化Excel解析逻辑为SAX流式读取替代DOM全量加载，分批次提交事务，每500条commit一次。增加上传文件大小限制50MB。"},
    {"title": "家长端小程序白屏，接口返回500", "category": "功能BUG", "status": 4,
     "desc": "家长反馈放学时段（16:00-17:00）打开家校通小程序查看学生成绩时频繁白屏，刷新无效。集中在某一年级。",
     "log": "",
     "resolution": "定位到某SQL中IN子句参数超过1000个导致MySQL报错。改为分批次查询+程序merge。增加接口熔断降级逻辑。"},
    {"title": "校园一卡通充值服务间歇性不可用", "category": "网络异常", "status": 5,
     "desc": "食堂/超市POS机刷一卡通时偶发性提示'网络超时请重试'，高峰期（午餐12:00-12:30）频发，学生排队严重。",
     "log": "",
     "resolution": "排查发现核心交换机光模块故障导致丢包率5%。更换光模块后恢复正常。增加POS机本地缓存离线模式。"},
    {"title": "Linux服务器凌晨自动重启，教务服务中断", "category": "系统故障", "status": 5,
     "desc": "凌晨3:15教务系统全部服务中断，持续约10分钟。值班运维收到监控告警后排查发现服务器被自动重启。",
     "log": "",
     "resolution": "排查/var/log/sa发现凌晨OOM Killer杀死了内核进程。原因是备份脚本并发压缩100GB文件耗尽内存。改为串行压缩+限制内存使用。"},
    {"title": "教室多媒体终端无法连接中控平台", "category": "网络异常", "status": 4,
     "desc": "教学楼A栋全部24间教室的多媒体终端突然离线，中控平台显示全部'Offline'，影响当天上午全部课程。",
     "log": "",
     "resolution": "排查发现A栋弱电间交换机因空调故障过热自动保护断电。重启交换机+修复空调后恢复。在弱电间增加温度传感器。"},

    # --- 数据库异常类 (6条) ---
    {"title": "MySQL主从复制延迟超过30分钟", "category": "数据库异常", "status": 5,
     "desc": "监控发现MySQL主从复制延迟从正常<1秒飙升到30分钟，从库数据严重滞后，影响报表查询准确性。",
     "log": "",
     "resolution": "定位到大事务批量UPDATE 200万条成绩记录导致binlog积压。拆分大事务为每批5000条，从库增加并行复制线程。"},
    {"title": "Redis内存溢出，教务缓存全部失效", "category": "数据库异常", "status": 5,
     "desc": "Redis突然OOM重启，所有Session和业务缓存丢失，用户被迫重新登录，高峰期数据库压力陡增。",
     "log": "",
     "resolution": "设置Redis maxmemory-policy为allkeys-lru淘汰策略，增加内存从4G到16G，配置Sentinel高可用。"},
    {"title": "课表数据出现重复记录，学生课程混乱", "category": "数据库异常", "status": 4,
     "desc": "新学期课表发布后，多名学生反映同一时间出现两门不同课程。排查发现schedule表存在重复排课记录。",
     "log": "",
     "resolution": "在schedule表添加(term, class_id, week_day, period)唯一约束，清理历史重复数据。修复排课接口幂等性缺陷。"},
    {"title": "数据库定时备份任务连续3天失败", "category": "系统故障", "status": 5,
     "desc": "DBA发现数据库自动备份任务连续3天凌晨执行失败，备份文件大小为0KB，数据库数据无最新备份。",
     "log": "",
     "resolution": "排查发现备份存储NFS挂载点因网络波动断开，mysqldump写入失败无报错。增加备份后文件大小校验+企微通知。"},
    {"title": "PostgreSQL autovacuum阻塞业务查询", "category": "数据库异常", "status": 4,
     "desc": "下午业务高峰期，教务系统多个页面查询超时。数据库日志显示autovacuum正在对一张大表执行VACUUM FULL。",
     "log": "",
     "resolution": "调整autovacuum参数，设置vacuum_cost_limit从默认200→2000，增加autovacuum_workers到4。大表手动VACUUM改在凌晨执行。"},
    {"title": "学生信息表索引缺失导致分页查询极慢", "category": "数据库异常", "status": 5,
     "desc": "管理员在学生管理页面翻页到100页以后时，页面加载时间超过30秒，SQL执行计划显示全表扫描50万条。",
     "log": "",
     "resolution": "添加(name, student_no, class_id)复合索引，使用延迟关联（deferred join）优化深度分页。查询耗时从30秒降至100ms。"},

    # --- 配置错误类 (6条) ---
    {"title": "Nginx反向代理配置错误，部分页面404", "category": "配置错误", "status": 5,
     "desc": "运维调整Nginx配置后reload，发现教务系统中'/api/student/*'路径全部返回404，其余路径正常。",
     "log": "",
     "resolution": "检查nginx.conf发现location /api/student 后缺少斜杠匹配规则，导致精确匹配失败。修正为location /api/student/ { }。"},
    {"title": "应用连接数据库字符集不匹配导致中文乱码", "category": "配置错误", "status": 4,
     "desc": "新部署的测试环境教务系统所有中文显示为???，排查发现数据库连接URL中未指定characterEncoding参数。",
     "log": "",
     "resolution": "在JDBC连接串中添加useUnicode=true&characterEncoding=utf8mb4参数，同时统一MySQL服务端character-set-server=utf8mb4。"},
    {"title": "CORS跨域配置遗漏，H5页面接口调用失败", "category": "配置错误", "status": 5,
     "desc": "新上线的移动端H5家长端页面无法调用后端API，控制台报'Access-Control-Allow-Origin'错误。",
     "log": "",
     "resolution": "在Nginx配置中添加add_header Access-Control-Allow-Origin，后端增加OPTIONS预检请求处理，配置allowedOrigins白名单。"},
    {"title": "邮件服务SMTP配置错误，密码重置邮件发不出", "category": "配置错误", "status": 4,
     "desc": "多位教师反馈忘记密码后点击'找回密码'，提示邮件已发送但始终收不到，大量工单涌入。",
     "log": "",
     "resolution": "排查发现邮件服务商升级了SSL/TLS协议，旧配置使用TLSv1已被禁用。更新SMTP端口从25→587，启用STARTTLS。"},
    {"title": "K8s ConfigMap更新后Pod未自动重启", "category": "配置错误", "status": 5,
     "desc": "运维通过kubectl edit configmap更新数据库连接串后，预期Pod自动重载配置但实际未生效，仍连旧地址。",
     "log": "",
     "resolution": "ConfigMap的变更不会自动触发Pod重启。使用helm upgrade + annotation checksum/config触发滚动更新。后续引入Reloader工具。"},
    {"title": "日志级别配置为DEBUG导致磁盘IO打满", "category": "配置错误", "status": 5,
     "desc": "运维排查问题时将日志级别改为DEBUG忘记还原。3天后服务器磁盘IO飙升至100%，应用响应缓慢。",
     "log": "",
     "resolution": "将日志级别还原为INFO。清理50GB+ DEBUG日志。在logback配置中增加基于SizeAndTime的滚动策略，单文件上限200MB。"},

    # --- 功能BUG类 (5条) ---
    {"title": "学生请假审批流程卡在年级组长节点", "category": "功能BUG", "status": 4,
     "desc": "某学生提交请假申请后，班主任已审批通过，但流程在年级组长节点无法继续流转，按钮灰色不可点击。",
     "log": "",
     "resolution": "排查发现年级组长账号权限缓存未刷新，redis中旧角色数据导致按钮权限判断错误。清除缓存+修复审批人选择逻辑。"},
    {"title": "考勤统计报表导出数据与页面不一致", "category": "功能BUG", "status": 4,
     "desc": "管理员发现考勤月报页面显示某班缺勤5人，但导出Excel后显示缺勤8人，数据不一致引发老师投诉。",
     "log": "",
     "resolution": "排查发现导出逻辑使用了未过滤del_flag的原始查询，页面列表则过滤了软删除记录。统一导出和列表的数据源。"},
    {"title": "移动端APP闪退，Android 14系统兼容问题", "category": "功能BUG", "status": 5,
     "desc": "多名使用最新Android 14系统手机的教师反馈，打开APP查看课表时频繁闪退，旧系统手机正常。",
     "log": "",
     "resolution": "Android 14对后台Service启动有更严格限制，课表Widget刷新逻辑调用startService触发SecurityException。改为JobScheduler方案。"},
    {"title": "批量排课时教室冲突检测不准确", "category": "功能BUG", "status": 4,
     "desc": "新学期排课时，系统未检测到美术教室在同一时段被两个班级同时占用，导致开学第一周出现教师'抢教室'。",
     "log": "",
     "resolution": "修复排课算法的冲突检测逻辑，增加对专用教室（美术/音乐/实验室/机房）的独占约束检查，增加可视化冲突高亮。"},
    {"title": "成绩单PDF生成时部分学生姓名缺失", "category": "功能BUG", "status": 5,
     "desc": "打印学期成绩单PDF时，发现个别学生姓名为空白，但系统页面显示正常。问题涉及含生僻字的学生姓名。",
     "log": "",
     "resolution": "PDF生成引擎使用的字体文件（SimSun）不包含生僻字字形。替换为思源宋体（Source Han Serif），覆盖CJK统一汉字全字集。"},

    # --- 操作咨询类 (3条) ---
    {"title": "新教师培训：如何使用在线阅卷系统", "category": "操作咨询", "status": 5,
     "desc": "新学期大批新入职教师不熟悉在线阅卷系统操作，信息中心需提供集中培训和使用手册。",
     "log": "",
     "resolution": "录制10分钟操作演示视频+编写图文操作手册PDF，通过企业微信群发。在系统首页增加'新手引导'弹窗，关键操作增加Tooltip提示。"},
    {"title": "教务处咨询如何批量调整学生班级", "category": "操作咨询", "status": 5,
     "desc": "高二重新分班，教务处需将800名学生批量调整到新班级，手动逐个操作工作量巨大。",
     "log": "",
     "resolution": "提供Excel模板，支持批量导入学生新班级信息。后台实现事务性批量更新，异常行跳过并生成错误报告，处理时间<10秒。"},
    {"title": "班主任咨询如何导出综合素质评价汇总表", "category": "操作咨询", "status": 4,
     "desc": "学期末班主任需对学生进行综合素质评价并导出汇总表交教务处，但不清楚具体操作路径。",
     "log": "",
     "resolution": "在'学生评价'模块增加'一键导出汇总'按钮，自动聚合自评/互评/师评三维度数据生成Excel。附操作指引弹窗。"},

    # ===== 状态 2-3（处理中/待确认）：15 条 =====
    {"title": "教务系统工作日高峰期响应缓慢", "category": "系统故障", "status": 2,
     "desc": "近一周工作日上午9:00-11:00，教务系统平均响应时间从200ms上升至3-5秒，教师反馈页面加载缓慢。",
     "log": "", "resolution": ""},
    {"title": "学生综合素质评价模块数据丢失", "category": "功能BUG", "status": 2,
     "desc": "高一年级组长反映上周录入的学生社会实践评价数据突然消失，涉及6个班级约300名学生，数据无法恢复。",
     "log": "", "resolution": ""},
    {"title": "校园无线网络教学楼区域信号弱", "category": "网络异常", "status": 2,
     "desc": "教学楼3-5层师生反映WiFi信号只有1格或断开，严重影响智慧课堂教学。1-2层信号正常。",
     "log": "", "resolution": ""},
    {"title": "教师考勤打卡定位偏差，部分老师无法打卡", "category": "功能BUG", "status": 3,
     "desc": "新安装的校园考勤系统，教学楼B栋1层办公室老师反映GPS定位偏差约500米，无法完成打卡。",
     "log": "", "resolution": "初步排查为B栋墙体含金属屏蔽导致GPS信号弱。建议增加WiFi辅助定位+蓝牙信标方案，待校方审批。"},
    {"title": "学校微信公众号菜单跳转白名单配置问题", "category": "配置错误", "status": 2,
     "desc": "学校微信公众号底部菜单'成绩查询'点击后跳转到空白页面，排查发现微信公众平台OAuth2.0回调域名未配置。",
     "log": "", "resolution": ""},
    {"title": "数据中心空调故障告警，温度持续升高", "category": "系统故障", "status": 3,
     "desc": "数据中心环境监控告警：机房温度从22°C升至32°C，精密空调1号机压缩机故障报警，仅靠2号机维持。",
     "log": "", "resolution": "已联系空调维保厂商，备件压缩机预计明日上午到货。临时措施：打开机房门+工业风扇强制通风，关闭非核心服务器降低发热。"},
    {"title": "单点登录SSO集成CAS认证失败", "category": "配置错误", "status": 2,
     "desc": "教务系统接入学校统一身份认证平台（CAS）后，登录跳转返回'无效的service票据'错误，教师无法使用统一账号登录。",
     "log": "", "resolution": ""},
    {"title": "智慧班牌终端频繁自动重启", "category": "系统故障", "status": 3,
     "desc": "教学楼走廊20块智慧班牌最近一周频繁自动重启，每天3-5次，影响班级信息展示和通知发布。",
     "log": "", "resolution": "排查日志发现Android系统WebView内存泄露导致OOM。已推送OTA升级包到所有班牌终端，等待全部升级完成。"},
    {"title": "高考志愿填报系统安全渗透测试发现漏洞", "category": "功能BUG", "status": 2,
     "desc": "第三方安全厂商渗透测试发现志愿填报系统存在SQL注入漏洞和XSS跨站脚本漏洞，需紧急修复。",
     "log": "", "resolution": ""},
    {"title": "一卡通门禁系统部分读卡器失灵", "category": "系统故障", "status": 3,
     "desc": "学生宿舍1-3号楼门禁读卡器全部无法识别校园卡，学生只能由宿管手动开门，早晚高峰期拥堵严重。",
     "log": "", "resolution": "排查发现门禁控制器与服务器之间的RS485转换器电源适配器烧毁。已更换适配器，1-2号楼已恢复，3号楼正在调试。"},
    {"title": "学籍管理系统照片批量上传接口报错", "category": "功能BUG", "status": 2,
     "desc": "新学期学籍照片采集后，管理员一次性上传1500张学生照片，系统报'413 Request Entity Too Large'错误。",
     "log": "", "resolution": ""},
    {"title": "教务通知推送延迟超过2小时", "category": "系统故障", "status": 2,
     "desc": "教务处发送的紧急调课通知，部分教师2小时后才收到APP推送，导致多节课出现教师未到岗情况。",
     "log": "", "resolution": ""},
    {"title": "在线考试系统防作弊监控功能异常", "category": "功能BUG", "status": 3,
     "desc": "期中在线考试期间，监考教师反映防作弊功能的切屏检测未触发，学生可以自由切换浏览器标签页查阅资料。",
     "log": "", "resolution": "定位为浏览器visibilitychange事件在最新Chrome版本中的行为变更导致。已紧急更新前端检测脚本，待下次考试验证效果。"},
    {"title": "校车GPS轨迹数据上报中断", "category": "网络异常", "status": 2,
     "desc": "12辆校车的GPS设备同时停止上报位置数据，家长APP无法查看校车实时位置，引发家长电话咨询高峰。",
     "log": "", "resolution": ""},
    {"title": "校内视频监控存储回放异常", "category": "系统故障", "status": 2,
     "desc": "保安室反馈需要调取上周五校门口监控录像时，发现该时段录像文件损坏无法播放，其余时段正常。",
     "log": "", "resolution": ""},

    # ===== 状态 1（新建/待分配）：5 条 =====
    {"title": "学生宿舍水电费计费系统数据异常", "category": "功能BUG", "status": 1,
     "desc": "多名学生反映本月水电费账单金额异常偏高，某宿舍显示用电量超上月10倍，怀疑计费系统存在Bug。",
     "log": "", "resolution": ""},
    {"title": "校园广播系统定时播放功能失效", "category": "系统故障", "status": 1,
     "desc": "本周一升旗仪式铃声未按时播放，检查发现广播系统定时任务全部丢失，需要重新配置。",
     "log": "", "resolution": ""},
    {"title": "图书馆管理系统借还书扫码枪连接异常", "category": "系统故障", "status": 1,
     "desc": "图书馆3台扫码枪同时无法连接管理系统，提示'设备未识别'，USB重新插拔无效。",
     "log": "", "resolution": ""},
    {"title": "教师职称评审系统附件上传失败", "category": "功能BUG", "status": 1,
     "desc": "教师申报高级职称时需要上传PDF证明材料，部分教师反馈上传进度卡在99%后报错。",
     "log": "", "resolution": ""},
    {"title": "体育馆LED大屏播放应急预案内容无法更新", "category": "操作咨询", "status": 1,
     "desc": "体育馆管理处咨询如何更换LED大屏上的校园安全应急预案展示内容，旧版本信息已过期。",
     "log": "", "resolution": ""},
]

# ============================================================
# 6. 生成工单
# ============================================================
print(f"生成 {len(TICKETS)} 条工单 ...")

for i, tpl in enumerate(TICKETS):
    day_offset = i * random.randint(1, 3)
    create_dt = base_date + timedelta(days=day_offset, hours=random.randint(0, 12), minutes=random.randint(0, 59))

    status = tpl["status"]
    customer_id = random.choice(customer_ids)
    handler_id = random.choice(engineer_ids) if status >= 2 else None
    start_dt = create_dt + timedelta(hours=random.randint(1, 6)) if status >= 2 else None
    finish_dt = (start_dt + timedelta(hours=random.randint(1, 48))) if status >= 4 and start_dt else None
    duration = int((finish_dt - start_dt).total_seconds() / 60) if finish_dt and start_dt else None

    # 为有日志的工单生成 raw_log
    raw_log = ""
    log_key = tpl.get("log", "")
    if log_key and log_key in LOG_TEMPLATES:
        raw_log = LOG_TEMPLATES[log_key]

    # 为已完成工单预填 AI 生成内容
    fault_summary = ""
    root_cause = ""
    solution = ""
    ai_summary = ""
    if status >= 4:
        fault_summary = tpl.get("desc", "")[:200]
        resolution = tpl.get("resolution", "")
        if resolution and "：" in resolution:
            parts = resolution.split("。", 1)
            root_cause = parts[0] if parts else resolution
            solution = resolution
        else:
            root_cause = resolution
            solution = resolution
        ai_summary = f"【{tpl['category']}】{tpl['title']}。{resolution[:100]}"

    ticket = Ticket(
        ticket_no=f"WO{create_dt.strftime('%Y%m%d')}{i+1:03d}",
        title=tpl["title"],
        customer_id=customer_id,
        category=tpl["category"],
        priority=random.choice([1, 2, 2, 2, 3]),  # 中优先级居多
        status=status,
        source=random.choice(["电话", "微信", "钉钉", "邮件", "运维监控"]),
        description=tpl["desc"],
        fault_summary=fault_summary or None,
        root_cause=root_cause or None,
        solution=solution or None,
        ai_summary=ai_summary or None,
        raw_log=raw_log or None,
        handler_id=handler_id,
        start_time=start_dt,
        finish_time=finish_dt,
        duration=duration,
        create_time=create_dt,
        update_time=create_dt,
    )
    db.add(ticket)
    db.flush()

    # ===== 生成时间线 =====
    # 1) 创建节点
    db.add(TicketTimeline(
        ticket_id=ticket.id,
        node_time=create_dt,
        node_type="创建",
        title=f"工单创建 — {tpl['category']}",
        content=f"来源：{ticket.source}\n{tpl['desc'][:200]}",
        operator=str(admin_id),
    ))

    # 2) 受理节点
    if status >= 2 and start_dt:
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            node_time=start_dt,
            node_type="受理",
            title=f"工程师受理 — 开始处理",
            content=f"处理人接单，开始排查处理。",
            operator=str(handler_id),
        ))

    # 3) 中间排查节点
    if status >= 3 and start_dt:
        mid_dt = start_dt + timedelta(hours=random.randint(1, 4))
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            node_time=mid_dt,
            node_type="排查",
            title="排查定位中",
            content="正在排查故障根因，分析日志和配置..." if not raw_log else raw_log[:500],
            operator=str(handler_id),
        ))

    # 4) 完成节点
    if status >= 4 and finish_dt:
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            node_time=finish_dt,
            node_type="完成",
            title=f"处理完成 — {tpl['category']}已修复",
            content=tpl.get("resolution", "问题已解决")[:500],
            operator=str(handler_id),
        ))

    # 5) 归档节点
    if status >= 5:
        archive_dt = finish_dt + timedelta(days=random.randint(1, 7)) if finish_dt else create_dt + timedelta(days=random.randint(3, 10))
        db.add(TicketTimeline(
            ticket_id=ticket.id,
            node_time=archive_dt,
            node_type="归档",
            title="工单已归档",
            content="问题确认解决，工单归档。",
            operator=str(admin_id),
        ))

    if (i + 1) % 10 == 0:
        db.commit()
        print(f"  已生成 {i+1}/{len(TICKETS)} 条工单 ...")

db.commit()

# ============================================================
# 7. 统计输出
# ============================================================
total = db.query(Ticket).count()
done = db.query(Ticket).filter(Ticket.status.in_([4, 5])).count()
pending = db.query(Ticket).filter(Ticket.status.in_([1, 2, 3])).count()
customers = db.query(Customer).count()
users = db.query(User).count()

print("\n[OK] 数据初始化完成!")
print(f"   用户: {users} 人")
print(f"   客户(学校): {customers} 所")
print(f"   工单总计: {total} 条")
print(f"     - 已完成/已归档: {done} 条")
print(f"     - 处理中/待确认: {pending} 条")
print(f"   登录账号: admin / admin123")
print(f"   登录账号: engineer / engineer123")

db.close()
