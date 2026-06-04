---
name: "Token 缓存无过期机制 — 无法处理 Token 吊销"
description: "_TOKEN_CACHE 中的缓存条目没有设置 TTL（过期时间）。即使 Token 已被吊销或过期，缓存仍会返回旧的 payload，导致已失效的 Token 仍能通过权限检查。这是一个严重的安全漏洞。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:155
- **描述**: _TOKEN_CACHE 中的缓存条目没有设置 TTL（过期时间）。即使 Token 已被吊销或过期，缓存仍会返回旧的 payload，导致已失效的 Token 仍能通过权限检查。这是一个严重的安全漏洞。
- **修复**: 使用带 TTL 的缓存（如 cachetools.TTLCache）或 Redis 并设置合理的过期时间。修改为：from cachetools import TTLCache; _TOKEN_CACHE = TTLCache(maxsize=1000, ttl=300)


### 案例 2
- **日期**: 2026-06-04 17202
- **来源 PR**: feat: 增加两个新方法
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:70-83
- **描述**: 在 isTokenValid 方法中，claims.getExpiration() 可能返回 null（如果 token 中没有设置过期时间），此时调用 expiration.before(new Date()) 会抛出 NullPointerException。虽然被 catch 捕获后会返回 false，但这是隐式的错误处理，不如显式检查更清晰。
- **修复**: 在调用 expiration.before() 之前添加 null 检查：if (expiration == null) return false; 或者认为没有过期时间的 token 应视为永久有效，根据业务需求决定。

### 案例 3
- **日期**: 2026-06-04 17381
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:84-101
- **描述**: getRemainingTime 方法捕获了所有 Exception 并统一返回 -1。这种做法会掩盖不同类型的错误（如 token 格式错误、签名验证失败、token 已过期等），使得调用方无法区分'token 无效'和'token 已过期'这两种不同的情况。从架构角度看，这降低了 API 的表达能力，迫使调用方进行额外的检查或猜测。
- **修复**: 建议区分异常类型：1) 对于 token 解析失败（如格式错误、签名无效），应抛出特定异常或返回特定错误码；2) 对于 token 已过期，应返回 0 或负值但通过不同的返回值或异常类型区分。例如，可以返回 -1 表示无效，返回 0 表示已过期，或者使用 Optional<Long> 并配合自定义异常。

### 案例 4
- **日期**: 2026-06-04 17455
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:88-95
- **描述**: getRemainingTime 方法在 token 无效（解析失败）和 token 已过期两种情况下均返回 -1。这导致调用方无法区分这两种不同的错误场景，可能会掩盖真正的错误原因（如 token 被篡改）。从性能角度看，这不是直接性能问题，但错误处理不明确可能导致后续的无效重试或错误日志，间接影响系统效率。
- **修复**: 建议区分两种错误场景：1) token 解析失败（格式错误/签名无效）时抛出特定异常或返回特殊值（如 Long.MIN_VALUE）；2) token 已过期时返回 0 或 -1。或者直接让异常向上传播，由调用方决定如何处理。
