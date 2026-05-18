# 模式: 缓存键设计不安全且不合理

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 Token 的完整 SHA256 哈希作为缓存键，或者使用用户 ID + Token 的哈希组合。更安全的做法是使用 JWT 的 jti（JWT ID）声明作为缓存键，因为它是唯一的。

## 审查次数: 5

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
