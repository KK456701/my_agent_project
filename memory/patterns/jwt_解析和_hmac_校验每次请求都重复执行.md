---
name: "JWT 解析和 HMAC 校验每次请求都重复执行"
description: "auth_require_permission 装饰器在每次请求时都重新解析 JWT（base64 解码 + JSON 解析）并计算 HMAC。虽然尝试了缓存，但缓存设计不安全且无过期策略。对于高并发场景，每次请求的 HMAC 计算（SHA256）和 base64 解码是 CPU 密集型操作。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-210
- **描述**: auth_require_permission 装饰器在每次请求时都重新解析 JWT（base64 解码 + JSON 解析）并计算 HMAC。虽然尝试了缓存，但缓存设计不安全且无过期策略。对于高并发场景，每次请求的 HMAC 计算（SHA256）和 base64 解码是 CPU 密集型操作。
- **修复**: 1. 使用成熟的 JWT 库（如 PyJWT）替代手动解析，它们内部有缓存和验证优化。2. 如果必须手动实现，使用 functools.lru_cache 缓存解析结果，但需注意 Token 过期问题（结合 exp 声明）。3. 移除无意义的 HMAC 计算（结果未使用）。

