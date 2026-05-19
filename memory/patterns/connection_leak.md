# 模式: 全局配置缓存无淘汰策略导致内存泄漏风险

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
1. 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存。2. 设置合理的 TTL 和最大缓存大小。3. 使用线程安全的缓存实现（如 Redis）或添加锁保护。

## 审查次数: 19

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:286-300
- **严重程度**: medium
- **描述**: _CONFIG_CACHE 全局字典作为缓存，没有 TTL（过期时间）、没有淘汰策略（如 LRU）、没有大小限制。随着时间推移，所有被访问过的配置项都会永久驻留在内存中，可能导致内存泄漏。同时，该缓存不是线程安全的，在多线程环境下存在竞态条件。
- **建议**: 1. 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存。2. 设置合理的 TTL 和最大缓存大小。3. 使用线程安全的缓存实现（如 Redis）或添加锁保护。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:284-301
- **严重程度**: medium
- **描述**: get_config_with_cache 函数使用全局字典 _CONFIG_CACHE 缓存配置，但没有任何淘汰策略（TTL、LRU 等）。随着不同 key 的查询，缓存会无限增长，可能导致内存泄漏。
- **建议**: 1. 使用 functools.lru_cache 并设置 maxsize。2. 为缓存添加 TTL 过期机制。3. 使用 Redis 等外部缓存服务。

### 案例 3
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: medium
- **描述**: 装饰器内部使用了模块级全局字典 _TOKEN_CACHE 作为缓存。在多线程或多进程环境下，对 _TOKEN_CACHE 的并发读写会导致数据竞争、缓存不一致甚至程序崩溃。此外，该缓存没有过期策略，可能导致内存泄漏。
- **建议**: 使用线程安全的缓存方案，如 functools.lru_cache（适用于纯函数）或专门的缓存库（如 cachetools）。如果必须使用全局字典，应使用 threading.Lock 或读写锁来保护。同时，为缓存添加 TTL（过期时间）和最大容量限制。

### 案例 4
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:287-289
- **严重程度**: medium
- **描述**: _CONFIG_CACHE 是一个全局字典，缓存的数据永不过期、永不淘汰。随着时间推移，缓存会无限增长，可能导致内存泄漏。同时，如果数据库中的配置被更新，缓存不会同步更新，导致返回过时的配置值。
- **建议**: 1. 使用 functools.lru_cache 并设置 maxsize。2. 或使用支持 TTL 的缓存库（如 cachetools.TTLCache）。3. 实现缓存失效机制，当配置更新时主动清除缓存。

### 案例 5
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:24-28
- **严重程度**: high
- **描述**: get_db() 函数每次调用都创建新的数据库连接，且没有连接池、没有上下文管理器、没有异常处理。调用方（如 get_user_orders_n_plus_1、save_user_data_encrypted）在 finally 中关闭连接，但部分调用（如 login_user）根本没有关闭连接，导致连接泄漏。这种设计使得数据库资源管理不可靠，在高并发下会耗尽连接。
- **建议**: 1. 使用上下文管理器封装连接生命周期：with get_db() as conn:。2. 引入连接池（如 sqlite3 的 connection 复用或使用 SQLAlchemy 的池化）。3. 将 get_db 改为返回连接池中的连接，并确保调用方通过 with 语句使用。

### 案例 6
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:295-301
- **严重程度**: medium
- **描述**: get_config_with_cache 函数使用全局字典 _CONFIG_CACHE 缓存配置，但：1. 缓存永不过期，配置变更后不会更新。2. 字典不是线程安全的，并发写入可能导致数据损坏。3. 没有缓存大小限制，可能内存泄漏。
- **建议**: 使用 functools.lru_cache(maxsize=128) 替代手动缓存，或使用 Redis 等支持 TTL 的缓存系统。如果必须用内存缓存，添加 TTL 检查和线程锁。

### 案例 7
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:27
- **严重程度**: high
- **描述**: _TOKEN_CACHE 中的缓存项永不过期。如果某个 JWT Token 被泄漏或用户权限被撤销，攻击者可以永久使用该 Token 的缓存结果，直到服务重启。这违反了最小权限原则和会话管理的最佳实践。
- **建议**: 为缓存添加 TTL（过期时间），例如使用 cachetools.TTLCache 或手动记录时间戳。修改为：from cachetools import TTLCache; _TOKEN_CACHE = TTLCache(maxsize=10000, ttl=300)  # 5分钟过期

### 案例 8
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:21-35
- **严重程度**: high
- **描述**: _TOKEN_CACHE 是一个全局字典，缓存键使用 token[-20:] 存在碰撞风险，且缓存条目永不过期。随着时间推移，所有访问过的 Token 都会永久驻留内存，导致内存持续增长直至 OOM。
- **建议**: 1. 使用 functools.lru_cache(maxsize=10000) 或 cachetools.TTLCache 替代手动字典。2. 设置合理的 TTL（如 300 秒）和最大缓存大小。3. 使用完整的 Token 哈希作为缓存键避免碰撞。

### 案例 9
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:26
- **严重程度**: high
- **描述**: JWT 解析结果被缓存到全局字典 _TOKEN_CACHE 中且永不过期。一旦某个 Token 被泄露或用户权限被撤销，攻击者可以永久使用该缓存的 payload 进行越权操作，因为缓存不会失效。
- **建议**: 1. 添加 TTL（过期时间）到缓存条目，例如使用 cachetools.TTLCache。2. 在 Token 验证时检查 JWT 的 exp（过期时间）声明。3. 考虑使用 Redis 等外部缓存并设置合理的过期时间。

### 案例 10
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:28-40
- **严重程度**: high
- **描述**: _TOKEN_CACHE 是一个全局字典，缓存键为 token[-20:]，且缓存永不过期。随着时间推移，所有访问过的 Token 都会永久驻留在内存中，导致内存无限增长。在长期运行的服务中，这会造成严重的内存泄漏。
- **建议**: 1. 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存。2. 设置合理的 TTL（如 5 分钟）和最大缓存大小（如 1000 条）。3. 使用更安全的缓存键（如 Token 的完整 SHA256 哈希）。

### 案例 11
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:262-280
- **严重程度**: medium
- **描述**: _CONFIG_CACHE 全局字典作为缓存，没有 TTL（过期时间）、没有淘汰策略（如 LRU）、没有大小限制。随着时间推移，所有被访问过的配置项都会永久驻留在内存中，可能导致内存泄漏。同时，该缓存线程不安全。
- **建议**: 1) 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存；2) 设置合理的 TTL 和最大缓存大小；3) 使用线程安全的缓存实现（如 Redis）或添加锁保护。

### 案例 12
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:268-300
- **严重程度**: medium
- **描述**: _CONFIG_CACHE 全局字典作为缓存，没有 TTL（过期时间）、没有淘汰策略（如 LRU）、没有大小限制。随着时间推移，所有被访问过的配置项都会永久驻留在内存中。此外，该缓存未考虑线程安全，在多线程环境下可能出现数据竞争。
- **建议**: 1) 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存；2) 设置合理的 TTL 和最大缓存大小；3) 使用线程安全的缓存实现（如 Redis）或添加锁保护。

### 案例 13
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:273-301
- **严重程度**: high
- **描述**: _CONFIG_CACHE 全局字典作为缓存，没有 TTL（过期时间）、没有淘汰策略（如 LRU）、没有大小限制。随着时间推移，所有被访问过的配置项都会永久驻留内存。如果配置项数量很大（如动态生成的配置），可能导致内存泄漏。
- **建议**: 1. 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存。2. 设置合理的 TTL 和最大缓存大小。3. 使用线程安全的缓存实现（如 Redis）或添加锁保护。

### 案例 14
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:168-199
- **严重程度**: medium
- **描述**: _TOKEN_CACHE 全局字典作为缓存，没有 TTL（过期时间）、没有淘汰策略（如 LRU）、没有大小限制。随着时间推移，所有被访问过的 Token 都会永久驻留内存，导致内存泄漏。对于高并发系统，可能耗尽内存。
- **建议**: 1. 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存。2. 设置合理的 TTL（如 5 分钟）和最大缓存大小（如 10000 条）。3. 使用线程安全的缓存实现（如 Redis）或添加锁保护。

### 案例 15
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:73-75
- **严重程度**: medium
- **描述**: get_user_orders_n_plus_1 函数中，数据库连接在函数末尾关闭。如果函数中间发生异常，连接将不会被关闭，导致资源泄漏。
- **建议**: 使用 try...finally 块或上下文管理器（with 语句）来确保连接始终被关闭。例如：conn = get_db(); try: ... finally: conn.close()

### 案例 16
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-168
- **严重程度**: high
- **描述**: _TOKEN_CACHE 是模块级全局字典，被装饰器内部使用。在多线程环境下，并发访问该字典会导致数据竞争。同时，缓存没有 TTL 和淘汰策略，随着时间推移会无限增长，导致内存泄漏。
- **建议**: 1) 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存；2) 设置合理的 TTL（如 5 分钟）和最大缓存大小；3) 如果必须使用全局缓存，使用 threading.Lock 保护写操作。

### 案例 17
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:240-260
- **严重程度**: high
- **描述**: _CONFIG_CACHE 全局字典作为缓存，没有 TTL（过期时间）、没有淘汰策略（如 LRU）、没有大小限制。随着时间推移，所有被访问过的配置项都会永久驻留在内存中，导致内存泄漏。
- **建议**: 1) 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典缓存；2) 设置合理的 TTL 和最大缓存大小；3) 使用线程安全的缓存实现（如 Redis）或添加锁保护。

### 案例 18
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:73-74
- **严重程度**: medium
- **描述**: get_user_orders_n_plus_1 函数在正常路径中关闭了数据库连接，但如果查询过程中抛出异常，连接将永远不会被关闭，导致连接泄漏。
- **建议**: 使用上下文管理器（with 语句）或 try/finally 块确保连接始终被关闭。修改为：conn = get_db(); try: ... finally: conn.close()

### 案例 19
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:206-207
- **严重程度**: medium
- **描述**: 装饰器中使用 print() 记录审计日志，违反了团队编码规范。print() 无法控制日志级别、无法配置输出目标、无法在生产环境中关闭。
- **建议**: 使用 logging 模块：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] {payload.get('sub')} accessed")
