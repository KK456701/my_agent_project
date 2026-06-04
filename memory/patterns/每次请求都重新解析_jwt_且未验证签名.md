---
name: "每次请求都重新解析 JWT 且未验证签名"
description: "auth_require_permission 装饰器中，每次请求都执行 base64 解码和 JSON 解析来提取 JWT payload，但没有真正验证 HMAC 签名（HMAC 计算结果未与任何期望值比较）。同时使用了无过期时间的全局缓存，可能导致使用已吊销的 Token。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:200-215
- **描述**: auth_require_permission 装饰器中，每次请求都执行 base64 解码和 JSON 解析来提取 JWT payload，但没有真正验证 HMAC 签名（HMAC 计算结果未与任何期望值比较）。同时使用了无过期时间的全局缓存，可能导致使用已吊销的 Token。
- **修复**: 1. 使用成熟的 JWT 库（如 PyJWT）进行验证，它会自动处理签名验证和过期检查。2. 移除不安全的缓存，或使用带 TTL 的缓存（如 Redis）并验证 Token 是否被吊销。3. 将 JWT 验证结果缓存到请求上下文而非全局变量。

### 案例 2
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:193-200
- **描述**: auth_require_permission 装饰器中，每次请求都执行 base64 解码和 JSON 解析 JWT payload。虽然 JWT 解析本身开销不大，但结合 HMAC 计算（第 199 行）和后续的权限检查，每次请求都重复这些操作。更严重的是，HMAC 计算结果未与任何签名比较，导致安全校验形同虚设，同时浪费了 CPU 资源。
- **修复**: 1. 使用成熟的 JWT 库（如 PyJWT）进行解析和验证，它内部会缓存解码结果。2. 将 JWT 验证结果缓存到请求上下文中（如 Flask 的 g 对象），避免同一请求内重复解析。3. 移除无意义的 HMAC 计算，改用真正的签名验证。


### 案例 3
- **日期**: 2026-06-04 17384
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:88-101
- **描述**: 新增的 getRemainingTime 方法（第88-101行）每次调用都会完整解析 JWT Token（调用 parseToken），然后计算剩余时间。在典型的 Web 应用中，同一个 Token 可能在一次请求中被多次检查有效期（如多个过滤器、拦截器），每次都会重复解析 Token，造成不必要的 CPU 开销。JWT 解析涉及 Base64 解码、签名验证和 Claims 提取，是相对昂贵的
- **修复**: 1) 如果调用方已经持有 Claims 对象，建议提供一个重载方法 getRemainingTime(Claims claims) 避免重复解析；2) 在 UserContext 或请求级别的缓存中缓存解析后的 Claims 对象，避免同一请求中多次解析同一个 Token；3) 如果 Token 解析是高频操作，考虑使用 ThreadLocal 缓存当前请求的 Claims 对象。
