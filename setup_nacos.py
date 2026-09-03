import urllib.request
import urllib.parse
import json

NACOS_URL = "http://127.0.0.1:8848"

# Login
login_data = urllib.parse.urlencode({"username": "nacos", "password": "nacos"}).encode()
req = urllib.request.Request(f"{NACOS_URL}/nacos/v1/auth/login", data=login_data, method="POST")
resp = urllib.request.urlopen(req)
token = json.loads(resp.read())["accessToken"]
print(f"Token obtained: {token[:20]}...")

configs = {
    "yzy-demo.yml": """# Nacos config for yzy-demo
test:
  message: "Hello from Nacos Config Center - yzy-demo"

spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/YZY_DB?characterEncoding=utf8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC
    username: YZY_MASTER
    password: yzy@1234
    driver-class-name: com.mysql.cj.jdbc.Driver
""",
    "yzy-gateway.yml": """# Nacos config for yzy-gateway
test:
  message: "Hello from Nacos Config Center - yzy-gateway"

spring:
  cloud:
    gateway:
      routes:
        - id: yzy-b-demo-route
          uri: lb://yzy-b-demo
          predicates:
            - Path=/api/b/**
          filters:
            - StripPrefix=0
      discovery:
        locator:
          enabled: true
""",
    "yzy-b-demo.yml": """# Nacos config for yzy-b-demo
test:
  message: "Hello from Nacos Config Center - yzy-b-demo"

spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/YZY_DB?characterEncoding=utf8&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC
    username: YZY_MASTER
    password: yzy@1234
    driver-class-name: com.mysql.cj.jdbc.Driver
"""
}

for data_id, content in configs.items():
    data = urllib.parse.urlencode({
        "dataId": data_id,
        "group": "DEFAULT_GROUP",
        "content": content,
        "type": "yaml",
        "accessToken": token
    }).encode()
    req = urllib.request.Request(f"{NACOS_URL}/nacos/v1/cs/configs", data=data, method="POST")
    resp = urllib.request.urlopen(req)
    result = resp.read().decode()
    print(f"Create {data_id}: {result}")

print("=== Nacos configs created ===")
