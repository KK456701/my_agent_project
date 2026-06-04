---
name: "JWT 签名验证缺失"
description: "auth_require_permission 装饰器中，JWT 的解析仅通过 base64 解码 payload 部分，没有验证 JWT 的签名。攻击者可以伪造任意 JWT token，冒充任何用户身份。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:200-201
- **描述**: auth_require_permission 装饰器中，JWT 的解析仅通过 base64 解码 payload 部分，没有验证 JWT 的签名。攻击者可以伪造任意 JWT token，冒充任何用户身份。
- **修复**: 使用成熟的 JWT 库（如 PyJWT）进行完整的签名验证。修改为：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

