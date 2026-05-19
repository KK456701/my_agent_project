# 模式: JWT 解析未验证签名 — 可被伪造 Token 攻击

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用成熟的 JWT 库（如 PyJWT）进行 Token 的解析和验证。修改为：import jwt; payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

## 审查次数: 3

## 历史案例

### 案例 1
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:186-195
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中的 JWT 解析逻辑仅通过 split('.') 分割 Token 并 base64 解码 payload，没有验证 JWT 的签名。攻击者可以构造任意 payload 的 JWT Token，从而绕过权限检查。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行 Token 的解析和验证。修改为：import jwt; payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:175-210
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中，JWT Token 仅通过 base64 解码 payload 部分，没有验证签名。攻击者可以构造任意 payload 的 JWT Token，从而绕过权限检查。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行完整的 Token 验证：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。不要手动解析 JWT。

### 案例 3
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:186-192
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中，JWT Token 的解析仅通过 base64 解码 payload 部分，完全没有验证签名。攻击者可以构造任意 payload 的 JWT Token，从而绕过权限检查，冒充任何用户。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行完整的签名验证。例如：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
