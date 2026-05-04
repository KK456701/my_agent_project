"""
🏗️ Demo 示例代码 — 用于演示多智能体辩论式审查

这段代码故意包含了几类问题，供不同 Agent 发现和辩论：
- 安全: SQL 注入
- 性能: N+1 查询
- 架构: 职责不清晰

⚠️ 注意：这是故意写得有问题的代码，用于展示审查效果！
"""

import sqlite3
import hashlib
import os
from typing import Optional


# ============================================================
# 问题 1：硬编码密钥 + SQL 注入
# ============================================================
SECRET_KEY = "my-secret-key-12345"  # 🔴 安全问题：硬编码密钥
DATABASE_PATH = "/tmp/app.db"


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


def login_user(username: str, password: str) -> Optional[dict]:
    """
    用户登录

    问题：
    - SQL 注入漏洞：username 直接拼接到 SQL
    - 密码比较逻辑有问题
    """
    conn = get_db()
    cursor = conn.cursor()

    # 🔴 安全：SQL 注入 — username 未经过滤直接拼接
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()

    if user:
        # 🔴 安全：密码直接字符串比较（应该是哈希比较）
        stored_password = user[2]
        if password == stored_password:
            # 🟡 架构：认证逻辑和数据库操作混在一起
            return {"id": user[0], "username": user[1]}
    return None


# ============================================================
# 问题 2：N+1 查询
# ============================================================
def get_user_orders_n_plus_1(user_ids: list[int]) -> dict:
    """
    获取多个用户的订单

    问题：
    - N+1 查询：对每个用户单独查询，而不是用 IN 一次查出
    """
    conn = get_db()
    cursor = conn.cursor()
    result = {}

    for user_id in user_ids:
        # 🔴 性能：循环内执行 SQL，N+1 问题
        cursor.execute(f"SELECT * FROM orders WHERE user_id = {user_id}")
        orders = cursor.fetchall()
        result[user_id] = orders

    conn.close()  # 🟡 架构：没有在 finally 中关闭
    return result


# ============================================================
# 问题 3：不必要的循环 + 魔法数字
# ============================================================
def calculate_order_amount(items: list[dict]) -> float:
    """
    计算订单总金额

    问题：
    - 不必要的中间列表
    - 魔法数字
    """
    prices = []
    for item in items:
        # 🟡 架构：0.15 是魔法数字，应该定义为常量
        price = item["price"] * item["quantity"] * 0.15
        prices.append(price)

    total = 0
    for p in prices:
        total += p

    return total


# ============================================================
# 问题 4：密码哈希算法过时
# ============================================================
def hash_password(password: str, salt: Optional[str] = None) -> str:
    """
    密码哈希

    问题：
    - 使用 MD5（已不安全，应该用 bcrypt/argon2）
    - 加盐方式简单，容易被彩虹表攻击
    """
    if salt is None:
        salt = os.urandom(16).hex()

    # 🔴 安全：MD5 已破解，不应使用
    hashed = hashlib.md5((password + salt).encode()).hexdigest()
    return f"{salt}${hashed}"


# ============================================================
# 🔥 冲突场景 A：安全输入校验 vs 性能开销
# ============================================================
# 预期辩论：
#   Security Agent: "每个字段都要严格校验，防止注入和 XSS"
#   Performance Agent: "逐字段正则匹配在批量请求时太慢"
#   Consensus: 应该裁决"用预编译正则 + 批量校验"折中

import re
import json
from typing import Any

def sanitize_user_input_batch(records: list[dict]) -> list[dict]:
    """
    批量清洗用户输入（如批量导入用户数据）

    ⚡ 冲突点：
    - Security: 必须逐字段严格校验，否则有 XSS/注入风险
    - Performance: 10000 条记录逐字段正则会非常慢
    """
    cleaned = []
    for record in records:
        sanitized = {}
        for key, value in record.items():
            if isinstance(value, str):
                # 🔴 Security: 正则逐个字段清洗（但 10000 条就很慢）
                value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE)
                value = re.sub(r'[<>"\']', '', value)  # 过于激进，可能误杀正常字符
                value = re.sub(r'(SELECT|INSERT|DELETE|DROP|UNION)\s', '', value, flags=re.IGNORECASE)
            sanitized[key] = value
        cleaned.append(sanitized)
    return cleaned


# ============================================================
# 🔥 冲突场景 B：过度抽象 vs 性能 vs 安全
# ============================================================
# 预期辩论：
#   Architecture Agent: "这个装饰器过度抽象了，职责太多"
#   Performance Agent: "每次请求都重新解析 JWT，应该缓存"
#   Security Agent: "缓存 JWT 验证结果有安全隐患，Token 可能已过期"

from functools import wraps
import time
import base64
import hmac

# 🔴 架构：全局可变状态 — 装饰器内部使用了模块级缓存
_TOKEN_CACHE: dict[str, dict] = {}

def auth_require_permission(permission: str):
    """
    多合一认证装饰器：同时做了 JWT 解析、权限校验、日志记录、频率限制

    ⚡ 冲突点：
    - Architecture: 这个装饰器承担了 4 种职责，违反单一职责原则
    - Performance: 每次都重新解析 JWT，开销大；但又用了不安全的缓存
    - Security: 缓存 Token 验证结果有安全风险（Token 可能已被吊销）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get('request', args[0] if args else None)
            token = getattr(request, 'token', '')

            # 🔴 Security: 直接用 split 解析 JWT，没有验证签名
            try:
                payload_b64 = token.split('.')[1]
                payload_json = base64.b64decode(payload_b64 + '==').decode()
                payload = json.loads(payload_json)
            except Exception:
                raise ValueError("Invalid token")

            # 🔴 Security + Performance 冲突：缓存 token 验证结果
            cache_key = token[-20:]  # 只用后 20 位做缓存 key — 不安全
            if cache_key in _TOKEN_CACHE:
                payload = _TOKEN_CACHE[cache_key]
            else:
                # 🔴 Performance: 每次做 HMAC 校验（实际上也没真正校验签名）
                secret = os.environ.get('JWT_SECRET', SECRET_KEY)
                expected = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()
                # 🔴 Security: HMAC 结果没和任何东西比较，形同虚设
                _TOKEN_CACHE[cache_key] = payload  # 无过期时间的缓存

            # 🟡 架构：权限检查、日志、频率限制全塞在一起
            if payload.get('role') != permission:
                raise PermissionError(f"Requires {permission}")

            print(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")  # 应该用 logging
            time.sleep(0.01)  # 🟡 Performance: 假装做频率限制，实际是 sleep

            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 🔥 冲突场景 C：加密 vs 性能 vs 过度设计
# ============================================================
# 预期辩论：
#   Security Agent: "敏感数据必须加密存储"
#   Performance Agent: "每行都单独 AES 加密，写入 10000 行太慢"
#   Architecture Agent: "应该用数据库透明加密而非应用层逐字段加密"

from Crypto.Cipher import AES  # pycryptodome

# 🔴 Security: 硬编码加密密钥
ENCRYPTION_KEY = b'my-32-byte-key!!-this-is-bad!!'
ENCRYPTION_IV = b'1234567890123456'

def save_user_data_encrypted(users: list[dict]) -> int:
    """
    逐行加密保存用户敏感数据

    ⚡ 冲突点：
    - Security: 敏感数据必须加密，AES-256 是正确的做法
    - Performance: 每行单独创建 cipher + 加密，10000 行 = 10000 次 AES 初始化
    - Architecture: 应用层手动加密不如用数据库透明加密(TDE)，代码还更干净
    """
    conn = get_db()
    cursor = conn.cursor()
    saved = 0

    for user in users:
        # 🔴 Performance：每次循环都创建新的 cipher 对象
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, ENCRYPTION_IV)

        # 🟡 Architecture：手动序列化 + 填充，容易出错
        raw_data = json.dumps(user).encode('utf-8')
        # PKCS7 padding — 手动实现容易出错
        pad_len = 16 - (len(raw_data) % 16)
        raw_data += bytes([pad_len]) * pad_len

        encrypted = cipher.encrypt(raw_data)
        encoded = base64.b64encode(encrypted).decode()

        # 🔴 Security: SQL 注入风险 — user['id'] 没有参数化
        cursor.execute(f"INSERT INTO users_encrypted (id, data) VALUES ({user['id']}, '{encoded}')")
        saved += 1

    conn.commit()
    conn.close()
    return saved


# ============================================================
# 🔥 冲突场景 D：全局缓存 vs 线程安全 vs 代码复杂度
# ============================================================
# 预期辩论：
#   Performance Agent: "频繁查询的配置应该加缓存"
#   Architecture Agent: "全局字典不当缓存，应该用 lru_cache 或 Redis"
#   Security Agent: "缓存里放了敏感配置，没有访问控制"

# 🔴 Security + Architecture: 全局配置缓存，无过期、无淘汰、无线程安全
_CONFIG_CACHE: dict[str, Any] = {}

def get_config_with_cache(key: str) -> Any:
    """
    获取配置项（带简单缓存）

    ⚡ 冲突点：
    - Performance: 缓存避免了重复 DB 查询，思路对
    - Architecture: 全局字典没有 TTL、没有淘汰策略、线程不安全
    - Security: 敏感配置（如第三方 API Key）存在内存中无保护
    """
    if key in _CONFIG_CACHE:
        return _CONFIG_CACHE[key]

    # 模拟从数据库查询
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT value FROM config WHERE key = '{key}'")  # 🔴 SQL 注入
    row = cursor.fetchone()
    conn.close()

    if row:
        _CONFIG_CACHE[key] = row[0]  # 永不淘汰的缓存
        return row[0]
    return None
