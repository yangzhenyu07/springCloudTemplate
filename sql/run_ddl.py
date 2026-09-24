import sys

import pymysql

SQL_FILE = r'E:\work\springCloudTemplate\sql\trade_idempotent.sql'

with open(SQL_FILE, 'r', encoding='utf-8') as f:
    raw = f.read()

# 去掉注释行，按分号拆分语句
statements = []
buf = []
for line in raw.splitlines():
    if line.strip().startswith('--') or line.strip() == '':
        continue
    buf.append(line)
    if line.rstrip().endswith(';'):
        statements.append('\n'.join(buf))
        buf = []

conn = pymysql.connect(host='127.0.0.1', port=3306, user='YZY_MASTER', password='yzy@1234',
                       charset='utf8mb4', autocommit=True)
cur = conn.cursor()
for sql in statements:
    cur.execute(sql)
cur.execute('SHOW TABLES LIKE %s', ('trade%',))
print('tables:', cur.fetchall())
cur.execute('SHOW INDEX FROM trade_message_flow WHERE Key_name="uk_idem_key"')
print('uk_idem_key:', cur.fetchall())
cur.close()
conn.close()
print('=== DDL done ===')
sys.exit(0)
