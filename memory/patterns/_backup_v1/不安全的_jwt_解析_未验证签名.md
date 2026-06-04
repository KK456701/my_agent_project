# 模式: 不安全的 JWT 解析 — 未验证签名

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用成熟的 JWT 库（如 PyJWT）进行完整的签名验证。修改为：import jwt; payload = jwt.decode(token, secret, algorithms=['HS256'])

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中，JWT 的解析仅通过 base64 解码 payload 部分，完全没有验证签名。攻击者可以伪造任意 JWT Token，绕过认证和权限检查。此外，HMAC 计算结果未与任何预期值比较，形同虚设。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行完整的签名验证。修改为：import jwt; payload = jwt.decode(token, secret, algorithms=['HS256'])

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
