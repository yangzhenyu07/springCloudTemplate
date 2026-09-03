import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='YZY_MASTER', password='yzy@1234', charset='utf8mb4')
cur = conn.cursor()

cur.execute('CREATE DATABASE IF NOT EXISTS YZY_DB DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci')
conn.commit()
cur.execute('USE YZY_DB')

cur.execute("""
CREATE TABLE IF NOT EXISTS sys_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    status TINYINT DEFAULT 1,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

cur.execute('DELETE FROM sys_user')
cur.execute("INSERT INTO sys_user (username, email, phone, status) VALUES ('admin', 'admin@yzy.com', '13800138000', 1)")
cur.execute("INSERT INTO sys_user (username, email, phone, status) VALUES ('zhangsan', 'zhangsan@yzy.com', '13900139000', 1)")
cur.execute("INSERT INTO sys_user (username, email, phone, status) VALUES ('lisi', 'lisi@yzy.com', '13700137000', 0)")
conn.commit()

cur.execute('SELECT id, username, email, phone, status FROM sys_user')
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
print('=== DB setup done ===')
