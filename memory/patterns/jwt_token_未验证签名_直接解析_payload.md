---
name: "JWT Token 未验证签名 — 直接解析 payload"
description: "auth_require_permission 装饰器中，JWT Token 的 payload 直接通过 base64 解码获取，没有验证 JWT 签名。攻击者可以伪造任意 Token，冒充任何用户身份并获取任意权限。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_094200
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:186-192
- **描述**: auth_require_permission 装饰器中，JWT Token 的 payload 直接通过 base64 解码获取，没有验证 JWT 签名。攻击者可以伪造任意 Token，冒充任何用户身份并获取任意权限。
- **修复**: 使用成熟的 JWT 库（如 PyJWT）进行 Token 验证：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。不要手动解析 JWT。

