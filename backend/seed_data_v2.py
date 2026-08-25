"""
重构测试数据 — 20 条工单

运行方式：
  cd backend
  python seed_data_v2.py

生成内容：
  - 5 条已完成工单（含完整生命周期: 排查建议/日志解析/AI生成/时间线/知识库）
  - 15 条新建工单（含基本信息 + 完整操作日志用于调试演示）
  - data/debug_logs.txt（15 条新建工单的标题+日志，供调试使用）
"""
import sys
import os
import json
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, create_tables
from app.models import User, Customer, CustomerContact, Ticket, TicketTimeline
from app.services.auth_service import hash_password

print("=" * 60)
print("  轻量化售后工单系统 — 测试数据重构")
print("=" * 60)

create_tables()
db = SessionLocal()

# ============================================================
# 1. 清理所有旧数据
# ============================================================
print("\n[1/5] 清理旧数据 ...")
db.query(TicketTimeline).delete()
db.query(Ticket).delete()
db.query(CustomerContact).delete()
db.query(Customer).delete()
db.query(User).delete()
db.commit()
print("      已清空所有表")

# ============================================================
# 2. 创建用户
# ============================================================
print("\n[2/5] 创建用户 ...")

users_data = [
    ("admin", "admin123", "系统管理员", 1),
    ("engineer", "engineer123", "张工", 3),
    ("li_wei", "123456", "李伟", 3),
    ("wang_fang", "123456", "王芳", 3),
    ("zhao_qiang", "123456", "赵强", 2),
]
user_ids = {}
for uname, pwd, rname, role in users_data:
    u = User(
        username=uname,
        password_hash=hash_password(pwd),
        real_name=rname,
        role=role,
        phone=f"138{random.randint(10000000,99999999)}",
        email=f"{uname}@company.com",
    )
    db.add(u)
    db.flush()
    user_ids[uname] = u.id
db.commit()
print(f"      创建 {len(users_data)} 个用户")

admin_id = user_ids["admin"]
engineer_ids = [user_ids[n] for n in ["engineer", "li_wei", "wang_fang", "zhao_qiang"]]

# ============================================================
# 3. 创建客户（学校）
# ============================================================
print("\n[3/5] 创建客户 ...")

schools = [
    {"name": "北京市第一中学", "region": "华北", "product_version": "教务系统 V3.2.0", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0"},
    {"name": "上海浦东实验小学", "region": "华东", "product_version": "教务系统 V3.2.1", "deploy_type": "云端部署", "os": "Linux Ubuntu 22.04", "db_type": "PostgreSQL 15"},
    {"name": "广州天河中学", "region": "华南", "product_version": "教务系统 V3.1.8", "deploy_type": "本地部署", "os": "Linux CentOS 8", "db_type": "MySQL 5.7"},
    {"name": "成都第七中学", "region": "西南", "product_version": "教务系统 V3.2.0", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0"},
    {"name": "武汉实验学校", "region": "华中", "product_version": "教务系统 V3.2.1", "deploy_type": "云端部署", "os": "Linux Ubuntu 22.04", "db_type": "PostgreSQL 15"},
    {"name": "南京金陵中学", "region": "华东", "product_version": "教务系统 V3.2.0", "deploy_type": "本地部署", "os": "Linux CentOS 7.9", "db_type": "MySQL 8.0"},
    {"name": "西安交大附中", "region": "西北", "product_version": "教务系统 V3.1.9", "deploy_type": "云端部署", "os": "Linux Ubuntu 20.04", "db_type": "PostgreSQL 14"},
    {"name": "深圳实验学校", "region": "华南", "product_version": "教务系统 V3.2.2", "deploy_type": "本地部署", "os": "Linux CentOS 8", "db_type": "MySQL 8.0"},
    {"name": "杭州学军中学", "region": "华东", "product_version": "教务系统 V3.2.1", "deploy_type": "云端部署", "os": "Linux Ubuntu 22.04", "db_type": "PostgreSQL 15"},
    {"name": "重庆巴蜀中学", "region": "西南", "product_version": "教务系统 V3.1.8", "deploy_type": "云端部署", "os": "Linux Ubuntu 20.04", "db_type": "PostgreSQL 14"},
]

customer_ids = []
for s in schools:
    c = Customer(**s)
    db.add(c)
    db.flush()
    customer_ids.append(c.id)
    # 添加联系人
    db.add(CustomerContact(customer_id=c.id, name="信息中心-王老师", phone=f"139{random.randint(10000000,99999999)}", email=f"it{c.id}@school.edu.cn", position="信息中心主任", is_primary=True))
    db.add(CustomerContact(customer_id=c.id, name="教务处-李老师", phone=f"138{random.randint(10000000,99999999)}", email=f"jw{c.id}@school.edu.cn", position="教务干事", is_primary=False))
db.commit()
print(f"      创建 {len(schools)} 所学校 + 联系人")


# ============================================================
# 4. 生成 20 条工单
# ============================================================
print("\n[4/5] 生成 20 条工单 ...")

base_date = datetime(2026, 7, 1, 9, 0, 0)
random.seed(42)

# ─────────── 日志库（用于已完成工单 + 新建工单）───────────
LOG_NGINX_502 = """[root@school-server ~]# systemctl status nginx
● nginx.service - The nginx HTTP and reverse proxy server
   Loaded: loaded (/usr/lib/systemd/system/nginx.service; enabled)
   Active: inactive (dead) since Tue 2026-07-15 08:30:15 CST

[root@school-server ~]# systemctl start nginx
Job for nginx.service failed because the control process exited with error code.
See "systemctl status nginx.service" and "journalctl -xe" for details.

[root@school-server ~]# journalctl -xe -u nginx | tail -20
Jul 15 08:30:15 school-server nginx[1823]: bind() to 0.0.0.0:80 failed (98: Address already in use)
Jul 15 08:30:15 school-server nginx[1823]: bind() to 0.0.0.0:443 failed (98: Address already in use)

[root@school-server ~]# netstat -tlnp | grep -E ':80|:443'
tcp   0   0 0.0.0.0:80    0.0.0.0:*   LISTEN   1024/nginx_old
tcp   0   0 0.0.0.0:443   0.0.0.0:*   LISTEN   1024/nginx_old

[root@school-server ~]# ps aux | grep nginx_old
root  1024  0.0  0.1  45876  2048 ?  Ss   Jul14  0:02 nginx_old: master process

[root@school-server ~]# kill -9 1024

[root@school-server ~]# systemctl start nginx
[root@school-server ~]# systemctl status nginx
● nginx.service - The nginx HTTP and reverse proxy server
   Active: active (running) since Tue 2026-07-15 08:35:22 CST

[root@school-server ~]# systemctl enable nginx
[root@school-server ~]# curl -I http://localhost
HTTP/1.1 200 OK
Server: nginx/1.24.0"""

LOG_DB_CONN = """[root@app-server ~]# mysql -u root -p -e "SELECT COUNT(*) FROM information_schema.PROCESSLIST;"
COUNT(*)
150

[root@app-server ~]# mysql -u root -p -e "SHOW VARIABLES LIKE 'max_connections';"
max_connections | 150

[root@app-server ~]# mysql -u root -p -e "SHOW PROCESSLIST;" | head -10
Id | User | Host      | db     | Command | Time | State | Info
12345 | app  | localhost | edu_db | Sleep   | 7200 |       | NULL
12346 | app  | localhost | edu_db | Sleep   | 7150 |       | NULL
12347 | app  | localhost | edu_db | Sleep   | 7100 |       | NULL
...

[root@app-server ~]# mysql -u root -p -e "SET GLOBAL max_connections = 500;"
[root@app-server ~]# mysql -u root -p -e "SET GLOBAL wait_timeout = 300;"
[root@app-server ~]# mysql -u root -p -e "SHOW VARIABLES LIKE 'max_connections';"
max_connections | 500

[root@app-server ~]# systemctl restart tomcat
[root@app-server ~]# curl -I http://localhost:8080/edu/login
HTTP/1.1 200 OK"""

LOG_DISK_FULL = """[root@data-server ~]# df -h
Filesystem   Size  Used Avail Use% Mounted on
/dev/sda1    100G   96G     0 100% /
/dev/sdb1    500G  200G   300G  40% /data

[root@data-server ~]# du -sh /var/log/*
128M  /var/log/messages
1.2G  /var/log/journal
45G   /var/log/nginx
28G   /var/log/tomcat

[root@data-server ~]# ls -lhS /var/log/nginx/ | head -5
-rw-r--r-- 1 nginx nginx 22G Jul 14 10:00 access.log
-rw-r--r-- 1 nginx nginx 18G Jul 14 10:00 access.log.1
-rw-r--r-- 1 nginx nginx  5G Jul 01 00:00 error.log

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
/dev/sda1    100G   51G   49G  51% /"""

LOG_CERT_EXPIRE = """[root@web-server ~]# curl -Iv https://edu.school.edu.cn 2>&1 | grep -E 'expire|certificate|SSL'
* SSL certificate problem: certificate has expired
* expire date: Jul  1 00:00:00 2026 GMT

[root@web-server ~]# openssl x509 -enddate -noout -in /etc/nginx/ssl/school.crt
notAfter=Jul  1 00:00:00 2026 GMT

[root@web-server ~]# certbot certonly --webroot -w /usr/share/nginx/html -d edu.school.edu.cn
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/edu.school.edu.cn/fullchain.pem

[root@web-server ~]# cp /etc/letsencrypt/live/edu.school.edu.cn/fullchain.pem /etc/nginx/ssl/school.crt
[root@web-server ~]# cp /etc/letsencrypt/live/edu.school.edu.cn/privkey.pem /etc/nginx/ssl/school.key
[root@web-server ~]# nginx -t && systemctl reload nginx
[root@web-server ~]# curl -I https://edu.school.edu.cn
HTTP/2 200"""

LOG_SLOW_SQL = """[root@db-server ~]# mysqladmin -u root -p processlist | head -10
| 4521 | app  | localhost | edu_db | Query   | 38  | Sending data | SELECT * FROM score WHERE term='202601' AND class_id IN (SELECT id FROM class WHERE grade='高三') ORDER BY total_score DESC |

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

LOG_REDIS_OOM = """[root@cache-server ~]# redis-cli INFO memory
used_memory:4294967296
used_memory_human:4.00G
maxmemory:4294967296
maxmemory_human:4.00G
maxmemory_policy:noeviction

[root@cache-server ~]# redis-cli INFO keyspace
db0:keys=15234567,expires=0,avg_ttl=0

[root@cache-server ~]# tail -50 /var/log/redis/redis.log
[7834] 15 Jul 14:30:22 # OOM command not allowed when used memory > 'maxmemory'.
[7834] 15 Jul 14:30:25 # OOM command not allowed when used memory > 'maxmemory'.
[7834] 15 Jul 14:32:10 * Saving the final RDB before exiting.
[7834] 15 Jul 14:32:15 * DB saved on disk
[7834] 15 Jul 14:32:15 # Redis is now ready to exit, bye bye...

[root@cache-server ~]# redis-cli CONFIG SET maxmemory 8gb
[root@cache-server ~]# redis-cli CONFIG SET maxmemory-policy allkeys-lru
[root@cache-server ~]# redis-cli CONFIG REWRITE
[root@cache-server ~]# systemctl restart redis
[root@cache-server ~]# redis-cli PING
PONG"""

LOG_TOMCAT_OOM = """[root@app-server ~]# tail -100 /opt/tomcat/logs/catalina.out
java.lang.OutOfMemoryError: Java heap space
        at org.apache.poi.xssf.usermodel.XSSFSheet.read(XSSFSheet.java:245)
        at com.edu.service.ExcelService.importScores(ExcelService.java:128)
        at com.edu.controller.ScoreController.importExcel(ScoreController.java:56)
...
Exception in thread "http-nio-8080-exec-8" java.lang.OutOfMemoryError: Java heap space

[root@app-server ~]# ps aux | grep tomcat
root  4521  2.5 98.0 4194304 3920000 ?  Sl  09:30 125:30 /usr/java/jdk-11/bin/java -Xmx512m -jar tomcat.jar

[root@app-server ~]# cat /opt/tomcat/bin/setenv.sh
JAVA_OPTS="-Xms256m -Xmx512m -XX:MaxPermSize=128m"

[root@app-server ~]# sed -i 's/-Xmx512m/-Xmx2048m/' /opt/tomcat/bin/setenv.sh
[root@app-server ~]# sed -i 's/-Xms256m/-Xms1024m/' /opt/tomcat/bin/setenv.sh
[root@app-server ~]# systemctl restart tomcat
[root@app-server ~]# curl -I http://localhost:8080/edu/login
HTTP/1.1 200 OK"""

LOG_NETWORK_LOSS = """[root@switch-room ~]# ssh core-switch-01
core-switch-01# show interfaces gi1/0/24
GigabitEthernet1/0/24 is up, line protocol is up
  Input errors: 0, CRC: 0
  Output errors: 0, collisions: 0
  Output queue: 0/40 (size/max)
  5 minute input rate: 850000000 bits/sec, 125000 packets/sec
  5 minute output rate: 920000000 bits/sec, 138000 packets/sec

core-switch-01# show interfaces gi1/0/24 | include errors
  5234 input errors, 3120 CRC, 0 frame, 0 overrun, 0 ignored

core-switch-01# show logging | include Jul 15
Jul 15 14:25:01: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/24, changed state to down
Jul 15 14:25:05: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/24, changed state to up
Jul 15 14:28:11: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/24, changed state to down
Jul 15 14:28:18: %LINK-3-UPDOWN: Interface GigabitEthernet1/0/24, changed state to up

core-switch-01# show interface gi1/0/24 transceiver
Temperature: 58.2 C (Warning: > 50C)
Voltage: 3.28 V
Current: 8.5 mA
TX Power: -2.8 dBm
RX Power: -28.5 dBm (Warning: < -20 dBm)"""

LOG_K8S_POD_CRASH = """[root@k8s-master ~]# kubectl get pods -n edu-system
NAME                          READY   STATUS             RESTARTS      AGE
edu-api-7d8f9c6b-abcde       0/1     CrashLoopBackOff   15            2h
edu-api-7d8f9c6b-fghij       1/1     Running            0             2h
edu-api-7d8f9c6b-klmno       1/1     Running            0             2h
edu-web-5c8b9d-xyz01         1/1     Running            2             5d
edu-db-0                      1/1     Running            0             30d
edu-redis-0                   1/1     Running            0             30d

[root@k8s-master ~]# kubectl logs edu-api-7d8f9c6b-abcde -n edu-system --tail=50
Traceback (most recent call last):
  File "/app/main.py", line 23, in <module>
    redis_client = redis.from_url(os.environ["REDIS_URL"])
KeyError: 'REDIS_URL'
During handling of the above exception, another exception occurred:
SystemExit: 1

[root@k8s-master ~]# kubectl describe pod edu-api-7d8f9c6b-abcde -n edu-system | grep -A5 "Environment"
Environment:
    DB_URL:    postgresql://edu-db-0.edu-db:5432/edu
    # REDIS_URL is missing!

[root@k8s-master ~]# kubectl get configmap edu-config -n edu-system -o yaml
data:
  DB_URL: postgresql://edu-db-0.edu-db:5432/edu
  REDIS_URL: redis://edu-redis-0.edu-redis:6379/0

[root@k8s-master ~]# kubectl rollout restart deployment edu-api -n edu-system
[root@k8s-master ~]# kubectl get pods -n edu-system | grep edu-api
edu-api-7d8f9c6b-new01      1/1     Running            0             30s
edu-api-7d8f9c6b-new02      1/1     Running            0             28s
edu-api-7d8f9c6b-new03      1/1     Running            0             25s"""

LOG_MYSQL_REPLICATION = """[root@db-master ~]# mysql -u root -p -e "SHOW SLAVE STATUS\\G" | grep -E "Seconds_Behind_Master|Slave_IO_Running|Slave_SQL_Running"
Slave_IO_Running: Yes
Slave_SQL_Running: Yes
Seconds_Behind_Master: 1800

[root@db-master ~]# mysql -u root -p -e "SHOW PROCESSLIST;" | grep -i "binlog"
1234 | system | localhost | NULL | Binlog Dump | 1800 | Master has sent all binlog

[root@db-master ~]# mysql -u root -p -e "SELECT COUNT(*) FROM information_schema.INNODB_TRX;"
COUNT(*)
5

[root@db-master ~]# mysql -u root -p -e "SELECT trx_id, trx_state, trx_rows_modified, TIMESTAMPDIFF(SECOND, trx_started, NOW()) as sec FROM information_schema.INNODB_TRX;"
trx_id | trx_state  | trx_rows_modified | sec
123456 | RUNNING    | 2000000           | 1800

[root@db-master ~]# mysql -u root -p -e "KILL 123456;"
[root@db-master ~]# mysql -u root -p -e "SHOW SLAVE STATUS\\G" | grep Seconds_Behind_Master
Seconds_Behind_Master: 5"""

LOG_CORS_ERROR = """[root@web-server ~]# tail -f /var/log/nginx/error.log
2026/07/15 14:20:01 [error] 12345#0: *5678 upstream sent no valid HTTP/1.0 header while reading response header from upstream

[root@web-server ~]# cat /etc/nginx/conf.d/edu.conf | grep -A5 "location /api"
location /api/ {
    proxy_pass http://localhost:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

[root@web-server ~]# curl -H "Origin: https://m.school.edu.cn" -H "Access-Control-Request-Method: GET" -X OPTIONS https://edu.school.edu.cn/api/student/list -I
HTTP/1.1 200 OK
# Missing: Access-Control-Allow-Origin header

[root@web-server ~]# vi /etc/nginx/conf.d/edu.conf
# Added:
# add_header Access-Control-Allow-Origin "https://m.school.edu.cn";
# add_header Access-Control-Allow-Methods "GET,POST,PUT,DELETE,OPTIONS";
# add_header Access-Control-Allow-Headers "Authorization,Content-Type";

[root@web-server ~]# nginx -t && systemctl reload nginx
[root@web-server ~]# curl -H "Origin: https://m.school.edu.cn" -X OPTIONS https://edu.school.edu.cn/api/student/list -I
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://m.school.edu.cn
Access-Control-Allow-Methods: GET,POST,PUT,DELETE,OPTIONS"""

LOG_LOGIN_TIMEOUT = """[root@app-server ~]# tail -f /opt/tomcat/logs/catalina.out | grep -E "ERROR|TIMEOUT"
2026-07-15 09:05:12 ERROR [http-nio-8080-exec-45] jdbc.connection.ConnectionPool - Connection is not available, request timed out after 30000ms
2026-07-15 09:05:13 ERROR [http-nio-8080-exec-46] c.e.c.LoginController - Login failed: Could not open JDBC Connection for transaction

[root@app-server ~]# netstat -an | grep 3306 | grep ESTABLISHED | wc -l
50

[root@app-server ~]# cat /opt/tomcat/conf/application.properties | grep jdbc
spring.datasource.url=jdbc:mysql://localhost:3306/edu_db?useSSL=false
spring.datasource.hikari.maximumPoolSize=50
spring.datasource.hikari.connectionTimeout=30000
spring.datasource.hikari.idleTimeout=600000

[root@app-server ~]# sed -i 's/maximumPoolSize=50/maximumPoolSize=200/' /opt/tomcat/conf/application.properties
[root@app-server ~]# sed -i 's/connectionTimeout=30000/connectionTimeout=60000/' /opt/tomcat/conf/application.properties
[root@app-server ~]# systemctl restart tomcat
[root@app-server ~]# curl -X POST http://localhost:8080/edu/login -d 'username=admin&password=****'
HTTP/1.1 200 OK"""

# ====== 5 条已完成工单 ======
COMPLETED_TICKETS = [
    {
        "title": "教务系统登录页报502错误，全校教师无法访问",
        "category": "系统故障",
        "priority": 1,
        "source": "电话",
        "customer_idx": 0,
        "handler": "engineer",
        "desc": "周一上午8:30，全校教师集中反馈登录教务系统时页面显示502 Bad Gateway，无法正常进入系统。正值期末考试周，教师需紧急录入成绩。影响全校3000余名师生。",
        "raw_log": LOG_NGINX_502,
        "fault_summary": "教务系统登录页返回502 Bad Gateway，nginx服务因端口被旧进程占用无法启动，所有教师均无法登录系统。",
        "root_cause": "服务器重启后旧版nginx_old进程未被正确清理，残留占用80和443端口，导致新版nginx服务启动失败。systemd未检测到旧实例的存在。",
        "solution": "强制终止残留的nginx_old进程（kill -9 1024）释放端口后启动新版nginx服务，并设置开机自启。建议在nginx.service中添加ExecPreStart清理脚本防止复发。",
        "ai_summary": "教务系统因nginx端口被旧进程占用导致502错误。工程师通过netstat定位残留进程，强制终止后重启nginx恢复正常。整个处理过程约15分钟。",
        "suggest_content": """【综合分析】根据故障描述和客户环境（CentOS 7.9 + Nginx），502错误通常源于反向代理异常或后端服务不可用。结合"周一上午集中爆发"，怀疑为周末维护或自动重启导致的服务异常。

【可能原因】
  1. Nginx服务未正常启动或已崩溃
  2. Nginx端口被其他进程占用（常见于服务器重启后旧进程残留）
  3. 后端Tomcat/应用服务不可用导致Nginx返回502
  4. 系统资源耗尽（内存/磁盘）导致服务异常

【建议检查项】
  1. 检查Nginx服务状态
     原因: 502最直接的原因就是nginx服务状态异常
     命令: systemctl status nginx && journalctl -xe -u nginx | tail -30
     预期: Nginx状态异常或日志中有bind/connect错误
  2. 检查端口占用情况
     原因: 端口冲突是nginx启动失败的常见原因
     命令: netstat -tlnp | grep -E ':80|:443'
     预期: 有非nginx进程占用80/443端口
  3. 检查后端应用状态
     原因: 如果nginx正常但后端挂了也会502
     命令: systemctl status tomcat && curl -I http://localhost:8080
     预期: Tomcat服务异常或接口无响应

【参考历史案例】
  1. Nginx端口冲突致502错误（相似度 89%）
  2. 教务系统登录页报502错误-端口占用（相似度 85%）
  3. nginx重启失败-Address already in use（相似度 72%）""",
    },
    {
        "title": "数据库连接池耗尽，教务系统全部页面报错",
        "category": "数据库异常",
        "priority": 1,
        "source": "运维监控",
        "customer_idx": 1,
        "handler": "li_wei",
        "desc": "下午14:30，教务系统监告：所有页面返回'数据库连接失败'。排查发现MySQL连接数达到上限150，大量Sleep连接未释放，持续约30分钟影响全校使用。",
        "raw_log": LOG_DB_CONN,
        "fault_summary": "教务系统所有页面报数据库连接失败错误，MySQL连接数达到上限150，大量空闲Sleep连接未释放。",
        "root_cause": "应用层HikariCP连接池配置过小（maxPoolSize=50），高峰期并发请求超出连接池容量。同时应用代码中部分连接未正确关闭导致连接泄漏，长期积累耗尽MySQL的max_connections=150。",
        "solution": "临时调大MySQL max_connections至500，wait_timeout至300秒自动回收空闲连接。应用层修复连接泄漏的代码缺陷，调大HikariCP maxPoolSize至200。",
        "ai_summary": "数据库连接池耗尽导致教务系统全面瘫痪30分钟。通过调大max_connections+修复应用层连接泄漏解决。建议增加连接数监控告警。",
        "suggest_content": """【综合分析】数据库连接池耗尽是典型的容量规划不足问题。高峰期并发请求超出连接池承载能力，加上可能存在连接泄漏，导致连接数逐步耗尽。需从数据库配置、应用连接池、代码规范三个层面综合解决。

【可能原因】
  1. 数据库连接数上限配置过低（默认150）
  2. 应用连接池配置不足（HikariCP maxPoolSize过小）
  3. 应用代码存在连接泄漏（未正确关闭Connection）
  4. 慢查询导致连接长时间占用

【建议检查项】
  1. 检查MySQL当前连接数和上限
     原因: 确认是否达到连接数上限
     命令: mysql -u root -p -e "SHOW VARIABLES LIKE 'max_connections'; SHOW STATUS LIKE 'Threads_connected';"
     预期: Threads_connected接近或等于max_connections
  2. 检查应用连接池配置
     原因: 连接池配置直接影响并发能力
     命令: grep -A10 'hikari\|datasource\|pool' /opt/tomcat/conf/application.properties
     预期: maximumPoolSize偏小（如≤50），connectionTimeout偏短
  3. 分析连接来源和状态
     原因: 区分是正常业务增长还是连接泄漏
     命令: mysql -u root -p -e "SELECT user, host, db, command, time, state FROM information_schema.PROCESSLIST WHERE command != 'Sleep';"
     预期: 大量长时间Sleep连接→说明连接未释放

【参考历史案例】
  1. 数据库连接池耗尽-高峰期服务不可用（相似度 91%）
  2. MySQL Too many connections-教务系统故障（相似度 78%）""",
    },
    {
        "title": "服务器磁盘空间耗尽，应用日志报错No space left",
        "category": "系统故障",
        "priority": 1,
        "source": "运维监控",
        "customer_idx": 2,
        "handler": "wang_fang",
        "desc": "教务系统突然无法登录，后端日志提示'No space left on device'。检查发现系统盘使用率100%，nginx和tomcat历史日志占用了大量磁盘空间。",
        "raw_log": LOG_DISK_FULL,
        "fault_summary": "服务器系统盘使用率100%导致教务系统无法写入任何文件，应用报'No space left on device'错误。",
        "root_cause": "nginx和tomcat的访问日志未配置自动轮转和清理策略，历史日志文件持续增长占用45GB和28GB。日志轮转缺失导致磁盘空间逐步耗尽。",
        "solution": "清理nginx和tomcat历史日志释放49GB空间，配置logrotate每日自动轮转（保留7天+压缩）。设置磁盘使用率>85%的监控告警。",
        "ai_summary": "系统盘100%使用率导致应用无法写入，通过清理历史日志+配置logrotate解决。建议所有生产服务器标配磁盘监控告警。",
        "suggest_content": """【综合分析】系统盘100%使用率是运维基础监控缺失的典型表现。通常由日志文件持续增长且无自动清理策略引起。需先紧急清理释放空间恢复服务，再建立长效的日志管理机制。

【可能原因】
  1. Nginx/Tomcat访问日志未配置轮转策略导致持续增长
  2. 系统journal日志过大
  3. 临时文件/tmp目录未清理
  4. Core dump文件占用空间

【建议检查项】
  1. 检查磁盘使用情况
     原因: 快速定位占用空间的目录
     命令: df -h && du -sh /var/log/* /tmp/* /opt/* | sort -rh | head -10
     预期: /var/log目录占用远大于正常水平
  2. 检查日志文件大小
     原因: 确认是否需要保留旧日志
     命令: ls -lhS /var/log/nginx/ | head -10
     预期: 存在GB级别的旧日志文件
  3. 检查是否有未压缩的大文件
     原因: 日志轮转但未压缩同样会快速占满磁盘
     命令: find /var/log -type f -size +100M -exec ls -lh {} \;
     预期: 找到可清理或压缩的大文件

【参考历史案例】
  1. 磁盘空间耗尽-nginx日志文件过大（相似度 93%）
  2. No space left on device-应用无法写入（相似度 80%）""",
    },
    {
        "title": "Redis内存溢出导致教务缓存全部失效",
        "category": "数据库异常",
        "priority": 1,
        "source": "运维监控",
        "customer_idx": 1,
        "handler": "engineer",
        "desc": "Redis突然OOM重启，所有Session和业务缓存丢失。用户被迫重新登录，高峰期数据库压力陡增，部分页面响应缓慢。影响时段：14:30-15:00。",
        "raw_log": LOG_REDIS_OOM,
        "fault_summary": "Redis服务因内存耗尽触发OOM自动重启，所有缓存数据丢失，导致用户Session失效需要重新登录，数据库瞬时压力剧增。",
        "root_cause": "Redis maxmemory配置为4GB且淘汰策略为noeviction（不淘汰），当数据量超过4GB后禁止写入，最终触发OOM。业务高峰期缓存写入量激增是诱因。",
        "solution": "将Redis内存扩展至8GB，淘汰策略改为allkeys-lru，确保内存满时可淘汰最久未使用的key而非直接拒绝写入。配置Sentinel高可用防止单点故障。",
        "ai_summary": "Redis OOM重启导致缓存全量丢失。通过扩容内存+修改淘汰策略+部署Sentinel解决，建议同时增加Redis内存使用率监控。",
        "suggest_content": """【综合分析】Redis内存耗尽通常由两因素共同导致：内存配置不足 + 淘汰策略不当。noeviction策略下内存满后所有写操作被拒绝，堆积累的数据最终触发OOM。需从容量规划和淘汰策略两方面入手。

【可能原因】
  1. Redis内存配置不足（4GB对百万级key不够）
  2. 淘汰策略为noeviction导致内存满后无法写入
  3. 未设置过期时间的key积压
  4. 大key/bigkey占用异常内存

【建议检查项】
  1. 检查Redis内存使用和配置
     原因: 了解当前内存使用状态和上限
     命令: redis-cli INFO memory | grep -E 'used_memory_human|maxmemory_human|maxmemory_policy'
     预期: used_memory接近或等于maxmemory，policy为noeviction
  2. 检查key数量和过期策略
     原因: 确认是否存在大量无过期时间的key
     命令: redis-cli INFO keyspace && redis-cli --bigkeys
     预期: keys数量异常大且无expire标记
  3. 检查内存碎片率
     原因: 高碎片率可能导致实际内存占用高于预期
     命令: redis-cli INFO memory | grep mem_fragmentation_ratio
     预期: 碎片率>1.5说明内存利用率低

【参考历史案例】
  1. Redis OOM重启-缓存雪崩导致DB压力（相似度 88%）
  2. Redis内存100%-淘汰策略配置问题（相似度 75%）""",
    },
    {
        "title": "学校官网SSL证书过期，浏览器提示不安全",
        "category": "配置错误",
        "priority": 2,
        "source": "微信",
        "customer_idx": 3,
        "handler": "zhao_qiang",
        "desc": "多位家长通过微信反映，访问学校官网时浏览器提示「您的连接不是私密连接」，影响学校形象和招生宣传。证书过期已3天。",
        "raw_log": LOG_CERT_EXPIRE,
        "fault_summary": "学校官网SSL证书于7月1日过期，浏览器提示连接不安全，家长无法正常访问官网。",
        "root_cause": "SSL证书由Let's Encrypt签发，有效期90天。服务器未配置certbot自动续期定时任务，运维团队未收到证书到期提醒，导致证书过期后未及时更新。",
        "solution": "使用certbot重新签发SSL证书并替换nginx中的旧证书，配置crontab每月自动续期。设置证书到期前30天企业微信提醒。",
        "ai_summary": "SSL证书过期导致官网无法访问。重新签发证书后恢复，并配置自动续期+到期告警防止复发。",
        "suggest_content": """【综合分析】SSL证书过期是运维中最常见但又最容易忽略的问题。Let's Encrypt证书每90天过期，如果没有设置自动续期和到期提醒，很容易在过期后才发现。处理相对简单：要么续期要么重新签发。

【可能原因】
  1. Certbot自动续期crontab未配置或失效
  2. 证书签发时未设置自动续期
  3. 证书到期通知发送到了已离职员工的邮箱
  4. 域名DNS解析变化导致自动续期失败

【建议检查项】
  1. 检查证书过期时间
     原因: 确认证书是否确实过期
     命令: openssl x509 -enddate -noout -in /etc/nginx/ssl/school.crt
     预期: 证书已过期
  2. 检查certbot定时任务
     原因: 确认自动续期是否正常配置
     命令: crontab -l | grep certbot
     预期: 没有certbot相关定时任务
  3. 手动续期测试
     原因: 验证certbot能否正常工作
     命令: certbot renew --dry-run
     预期: 可能报域名验证失败或其他错误

【参考历史案例】
  1. SSL证书过期-Let's Encrypt续期失败（相似度 95%）
  2. 微信小程序接口证书到期-排查记录（相似度 70%）""",
    },
]

# ====== 15 条新建工单（含完整日志） ======
NEW_TICKETS = [
    {
        "title": "教务系统工作日高峰期响应缓慢，页面加载超5秒",
        "category": "系统故障",
        "priority": 1,
        "source": "电话",
        "customer_idx": 0,
        "desc": "近一周工作日上午9:00-11:00，教务系统平均响应时间从200ms上升至3-5秒。教师反馈录入成绩、查看课表等核心功能加载缓慢，严重时页面超时。非高峰期正常。",
        "raw_log": LOG_SLOW_SQL,
    },
    {
        "title": "期末成绩导入Excel功能报Java堆内存溢出",
        "category": "功能BUG",
        "priority": 1,
        "source": "钉钉",
        "customer_idx": 4,
        "desc": "教师批量导入期末考试Excel成绩表时，系统报'java.lang.OutOfMemoryError: Java heap space'。单次导入文件包含3000+学生记录。急需导入完成成绩录入。",
        "raw_log": LOG_TOMCAT_OOM,
    },
    {
        "title": "校园网络教学楼区域频繁断网，影响智慧课堂",
        "category": "网络异常",
        "priority": 1,
        "source": "电话",
        "customer_idx": 5,
        "desc": "教学楼A栋3-5层近期频繁出现网络中断（每天3-5次），每次持续1-3分钟自动恢复。1-2层和B栋网络正常。直接影响智慧课堂一体机的在线教学功能。",
        "raw_log": LOG_NETWORK_LOSS,
    },
    {
        "title": "K8s集群教务API Pod反复重启CrashLoopBackOff",
        "category": "配置错误",
        "priority": 1,
        "source": "运维监控",
        "customer_idx": 6,
        "desc": "K8s监控告警：edu-system命名空间下1个API Pod处于CrashLoopBackOff状态已持续2小时，重启次数超过15次。其余2个Pod正常运行，服务未完全中断但有单点风险。",
        "raw_log": LOG_K8S_POD_CRASH,
    },
    {
        "title": "MySQL主从复制延迟超过30分钟，从库数据滞后",
        "category": "数据库异常",
        "priority": 2,
        "source": "运维监控",
        "customer_idx": 1,
        "desc": "MySQL主从监控告警：Seconds_Behind_Master达到1800秒（30分钟）。从库数据严重滞后影响报表查询和只读接口的准确性。业务侧暂时切到主库查询但增加主库压力。",
        "raw_log": LOG_MYSQL_REPLICATION,
    },
    {
        "title": "移动端H5页面跨域请求被拦截，接口调用全部失败",
        "category": "配置错误",
        "priority": 2,
        "source": "钉钉",
        "customer_idx": 8,
        "desc": "新上线的移动端H5家长端页面（部署在m.school.edu.cn）调用教务系统API时全部失败。浏览器控制台报CORS错误：'Access-Control-Allow-Origin' header missing。",
        "raw_log": LOG_CORS_ERROR,
    },
    {
        "title": "教师考勤打卡定位偏差约500米，部分老师无法打卡",
        "category": "功能BUG",
        "priority": 2,
        "source": "微信",
        "customer_idx": 9,
        "desc": "新安装的校园考勤系统，教学楼B栋一层办公室6位老师反映GPS定位偏差约500米，钉钉显示定位在学校外，无法完成考勤打卡。其他区域正常。",
        "raw_log": """[root@app-server ~]# tail -100 /opt/attendance/logs/app.log | grep -E "GPS|location|error"
2026-07-15 08:05:01 INFO [AttendanceService] GPS location: lat=30.6512, lng=104.0823 (within campus range: YES)
2026-07-15 08:05:12 WARN [AttendanceService] GPS location: lat=30.6578, lng=104.0819 (within campus range: NO, distance=512m)
2026-07-15 08:05:23 INFO [AttendanceService] GPS location: lat=30.6514, lng=104.0820 (within campus range: YES)

[root@app-server ~]# cat /opt/attendance/conf/config.properties | grep -E "gps|location|range"
attendance.gps.campus.center=30.6530,104.0820
attendance.gps.campus.range=300
attendance.gps.allowedDeviation=500

[root@app-server ~]# grep "B栋" /opt/attendance/logs/app.log | grep "GPS" | head -5
B栋-101: avg GPS drift = 520m (max 650m)
B栋-102: avg GPS drift = 505m (max 620m)
B栋-103: avg GPS drift = 530m (max 680m)
B栋-104: avg GPS drift = 510m (max 640m)""",
    },
    {
        "title": "学生请假审批流程卡在年级组长节点无法流转",
        "category": "功能BUG",
        "priority": 2,
        "source": "电话",
        "customer_idx": 0,
        "desc": "高二(5)班学生提交请假申请，班主任已审批通过，但流程在年级组长节点无法继续。年级组长登录后审批按钮为灰色不可点击状态。涉及其余3名学生也遇到同样问题。",
        "raw_log": """[root@app-server ~]# tail -50 /opt/tomcat/logs/catalina.out | grep -E "workflow|approval|ERROR"
2026-07-15 09:30:05 ERROR [http-nio-8080-exec-12] c.e.w.WorkflowService - 审批人校验失败
2026-07-15 09:30:05 ERROR [http-nio-8080-exec-12] c.e.w.WorkflowService - userId=105(年级组长-赵老师) 权限缓存未命中
2026-07-15 09:30:05 ERROR [http-nio-8080-exec-12] c.e.w.WorkflowService - 缓存中角色: ROLE_TEACHER, 需要角色: ROLE_GRADE_LEADER

[root@app-server ~]# redis-cli GET "user:105:role"
"ROLE_TEACHER"

[root@app-server ~]# mysql -u root -p edu_db -e "SELECT id, real_name, role_id, grade_leader_for FROM sys_user WHERE id=105;"
id | real_name | role_id | grade_leader_for
105 | 赵老师    | 3       | 高二年级

[root@app-server ~]# redis-cli DEL "user:105:role"
[root@app-server ~]# redis-cli SET "user:105:role" "ROLE_GRADE_LEADER"
OK""",
    },
    {
        "title": "校园广播系统定时播放任务全部丢失",
        "category": "系统故障",
        "priority": 2,
        "source": "电话",
        "customer_idx": 7,
        "desc": "本周一升旗仪式铃声未按时播放。检查广播系统后发现所有定时任务（上课铃、下课铃、眼保健操、午休音乐）全部丢失，需要紧急恢复。",
        "raw_log": """[root@broadcast-server ~]# systemctl status broadcast
● broadcast.service - Campus Broadcast System
   Active: active (running) since Mon 2026-07-14 03:15:00 CST

[root@broadcast-server ~]# mysql -u root -p broadcast_db -e "SELECT COUNT(*) FROM schedule;"
COUNT(*)
0

[root@broadcast-server ~]# mysql -u root -p broadcast_db -e "SELECT * FROM schedule_backup;"
id | name          | time     | audio_file          | days       | enabled
1  | 早自习预备铃   | 07:50:00 | bell_pre.mp3        | Mon-Fri    | 1
2  | 第一节课上课   | 08:00:00 | bell_class_start.mp3 | Mon-Fri    | 1
3  | 第一节课下课   | 08:45:00 | bell_class_end.mp3   | Mon-Fri    | 1
...
24 | 午休音乐      | 12:30:00 | music_noon.mp3      | Mon-Fri    | 1

[root@broadcast-server ~]# mysql -u root -p broadcast_db -e "INSERT INTO schedule SELECT * FROM schedule_backup;"
Query OK, 24 rows affected

[root@broadcast-server ~]# systemctl restart broadcast""",
    },
    {
        "title": "在线考试系统防作弊切屏检测功能失效",
        "category": "功能BUG",
        "priority": 2,
        "source": "邮件",
        "customer_idx": 5,
        "desc": "期中在线考试期间，监考教师反映防作弊功能的切屏检测未触发——学生在考试中可以自由切换浏览器标签页查阅资料，系统未记录任何违规行为。",
        "raw_log": """[root@app-server ~]# tail -50 /opt/tomcat/logs/catalina.out | grep -E "cheat|visibility|blur"
2026-07-15 10:00:01 WARN [ExamMonitor] document.visibilityState change not detected for student #4521
2026-07-15 10:00:05 WARN [ExamMonitor] document.visibilityState change not detected for student #4533
2026-07-15 10:01:12 WARN [ExamMonitor] document.visibilityState change not detected for student #4589

[root@app-server ~]# cat /opt/tomcat/webapps/exam/js/anti-cheat.js | grep -A5 "visibilitychange"
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    reportViolation('tab_switch');
  }
});

[root@app-server ~]# chromium --version
Chromium 128.0.6613.36

# visibilitychange事件在Chromium 127+中的行为变更说明:
# 当用户使用Alt+Tab切换窗口时，document.hidden状态更新延迟>500ms
# 导致部分切换行为未被捕获

[root@app-server ~]# vi /opt/tomcat/webapps/exam/js/anti-cheat.js
# 增加 window.addEventListener('blur', ...) 作为补充检测
# 增加 requestAnimationFrame 轮询 document.hidden 状态""",
    },
    {
        "title": "校车GPS定位设备全部离线，家长APP无法查看位置",
        "category": "网络异常",
        "priority": 1,
        "source": "电话",
        "customer_idx": 3,
        "desc": "下午15:30放学时段，家长集中反馈APP无法查看校车实时位置。排查发现全部12辆校车的GPS设备均处于离线状态，最后上报时间均为14:52。",
        "raw_log": """[root@gps-server ~]# systemctl status gps-gateway
● gps-gateway.service - GPS Data Gateway
   Active: active (running) since Wed 2026-07-09 08:00:00 CST

[root@gps-server ~]# tail -30 /var/log/gps-gateway/app.log
2026-07-15 14:52:01 INFO  [TCP-Server] Device BUS-001 heartbeat timeout (120s)
2026-07-15 14:52:02 INFO  [TCP-Server] Device BUS-002 heartbeat timeout (120s)
2026-07-15 14:52:03 INFO  [TCP-Server] Device BUS-003 heartbeat timeout (120s)
...
2026-07-15 14:52:12 INFO  [TCP-Server] All 12 devices disconnected

[root@gps-server ~]# ping 10.0.100.1  # GPS网关IP
PING 10.0.100.1 56(84) bytes of data.
# no response

[root@gps-server ~]# traceroute 10.0.100.1
 1  10.0.0.1 (0.5ms)
 2  * * *
 3  * * *

[root@gps-server ~]# ssh switch-room
switch-room# show interface vlan 100
Vlan100 is down, line protocol is down""",
    },
    {
        "title": "图书管理系统扫码枪突然全部无法识别",
        "category": "系统故障",
        "priority": 3,
        "source": "电话",
        "customer_idx": 2,
        "desc": "图书馆3台USB扫码枪同时无法连接管理系统。系统提示'设备未识别'，重新插拔USB线、更换USB口均无效。借还书业务只能手动输入条码，效率低下。",
        "raw_log": """[root@library-server ~]# lsusb | grep -i scanner
Bus 001 Device 005: ID 05e0:1200 Symbol Technologies Barcode Scanner
Bus 001 Device 006: ID 05e0:1200 Symbol Technologies Barcode Scanner
Bus 001 Device 007: ID 05e0:1200 Symbol Technologies Barcode Scanner

[root@library-server ~]# dmesg | tail -20 | grep -E "usb|scanner|error"
[12345.678] usb 1-3: reset high-speed USB device number 5
[12345.789] usb 1-3: device descriptor read/64, error -71
[12346.012] usb 1-5: reset high-speed USB device number 6
[12346.123] usb 1-5: device descriptor read/64, error -71
[12346.234] usb 1-7: reset high-speed USB device number 7
[12346.345] usb 1-7: device descriptor read/64, error -71

[root@library-server ~]# uname -r
3.10.0-1127.el7.x86_64

[root@library-server ~]# ls -la /dev/input/by-id/ | grep scanner
# 设备文件不存在 - 驱动未能正确加载

[root@library-server ~]# cat /etc/yum.repos.d/kernel.repo
# 内核版本过旧，USB驱动对新设备的兼容性问题""",
    },
    {
        "title": "教师职称评审系统PDF附件上传99%卡死",
        "category": "功能BUG",
        "priority": 2,
        "source": "微信",
        "customer_idx": 4,
        "desc": "教师申报高级职称时需要上传PDF证明材料（论文、获奖证书扫描件等），多位教师反馈上传进度卡在99%后报错'上传失败，请重试'。文件大小均在5-15MB之间。",
        "raw_log": """[root@app-server ~]# tail -20 /var/log/nginx/error.log
2026/07/15 15:10:01 [error] 12345#0: *1234 client intended to send too large body: 15728640 bytes

[root@app-server ~]# cat /etc/nginx/conf.d/edu.conf | grep client_max_body_size
client_max_body_size 10m;

[root@app-server ~]# tail -20 /opt/tomcat/logs/catalina.out | grep -E "upload|multipart|filesize"
2026-07-15 15:10:05 ERROR [FileUpload] MultipartFile size 14.5MB exceeds limit of 10MB
2026-07-15 15:10:05 ERROR [FileUpload] Upload failed: org.springframework.web.multipart.MaxUploadSizeExceededException

[root@app-server ~]# cat /opt/tomcat/conf/application.properties | grep multipart
spring.servlet.multipart.max-file-size=10MB
spring.servlet.multipart.max-request-size=20MB

[root@app-server ~]# ls -la /data/uploads/tmp/ | wc -l
587

# 大量半截上传的临时文件未清理
[root@app-server ~]# du -sh /data/uploads/tmp/
2.3G    /data/uploads/tmp/""",
    },
    {
        "title": "体育馆LED大屏应急预案内容无法更新",
        "category": "操作咨询",
        "priority": 3,
        "source": "微信",
        "customer_idx": 0,
        "desc": "体育馆管理处咨询如何更换LED大屏上的校园安全应急预案展示内容。当前显示的旧版本信息（2024年版）已过期，需要展示2026年最新版应急预案。",
        "raw_log": """[root@led-server ~]# systemctl status led-display
● led-display.service - LED Display Controller
   Active: active (running) since Jan 2026

[root@led-server ~]# cat /opt/led-display/config.ini
[DISPLAY]
screen_width=1920
screen_height=1080
content_path=/opt/led-display/content/emergency_plan_v2024.html
update_interval=3600
update_source=manual

[root@led-server ~]# ls /opt/led-display/content/
emergency_plan_v2024.html
emergency_plan_v2026.html  # 新文件已准备好但未修改配置引用

[root@led-server ~]# cat /opt/led-display/content/emergency_plan_v2024.html | head -5
<title>校园安全应急预案 (2024年3月修订版)</title>

[root@led-server ~]# cat /opt/led-display/content/emergency_plan_v2026.html | head -5
<title>校园安全应急预案 (2026年7月修订版)</title>

# 问题确认: config.ini中content_path仍指向v2024版本
[root@led-server ~]# sed -i 's/emergency_plan_v2024.html/emergency_plan_v2026.html/' /opt/led-display/config.ini
[root@led-server ~]# systemctl restart led-display""",
    },
    {
        "title": "学生宿舍水电费计费系统显示用电量异常偏高",
        "category": "功能BUG",
        "priority": 3,
        "source": "电话",
        "customer_idx": 9,
        "desc": "多名学生反映本月(7月)水电费账单金额异常偏高。某宿舍（4人间）显示月用电量达850度，而该宿舍上月仅85度，且同楼层其他宿舍用电量也普遍翻了5-10倍。",
        "raw_log": """[root@billing-server ~]# mysql -u root -p billing_db -e "SELECT dorm_id, month, elec_kwh, water_ton FROM bills WHERE month='202607' AND dorm_id IN (301,302,303,304,305) ORDER BY dorm_id;"
dorm_id | month  | elec_kwh | water_ton
301     | 202607 | 850      | 15
302     | 202607 | 720      | 12
303     | 202607 | 680      | 10
304     | 202607 | 45       | 3
305     | 202607 | 50       | 4

[root@billing-server ~]# mysql -u root -p billing_db -e "SELECT dorm_id, month, elec_kwh FROM bills WHERE month='202606' AND dorm_id IN (301,302,303);"
dorm_id | month  | elec_kwh
301     | 202606 | 85
302     | 202606 | 78
303     | 202606 | 92

[root@billing-server ~]# mysql -u root -p billing_db -e "SELECT dorm_id, meter_id FROM meters WHERE dorm_id IN (301,302,303,304,305);"
dorm_id | meter_id
301     | MTR-301
302     | MTR-302
303     | MTR-303
304     | MTR-304
305     | MTR-305

[root@billing-server ~]# tail -30 /var/log/billing/meter-collector.log | grep -E "MTR-301|MTR-302|MTR-303"
2026-07-01 00:05:01 INFO [Collector] MTR-301 reading: 15000 -> THIS MONTH: 750 (calc base: 14250)
2026-07-01 00:05:02 INFO [Collector] MTR-302 reading: 28000 -> THIS MONTH: 650 (calc base: 27350)
2026-07-01 00:05:03 INFO [Collector] MTR-303 reading: 42000 -> THIS MONTH: 600 (calc base: 41400)

# 问题: 月初读数基准值(calc base)远低于上月表底读数!
# 上月表底应为: MTR-301=14915, 但calc base=14250（差了665度）
[root@billing-server ~]# mysql -u root -p billing_db -e "SELECT meter_id, reading, read_time FROM meter_readings WHERE read_time LIKE '2026-06-30%' AND meter_id IN ('MTR-301','MTR-302','MTR-303');"
meter_id | reading | read_time
MTR-301  | 14915   | 2026-06-30 23:55
MTR-302  | 27922   | 2026-06-30 23:55
MTR-303  | 41308   | 2026-06-30 23:55""",
    },
]

# ─────────── 工单编号生成 ───────────
ticket_counter = [0]

def make_ticket_no(day_offset):
    dt = datetime(2026, 7, 15) + timedelta(days=day_offset)
    ticket_counter[0] += 1
    return f"WO{dt.strftime('%Y%m%d')}{ticket_counter[0]:03d}"


# ============================================================
# 4a. 生成 5 条已完成工单（完整生命周期）
# ============================================================
completed_ids = []
for i, tpl in enumerate(COMPLETED_TICKETS):
    customer_idx = tpl["customer_idx"]
    handler_id = user_ids[tpl["handler"]]
    create_dt = base_date + timedelta(days=i * 2, hours=random.randint(0, 3))
    start_dt = create_dt + timedelta(hours=1)
    parse_dt = start_dt + timedelta(hours=2)
    suggest_dt = create_dt + timedelta(minutes=30)  # 排查建议在创建后不久
    generate_dt = parse_dt + timedelta(hours=1)
    finish_dt = generate_dt + timedelta(hours=2)
    duration = int((finish_dt - start_dt).total_seconds() / 60)

    ticket = Ticket(
        ticket_no=make_ticket_no(i),
        title=tpl["title"],
        customer_id=customer_ids[customer_idx],
        category=tpl["category"],
        priority=tpl["priority"],
        status=4,
        source=tpl["source"],
        description=tpl["desc"],
        fault_summary=tpl["fault_summary"],
        root_cause=tpl["root_cause"],
        solution=tpl["solution"],
        ai_summary=tpl["ai_summary"],
        raw_log=tpl["raw_log"],
        handler_id=handler_id,
        start_time=start_dt,
        finish_time=finish_dt,
        duration=duration,
        create_time=create_dt,
        update_time=finish_dt,
        knowledge_id=ticket_counter[0],  # 模拟知识库关联
    )
    db.add(ticket)
    db.flush()
    completed_ids.append(ticket.id)

    # -- 时间线: 创建 --
    db.add(TicketTimeline(
        ticket_id=ticket.id, node_time=create_dt,
        node_type="创建", title=f"工单创建 — {tpl['category']}",
        content=f"来源：{tpl['source']}\n{tpl['desc'][:200]}",
        operator=str(admin_id),
    ))

    # -- 时间线: Agent 排查建议 --
    db.add(TicketTimeline(
        ticket_id=ticket.id, node_time=suggest_dt,
        node_type="Agent建议", title="🤖 AI 排查方向建议",
        content=tpl["suggest_content"],
        operator=str(handler_id), ai_generated=True,
    ))

    # -- 时间线: 受理 --
    db.add(TicketTimeline(
        ticket_id=ticket.id, node_time=start_dt,
        node_type="受理", title="工程师受理 — 开始排查",
        content="接到工单后开始排查处理。参考AI排查建议，根据实际日志情况逐步确认故障根因。",
        operator=str(handler_id),
    ))

    # -- 时间线: Agent 日志解析结果 --
    db.add(TicketTimeline(
        ticket_id=ticket.id, node_time=parse_dt,
        node_type="Agent解析", title="🤖 AI 日志解析 — 结构化时间线",
        content="日志解析完成，识别到关键操作步骤并生成结构化时间线。详见工单详情中的AI分析结果。",
        operator=str(handler_id), ai_generated=True,
    ))

    # -- 时间线: 生成工单内容 --
    db.add(TicketTimeline(
        ticket_id=ticket.id, node_time=generate_dt,
        node_type="Agent生成", title="🤖 AI 自动生成工单内容",
        content=f"AI已根据操作日志和时间线自动生成工单内容：\n故障现象：{tpl['fault_summary']}\n根因分析：{tpl['root_cause']}\n解决方案：{tpl['solution']}",
        operator=str(handler_id), ai_generated=True,
    ))

    # -- 时间线: 完成 --
    db.add(TicketTimeline(
        ticket_id=ticket.id, node_time=finish_dt,
        node_type="完成", title="处理完成 — 问题已解决",
        content=tpl["solution"][:500],
        operator=str(handler_id),
    ))

    if i % 2 == 0:
        db.commit()

db.commit()
print(f"      5 条已完成工单（含完整时间线: 创建/建议/受理/解析/生成/完成）")


# ============================================================
# 4b. 生成 15 条新建工单（含基本信息 + 完整日志）
# ============================================================
new_ticket_data = []  # 用于导出到 txt

for i, tpl in enumerate(NEW_TICKETS):
    customer_idx = tpl["customer_idx"]
    create_dt = base_date + timedelta(days=i, hours=random.randint(8, 16))

    ticket = Ticket(
        ticket_no=make_ticket_no(5 + i),
        title=tpl["title"],
        customer_id=customer_ids[customer_idx],
        category=tpl["category"],
        priority=tpl["priority"],
        status=1,
        source=tpl["source"],
        description=tpl["desc"],
        raw_log=tpl["raw_log"],
        create_time=create_dt,
        update_time=create_dt,
    )
    db.add(ticket)
    db.flush()

    # 仅创建节点
    db.add(TicketTimeline(
        ticket_id=ticket.id, node_time=create_dt,
        node_type="创建", title=f"工单创建 — {tpl['category']}",
        content=f"来源：{tpl['source']}\n{tpl['desc'][:200]}",
        operator=str(admin_id),
    ))

    new_ticket_data.append({
        "ticket_no": ticket.ticket_no,
        "title": tpl["title"],
        "category": tpl["category"],
        "priority": tpl["priority"],
        "raw_log": tpl["raw_log"],
    })

    if i % 5 == 0:
        db.commit()

db.commit()
print(f"      15 条新建工单（含完整操作日志 + 时间线创建节点）")

# ============================================================
# 5. 导出调试日志到 data/debug_logs.txt
# ============================================================
print("\n[5/5] 导出调试日志到 data/debug_logs.txt ...")

data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(data_dir, exist_ok=True)
log_path = os.path.join(data_dir, "debug_logs.txt")

with open(log_path, "w", encoding="utf-8") as f:
    f.write("=" * 70 + "\n")
    f.write("  轻量化售后工单系统 — 调试日志\n")
    f.write("  用途: 复制日志内容到工单详情页「操作日志」输入框\n")
    f.write("       然后点击「AI解析并生成工单」测试完整流程\n")
    f.write(f"  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"  共 {len(new_ticket_data)} 条日志\n")
    f.write("=" * 70 + "\n\n")

    for i, td in enumerate(new_ticket_data, 1):
        f.write("=" * 70 + "\n")
        f.write(f"【{i:02d}】{td['ticket_no']} | {td['category']} | 优先级:{td['priority']}\n")
        f.write(f"标题：{td['title']}\n")
        f.write("=" * 70 + "\n\n")
        f.write(td['raw_log'])
        f.write("\n\n")

print(f"      已导出 → {os.path.abspath(log_path)}")

# ============================================================
# 6. 统计输出
# ============================================================
total = db.query(Ticket).count()
done = db.query(Ticket).filter(Ticket.status == 4).count()
new = db.query(Ticket).filter(Ticket.status == 1).count()
timeline_count = db.query(TicketTimeline).count()
has_log = db.query(Ticket).filter(Ticket.raw_log.isnot(None), Ticket.raw_log != "").count()
has_ai = db.query(Ticket).filter(Ticket.ai_summary.isnot(None), Ticket.ai_summary != "").count()

print("\n" + "=" * 60)
print("  数据重构完成！")
print("=" * 60)
print(f"  用户: {db.query(User).count()} 人")
print(f"  客户: {db.query(Customer).count()} 所")
print(f"  工单: {total} 条")
print(f"    ├─ 已完成(status=4): {done} 条 (含完整AI内容+时间线)")
print(f"    └─ 新建(status=1):   {new} 条 (含完整操作日志)")
print(f"  时间线条目: {timeline_count} 条")
print(f"  含操作日志的工单: {has_log}/{total}")
print(f"  含AI生成内容的工单: {has_ai}/{total}")
print(f"\n  登录账号:")
print(f"    admin    / admin123    (系统管理员)")
print(f"    engineer / engineer123 (售后工程师-张工)")
print(f"    li_wei   / 123456      (售后工程师-李伟)")
print(f"    wang_fang / 123456     (售后工程师-王芳)")
print(f"    zhao_qiang / 123456    (运维管理员-赵强)")
print(f"\n  调试日志: {os.path.abspath(log_path)}")
print(f"  数据库:   {os.path.join(os.path.dirname(__file__), '..', 'data', 'work_order.db')}")

db.close()
