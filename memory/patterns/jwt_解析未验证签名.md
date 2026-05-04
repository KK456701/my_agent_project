# 模式: JWT 解析未验证签名

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用成熟的 JWT 库（如 PyJWT）来解析和验证 Token。例如：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。库会自动处理签名验证、过期时间检查等。

## 审查次数: 2

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:191-196
- **严重程度**: critical
- **描述**: auth_require_permission 装饰器中，JWT 的 payload 仅通过 base64 解码获取，没有验证 Token 的签名。攻击者可以伪造任意 JWT Token，从而绕过身份验证和权限检查。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）来解析和验证 Token。例如：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。库会自动处理签名验证、过期时间检查等。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:195-210
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中，JWT Token 仅通过 split 和 base64 解码解析，没有验证签名。攻击者可以伪造任意 JWT Token，绕过身份验证。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行解析和验证。例如：import jwt; payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
