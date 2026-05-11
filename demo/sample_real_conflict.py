"""
🔥 真正的 Agent 对抗 Demo — 修复建议互斥

设计目标：让 Security 和 Performance 对同一段代码给出**互相矛盾**的修复建议，
迫使 Consensus Agent 做真正的 trade-off 裁决。

三个精心设计的冲突场景：
"""

import hashlib
import time
import os


# ============================================================
# 🔥 冲突 A: 密码哈希 — bcrypt vs SHA256 (同一段代码)
# ============================================================
#
# 代码特征:
#   - 当前用 SHA256（Security 会要求换成 bcrypt）
#   - 函数注释说明这是高并发登录接口（Performance 会担心 bcrypt 太慢）
#
# 预期:
#   Security: "SHA256 不安全，用 bcrypt cookie=12"
#   Performance: "bcrypt 单次 200ms，1000 QPS 扛不住，用 SHA256+多次迭代 salt"
#   → Consensus 必须裁决：安全优先还是性能优先？

def verify_password_high_traffic(username: str, password: str) -> bool:
    """
    高并发登录验证 — 每秒数千次调用
    
    当前: SHA256 + 固定 salt（单次 < 1ms）
    问题: SHA256 对 GPU 暴力破解抵抗力弱
    """
    SALT = "company-wide-salt-2024"  # Security: 固定盐值
    
    # Performance: 这个 hash 很快 (< 1ms)，支撑 5000 QPS
    computed = hashlib.sha256((password + SALT).encode()).hexdigest()
    
    stored = _get_stored_hash(username)  # simulate DB lookup
    return computed == stored


# ============================================================
# 🔥 冲突 B: 敏感数据加密 — 全量加密 vs 选择性加密
# ============================================================
#
# 代码特征:
#   - 批量处理用户数据，每个请求都加密全部字段
#   - Security 会要求加密所有敏感字段
#   - Performance 会指出全部加密导致 QPS 骤降
#
# 预期:
#   Security: "所有 PII 字段必须 AES 加密"
#   Performance: "手机号和身份证加密就够了，昵称头像加密浪费性能"

ENCRYPTION_KEY = "hardcoded-key-1234"  # Security: 硬编码密钥必须修

def batch_export_users(user_ids: list[int]) -> list[dict]:
    """
    批量导出用户数据 — 每批 1000 条，每条 20 个字段
    
    当前: 所有字段都调用 encrypt_field（包括非敏感的昵称、头像URL）
    问题: 1000 × 20 = 20000 次加密操作，P99 延迟 300ms+
    """
    results = []
    for uid in user_ids:
        user = _fetch_user(uid)
        
        # Security: PII 字段必须加密（手机号、身份证、银行卡）
        # Performance: 下面昵称、头像URL 也加密了 — 没必要！
        user["phone"] = _encrypt_field(user["phone"])       # ✅ 必须加密
        user["id_card"] = _encrypt_field(user["id_card"])    # ✅ 必须加密
        user["nickname"] = _encrypt_field(user["nickname"])  # ❌ Performance: 浪费
        user["avatar_url"] = _encrypt_field(user["avatar_url"])  # ❌ Performance: 浪费
        user["address"] = _encrypt_field(user["address"])    # ⚠️  有争议
        
        results.append(user)
    return results


# ============================================================
# 🔥 冲突 C: 数据库查询 — 安全 vs 性能 (经典 trade-off)
# ============================================================
#
# 代码特征:
#   - 同一段代码里有 N+1 查询问题 + SQL 注入风险
#   - Security 会要求参数化查询
#   - Performance 会要求批量查询（IN 子句）
#   - 两个修复方案都在同一段代码上，互相不冲突但需要协调
#
# 预期:
#   Security: "必须参数化查询"（改成 ? 占位符）
#   Performance: "必须批量查询"（改成 IN 子句）
#   → Consensus: 都采纳，但参数化 + IN 子句的组合有技术细节需要裁决

def get_users_orders(db, usernames: list[str]) -> list:
    """
    获取用户订单 — 同时存在安全漏洞和性能问题
    
    安全: username 直接拼接 SQL（注入风险）
    性能: 循环内逐条查询（N+1 问题）
    """
    cursor = db.cursor()
    orders = []
    
    for name in usernames:
        # 同一行代码 — Security: SQL 注入（username 未过滤）
        #             Performance: 循环查询（N+1）
        query = f"SELECT * FROM orders WHERE username = '{name}'"
        cursor.execute(query)
        orders.extend(cursor.fetchall())  # Performance: 逐条 extend 低效
    
    return orders


# ── 辅助函数 ──
def _get_stored_hash(u): return "hash_" + u
def _fetch_user(uid): return {"phone": "13800138000", "id_card": "110101199001011234", "nickname": "test", "avatar_url": "http://img.com/1.jpg", "address": "Beijing"}
def _encrypt_field(v): return v[::-1]  # 模拟加密
