"""
🔥 冲突 Demo — 故意制造工程权衡困境

这段代码不是为了演示"找问题"，而是为了演示"Agents 打架"。

预期冲突：
A. Security vs Performance:
   "必须加密敏感数据" vs "加密导致每次请求多 15ms，QPS 降 30%"

B. Security vs Performance:  
   "必须用 bcrypt 做密码哈希" vs "bcrypt 太慢，用 SHA256+salt 就够了"

C. Security vs Architecture:
   "必须加输入验证" vs "过度验证导致无法灵活扩展字段"

D. Performance vs Architecture:
   "加缓存提速" vs "全局缓存是架构反模式，应该用 Redis"

每个场景的代码都让两个 Agent 从不同角度得出**互斥**的结论，
Consensus 必须做真正的 trade-off 裁决，而非简单的"都采纳"。
"""

import hashlib
import time
import json
from functools import lru_cache
from typing import Optional, Any


# ============================================================
# 🔥 冲突 A: 加密 vs 性能 — 同段代码两种对立观点
# ============================================================
# Security: "用户手机号必须 AES 加密存储，明文是严重泄露风险"
# Performance: "每个请求都加密解密，P99 延迟增加 15ms，高并发扛不住"
# → Consensus 需要判断：加密是否必须？性能代价是否可接受？

ENCRYPTION_KEY = b"this-is-a-hardcoded-key!!"  # 硬编码密钥

def save_user_profile(user_id: int, phone: str, address: str) -> None:
    """
    保存用户资料

    Security: 手机号和地址是 PII（个人身份信息），必须加密存储
    Performance: 这个函数在注册和更新时被高频调用，加密开销需要评估
    Architecture: 加密逻辑和业务逻辑耦合，应该分离
    """
    from Crypto.Cipher import AES  # type: ignore
    
    # Security: 每次加密创建新 cipher → 性能浪费
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_EAX)
    
    # Performance: 加密 10000 次 = 10000 次 AES init = 大量 CPU
    encrypted_phone = cipher.encrypt(phone.encode())
    encrypted_address = cipher.encrypt(address.encode())
    
    # 模拟写入数据库
    _store_to_db(user_id, encrypted_phone, encrypted_address)


# ============================================================
# 🔥 冲突 B: bcrypt vs SHA256+salt — 安全 vs 性能的经典对抗
# ============================================================
# Security: "bcrypt 是密码哈希行业标准，SHA256 不应该用于密码"
# Performance: "bcrypt 在高并发登录场景下 P99 延迟可达 200ms+"
# → Consensus 需要判断：安全到哪个程度？性能牺牲值不值？

def authenticate_user(username: str, password: str) -> bool:
    """
    用户认证

    Security: 应该用 bcrypt/argon2，SHA256 对 GPU 暴力破解抵抗力弱
    Performance: bcrypt 的 work factor=12 时单次验证 ~200ms，1000 QPS 扛不住
    Architecture: 哈希算法硬编码，应该可配置
    """
    stored_hash = _get_password_hash(username)
    
    # Performance 偏好: SHA256 + salt，单次 < 1ms
    # Security 偏好: bcrypt，单次 ~200ms
    salt = "fixed-salt-12345"  # Security: 固定盐值不安全
    computed = hashlib.sha256((password + salt).encode()).hexdigest()
    
    return computed == stored_hash


# ============================================================
# 🔥 冲突 C: 输入验证 — 安全严格 vs 业务灵活
# ============================================================
# Security: "所有输入必须严格校验，防止注入和 XSS"
# Performance: "每个字段正则匹配在大批量场景下是性能灾难"
# Architecture: "校验逻辑应该声明式配置，而非硬编码 if-else"
# → Consensus 需要平衡：哪些字段必须严审？哪些可以松一点？

def process_batch_users(users: list[dict]) -> list[dict]:
    """
    批量处理用户数据（如导入 10000 条用户记录）

    Security: 每个字段都要验证——防注入、防 XSS、防溢出
    Performance: 10000 条 × 10 字段 × 3 个正则 = 30 万次操作
    Architecture: 校验规则硬编码，新增字段需改代码
    """
    import re
    
    validated = []
    for user in users:
        # Security: 严格校验 — 每个字段都要过
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', user.get('username', '')):
            continue  # Performance: 正则编译消耗
        
        # Security: 邮箱格式校验 — 但正则在循环内每次编译
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', user.get('email', '')):
            continue  # Performance: 又一个正则
        
        # Security: 手机号校验
        if not re.match(r'^\d{11}$', user.get('phone', '')):
            continue
        
        # Security: 地址不能含特殊字符 → 防止注入
        address = user.get('address', '')
        address = re.sub(r'[<>\'";]', '', address)
        
        validated.append(user)
    
    return validated  # Performance: 逐条 append 低效


# ============================================================
# 🔥 冲突 D: 缓存 vs 安全 — 提速 vs 数据泄露风险
# ============================================================
# Performance: "高频查询的配置和用户数据应该缓存，减轻 DB 压力"
# Security: "缓存敏感数据（用户角色、权限）存在泄露和过期风险"
# Architecture: "全局字典做缓存是反模式，应该用 Redis 或 lru_cache"
# → Consensus 需要判断：什么可以缓存？缓存在哪里？

# Performance 偏好: 全局缓存，极速，但无限增长 + 无过期
_CONFIG_CACHE: dict[str, Any] = {}
_USER_ROLE_CACHE: dict[int, str] = {}  # Security: 用户权限缓存风险

def get_user_role(user_id: int) -> str:
    """
    获取用户角色

    Performance: 这个函数被每个请求调用，必须缓存（否则 DB 扛不住）
    Security: 角色变更后缓存不失效 = 已撤销的权限仍然生效 → 越权风险
    Architecture: 业务逻辑、缓存、DB 查询全混在一起
    """
    # Performance: 缓存命中 → 0.001ms vs DB 查询 5ms
    if user_id in _USER_ROLE_CACHE:
        return _USER_ROLE_CACHE[user_id]
    
    role = _query_role_from_db(user_id)
    
    # Security: 缓存无 TTL → 角色变更后不失效
    _USER_ROLE_CACHE[user_id] = role
    
    # Architecture: 缓存、查询、业务逻辑耦合
    if role == 'admin':
        _log_admin_access(user_id)
    
    return role


def get_config(key: str) -> Optional[str]:
    """
    获取配置项
    
    Performance: 配置很少变，必须缓存（高频调用）
    Security: 有些配置包含敏感信息（如第三方 API Key），缓存泄露风险
    """
    # Performance: 缓存命中 → 极快
    if key in _CONFIG_CACHE:
        return _CONFIG_CACHE[key]
    
    value = _query_config_from_db(key)
    
    # Security: 不管什么配置都缓存 — API Key 也缓存
    _CONFIG_CACHE[key] = value
    
    return value


# ============================================================
# 🔥 冲突 E: 日志记录 — 安全审计 vs 性能开销 vs 架构
# ============================================================
# Security: "所有敏感操作必须记录审计日志，不可遗漏"
# Performance: "每次操作都写日志，I/O 开销比业务逻辑还大"
# Architecture: "print 做审计日志？应该用 logging + 异步写入"

def transfer_money(from_user: int, to_user: int, amount: float) -> bool:
    """
    转账操作

    Security: 必须记录完整的审计日志（谁、何时、转多少）
    Performance: 日志写磁盘 I/O 可能比转账计算还慢
    Architecture: print 输出到 stdout 无法管理、无法持久化
    """
    # 业务逻辑（假设很快）
    success = _do_transfer(from_user, to_user, amount)
    
    # Security: 审计日志 — 完整记录
    # Performance: 每次转账都写日志，高并发下文件锁竞争
    # Architecture: print 不是日志方案
    print(f"[AUDIT] transfer: {from_user} -> {to_user}, amount={amount}, time={time.time()}")
    
    return success


# ── 辅助函数（模拟）──
def _store_to_db(user_id, *args): pass
def _get_password_hash(username): return "dummy_hash"
def _query_role_from_db(user_id): return "user"
def _query_config_from_db(key): return "dummy_value"
def _do_transfer(frm, to, amount): return True
def _log_admin_access(user_id): pass
