---
name: "JWT 解析无签名验证 + 每次请求都重新解析"
description: "auth_require_permission 装饰器中，每次请求都通过 split 和 base64 解码手动解析 JWT，但没有验证 JWT 签名。这导致：1) 安全风险：任何人都可以伪造 Token；2) 性能开销：每次请求都进行 base64 解码和 JSON 解析，对于高并发场景是显著的 CPU 开销。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-210
- **描述**: auth_require_permission 装饰器中，每次请求都通过 split 和 base64 解码手动解析 JWT，但没有验证 JWT 签名。这导致：1) 安全风险：任何人都可以伪造 Token；2) 性能开销：每次请求都进行 base64 解码和 JSON 解析，对于高并发场景是显著的 CPU 开销。
- **修复**: 1. 使用成熟的 JWT 库（如 PyJWT）替代手动解析，库会自动验证签名。2. 对于高频访问的 Token，可以考虑缓存验证结果（但需注意安全 Agent 的缓存过期风险）。修改为：import jwt; payload = jwt.decode(token, secret, algorithms=['HS256'])。

