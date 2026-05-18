"""
🔴 对抗性冲突测试 — 保证触发的场景

设计原则：同一段代码，两个 Agent 的修复建议方向相反，Consensus 必须二选一。
"""

import time
from Crypto.Cipher import AES

# ============================================================
# 🔴 冲突 1: JWT 缓存 — 删除 vs 保留
# ============================================================
# Security: "缓存永不过期→Token泄漏永久有效→必须删除缓存每次验签"
# Performance: "每次验签50ms→高并发扛不住→必须保留缓存加TTL"
# → 修复方向互斥：一个说删，一个说留

_TOKEN_CACHE = {}

def auth_require_permission(permission: str):
    """认证装饰器 — JWT 缓存存在安全与性能的 trade-off"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            token = kwargs.get("token", "")
            # 缓存 key 取 token 后20位 → 碰撞风险
            cache_key = token[-20:]
            if cache_key in _TOKEN_CACHE:
                return _TOKEN_CACHE[cache_key]
            # 解析 JWT
            payload = _decode_jwt(token)
            _TOKEN_CACHE[cache_key] = payload  # 永不过期
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# 🔴 冲突 2: 密码验证 — bcrypt vs SHA256
# ============================================================
# Security: "SHA256 不安全，必须改用 bcrypt"
# Performance: "bcrypt 单次 200ms，高并发登录扛不住，SHA256+多次迭代就够了"
# → 修复方向互斥：一个要 bcrypt（安全但慢），一个要 SHA256（快但不安全）

def verify_password_high_qps(username: str, password: str) -> bool:
    """
    高并发登录验证 — 峰值 5000 QPS
    当前: SHA256 + 固定 salt
    """
    SALT = "hardcoded-salt-123"
    digest = __import__("hashlib").sha256((password + SALT).encode()).hexdigest()
    return digest == _db_lookup(username)


# ============================================================
# 🔴 冲突 3: SQL 参数化 vs 字符串拼接
# ============================================================
# Security: "f-string 拼接 SQL → 注入风险 → 必须参数化"
# Performance: "参数化会导致优化器选错索引 → 这个查询 QPS 太高不能参数化"
# → 修复方向互斥：一个要参数化，一个要拼接

def search_orders(db, keyword: str):
    """
    高频订单搜索 — 峰值 3000 QPS，已有专用索引
    """
    cursor = db.cursor()
    # Security: f-string 拼接，SQL 注入风险
    # Performance: 当前执行计划最优，参数化会导致索引失效
    query = f"SELECT * FROM orders WHERE title LIKE '%{keyword}%'"
    cursor.execute(query)
    return cursor.fetchall()


# ============================================================
# 🔴 冲突 4: 加密 — AES 应用层 vs 数据库 TDE
# ============================================================
# Security: "所有敏感数据必须 AES-256 加密存储"
# Performance: "每行 AES 加密耗时 2ms，10万行要 200 秒，应用层加密是性能灾难"
# Architecture: "应用层加密是过度设计，数据库 TDE 就够了"
# → 三个 Agent 可能给出三个不同方向

ENCRYPTION_KEY = "hardcoded-aes-key!!"

def save_user_data_encrypted(users: list[dict], db) -> None:
    """
    批量保存加密用户数据 — 每次 10000 条
    """
    cipher = AES.new(ENCRYPTION_KEY.encode(), AES.MODE_CBC, b"fixed-iv-1234567")
    
    for user in users:
        raw = f"{user['name']}|{user['email']}|{user['phone']}"
        # 手动 PKCS7 填充
        pad = 16 - len(raw) % 16
        padded = raw + chr(pad) * pad
        encrypted = cipher.encrypt(padded.encode())
        
        db.execute(
            f"INSERT INTO users_encrypted (id, data) VALUES ({user['id']}, '{encrypted.hex()}')"
        )
    db.commit()


# ── 辅助函数 ──
def _decode_jwt(t): return {"sub": "user1", "perm": "admin"}
def _db_lookup(u): return "stored_hash"
