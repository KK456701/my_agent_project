# 模式: JWT 解析未验证签名

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用成熟的 JWT 库（如 PyJWT）来解析和验证 Token。例如：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。库会自动处理签名验证、过期时间检查等。

## 审查次数: 10

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

### 案例 3
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:196-210
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中，JWT 的 payload 仅通过 base64 解码直接解析，完全没有验证签名。攻击者可以伪造任意 JWT Token，绕过认证和权限检查。后续的 HMAC 计算虽然存在，但结果未被用于任何验证，形同虚设。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行签名验证。修改为：import jwt; payload = jwt.decode(token, secret, algorithms=['HS256'])

### 案例 4
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:193-199
- **严重程度**: high
- **描述**: 装饰器 auth_require_permission 中直接使用 split 解析 JWT 的 payload，但没有验证 JWT 的签名。攻击者可以伪造任意 JWT Token，冒充任何用户或角色。
- **建议**: 使用 PyJWT 库进行完整的 JWT 验证：payload = jwt.decode(token, secret, algorithms=['HS256'])

### 案例 5
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:186-195
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中直接对 JWT 进行 base64 解码并解析 payload，但没有验证 JWT 的签名。攻击者可以伪造任意 JWT Token，从而绕过认证和权限检查。
- **建议**: 使用 PyJWT 库进行完整的 JWT 验证：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

### 案例 6
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:194-195
- **严重程度**: high
- **描述**: 装饰器中直接使用 split('.') 解析 JWT 的 payload，但没有验证 JWT 的签名。攻击者可以伪造任意 JWT Token，绕过认证。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）来解析和验证 Token。例如：import jwt; payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

### 案例 7
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:186-189
- **严重程度**: critical
- **描述**: 装饰器中直接使用 split('.') 解析 JWT 的 payload，未验证签名。攻击者可以伪造任意 JWT Token，完全绕过认证。这是严重的安全漏洞。
- **建议**: 使用 PyJWT 库进行完整的签名验证：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。

### 案例 8
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:188-189
- **严重程度**: critical
- **描述**: 装饰器中直接使用 split 解析 JWT 的 payload，但没有验证签名。攻击者可以伪造任意 JWT Token，完全绕过认证。
- **建议**: 使用 PyJWT 库进行完整的 JWT 验证：import jwt; payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。不要手动解析 JWT。

### 案例 9
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:194-199
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中，JWT Token 的解析仅通过 base64 解码 payload 部分，没有验证签名。攻击者可以伪造任意 JWT Token，从而绕过认证和权限检查。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行 Token 验证：payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])。不要手动解析 JWT。

### 案例 10
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: high
- **描述**: 在 auth_require_permission 装饰器中，JWT Token 仅通过 split 分割后 base64 解码 payload，完全没有验证签名。攻击者可以伪造任意 JWT Token，绕过认证和权限检查。后续的 HMAC 计算也没有与任何期望值进行比较，形同虚设。
- **建议**: 使用成熟的 JWT 库（如 PyJWT）进行完整的签名验证： ```python import jwt
