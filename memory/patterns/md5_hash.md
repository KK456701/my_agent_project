# 模式: 缓存键设计不安全且不合理

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

## 审查次数: 27

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户数据。同时，使用 Token 的一部分作为键，而不是使用 Token 的完整哈希或用户 ID，增加了安全风险。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:120
- **严重程度**: high
- **描述**: Skills 规则命中: hashlib\.md5\(
- **建议**: 改为 bcrypt.hashpw(password.encode(), bcrypt.gensalt())

### 案例 3
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:120
- **严重程度**: high
- **描述**: Skills 规则命中: hashlib\.md5\(
- **建议**: 改为 bcrypt.hashpw(password.encode(), bcrypt.gensalt())

### 案例 4
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:212-218
- **严重程度**: high
- **描述**: _TOKEN_CACHE 缓存了 JWT 解析结果，但：1. 缓存 key 只取 token 后 20 位，存在哈希冲突风险，不同 token 可能映射到同一缓存项。2. 缓存无 TTL（过期时间），token 被吊销后缓存仍有效，导致已失效的 token 可继续使用。3. 缓存为全局字典，无大小限制，可能导致内存泄漏。
- **建议**: 1. 使用完整的 token 哈希作为缓存 key。2. 为缓存添加 TTL（如 5 分钟），或使用 Redis 等支持过期时间的缓存。3. 如果必须缓存，应同时缓存 token 的过期时间并验证。

### 案例 5
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:196-210
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中的 _TOKEN_CACHE 缓存了 JWT 解析结果，但：1. 缓存 key 只取 token 后 20 位，可能导致不同 token 产生相同 key（哈希冲突），返回错误结果。2. 缓存永不过期，token 被吊销后仍可使用。3. 缓存是全局字典，无并发保护。
- **建议**: 1. 使用完整的 token SHA256 哈希作为缓存 key。2. 为缓存添加 TTL（如 5 分钟），或使用 Redis 等支持过期时间的缓存。3. 如果必须缓存，应同时缓存 token 的过期时间并验证。修改为：cache_key = hashlib.sha256(token.encode()).hexdigest(); 并检查 payload 中的 exp 字段。

### 案例 6
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:120
- **严重程度**: high
- **描述**: Skills 规则命中: hashlib\.md5\(
- **建议**: 改为 bcrypt.hashpw(password.encode(), bcrypt.gensalt())

### 案例 7
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-210
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中的 _TOKEN_CACHE 缓存了 JWT 解析结果，但：1. 缓存 key 只取 token 后 20 位，可能导致不同 token 产生相同 key（哈希冲突）；2. 缓存没有过期时间，已吊销的 token 仍会被视为有效；3. 缓存是全局可变状态，存在线程安全问题。
- **建议**: 1. 使用完整的 token 哈希作为缓存 key。2. 为缓存添加 TTL（如 5 分钟），或使用 Redis 等支持过期时间的缓存。3. 如果必须缓存，应同时缓存 token 的过期时间并验证。

### 案例 8
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:24-26
- **严重程度**: high
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的认证结果，造成越权访问。攻击者可以构造后 20 字符相同的恶意 Token 来利用此漏洞。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用 JWT 的 jti（JWT ID）声明作为缓存键。修改为：import hashlib; cache_key = hashlib.sha256(token.encode()).hexdigest()

### 案例 9
- **日期**: 2026-05-18_105740
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:22-28
- **严重程度**: info
- **描述**: process_secure_transaction 函数依赖 old-crypto-lib v1.2.3，该版本存在已知的 RCE 漏洞（CVE-2024-5678，CVSS 9.8）。攻击者可以通过构造恶意的密文触发远程代码执行。虽然代码注释说明了替换成本（3 个月重写、15 倍性能下降），但安全风险不可接受。
- **建议**: 立即停止使用该库。短期方案：在调用 decrypt_payload 前增加输入验证和长度限制，并部署 WAF 规则拦截可疑请求。长期方案：按计划替换为安全库，同时考虑使用硬件安全模块（HSM）或 sidecar 代理来隔离风险。

### 案例 10
- **日期**: 2026-05-18_105740
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:7
- **严重程度**: info
- **描述**: 文件导入了 hashlib 模块，但在代码中未使用。虽然这是小问题，但未使用的导入会增加代码混乱度，并可能误导后续维护者。
- **建议**: 移除未使用的导入：删除 'import hashlib' 这一行。

### 案例 11
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:24-25
- **严重程度**: high
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的认证结果，造成越权访问。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

### 案例 12
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:28-40
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的权限信息。虽然概率较低，但在高并发场景下可能被利用。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

### 案例 13
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:22-35
- **严重程度**: critical
- **描述**: 虽然使用了缓存，但缓存键 `token[-20:]` 仅取后 20 个字符，存在哈希碰撞风险。更严重的是，缓存永不过期，导致 Token 泄漏后永久有效。但若完全移除缓存，每次请求都解析 JWT（约 50ms），高并发下性能灾难。当前实现既不安全也不高效。
- **建议**: 使用 JWT 的 jti（JWT ID）作为缓存键，并设置合理的 TTL（如 15 分钟）。同时使用 `cachetools.TTLCache` 替代手动字典，自动过期。

### 案例 14
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:28-30
- **严重程度**: high
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的权限信息，造成越权访问。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

### 案例 15
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:202-203
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户信息。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

### 案例 16
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:170-210
- **严重程度**: high
- **描述**: auth_require_permission 装饰器同时承担了 JWT 解析、权限校验、审计日志、频率限制四种职责。此外：1) 使用模块级全局变量 _TOKEN_CACHE 作为缓存，无 TTL 和淘汰策略，可能导致内存泄漏；2) 缓存键只取 token 后 20 位，存在哈希冲突风险；3) HMAC 签名验证形同虚设（结果未比较）；4) 使用 print 而非 logging 记录审计日志。
- **建议**: 1) 拆分为多个独立的装饰器或中间件：@jwt_required @require_permission('admin') @audit_log @rate_limit；2) 使用 functools.lru_cache 或 Redis 替代手动字典缓存；3) 使用完整的 JWT 库（如 PyJWT）进行签名验证；4) 使用 logging 模块替代 print。

### 案例 17
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:198-209
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户权限信息。此外，缓存没有过期时间，Token 被吊销后缓存仍可能返回旧数据。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。同时应设置合理的 TTL。

### 案例 18
- **日期**: 2026-05-19_094200
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:195-206
- **严重程度**: high
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符，可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的认证结果。同时，HMAC 计算结果（expected）被赋值后从未使用，签名验证形同虚设。
- **建议**: 1. 使用 Token 的完整 SHA256 哈希作为缓存键。2. 移除无用的 HMAC 计算代码，或使用 PyJWT 库进行完整的签名验证。3. 如果必须缓存，应设置合理的 TTL 并考虑 Token 吊销场景。

### 案例 19
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:168-199
- **严重程度**: high
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户数据。同时，缓存键仅依赖 Token 的一部分，攻击者可以通过构造特定后缀的 Token 来利用缓存。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

### 案例 20
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:198-207
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户信息。此外，HMAC 计算结果未与任何预期值比较，形同虚设。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键。正确实现 HMAC 签名验证：expected_signature = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest(); if payload['signature'] != expected_signature: raise ValueError('Invalid signature')

### 案例 21
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:186-210
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中：1. 每次请求都重新 base64 解码和 JSON 解析 JWT payload，对于高并发场景开销大。2. 缓存键 cache_key = token[-20:] 只使用后 20 字符，可能导致不同 Token 产生相同缓存键（哈希冲突），返回错误数据。3. HMAC 计算结果未与任何值比较，形同虚设但仍在每次请求中执行。4. time
- **建议**: 1. 使用 Token 的完整 SHA256 哈希作为缓存键。2. 使用 functools.lru_cache 或 cachetools.TTLCache 替代手动字典，设置合理的 TTL（如 5 分钟）。3. 移除无意义的 HMAC 计算。4. 使用 asyncio.sleep() 替代 time.sleep() 或在异步上下文中使用非阻塞限流。

### 案例 22
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:195-196
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的认证结果。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

### 案例 23
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-168
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户信息。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

### 案例 24
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: high
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户权限信息。更严重的是，攻击者可以构造一个后 20 位相同的恶意 Token 来利用缓存。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用 JWT 的 jti（JWT ID）声明作为缓存键。修改为：cache_key = hashlib.sha256(token.encode()).hexdigest()

### 案例 25
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:192-200
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户权限。同时，缓存无过期时间，Token 吊销后仍可使用。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。同时添加 TTL 过期策略。

### 案例 26
- **日期**: 2026-05-19_101230
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:186-200
- **严重程度**: high
- **描述**: _TOKEN_CACHE 全局字典作为 JWT 验证结果缓存，存在多个问题：1) 缓存键 cache_key = token[-20:] 只使用 Token 后 20 位，可能导致不同 Token 产生相同缓存键（哈希冲突）。2) 缓存无过期时间，已吊销的 Token 仍可被使用。3) 全局可变状态在多线程环境下不安全。
- **建议**: 1. 使用 Token 的完整 SHA256 哈希或 JWT 的 jti 声明作为缓存键。2. 使用带 TTL 的缓存（如 cachetools.TTLCache）或 Redis 并设置合理的过期时间。3. 考虑使用线程安全的缓存实现。

### 案例 27
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:193-194
- **严重程度**: medium
- **描述**: 缓存键 cache_key = token[-20:] 只使用了 JWT 的后 20 个字符。这可能导致不同 Token 产生相同的缓存键（哈希冲突），从而返回错误的用户信息。同时，使用 Token 的一部分作为键增加了安全风险。
- **建议**: 使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。
