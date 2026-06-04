# 模式: HMAC 签名验证形同虚设

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 JWT 库进行完整的签名验证。如果手动实现，必须将计算出的 HMAC 值与 Token 中的签名部分进行安全比较（使用 hmac.compare_digest 防止时序攻击）。

## 审查次数: 11

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:210-212
- **严重程度**: high
- **描述**: 在 auth_require_permission 装饰器中，代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较。这导致签名验证步骤完全无效，攻击者可以伪造任意 Token。
- **建议**: 使用 JWT 库进行完整的签名验证。如果手动实现，必须将计算出的 HMAC 值与 Token 中的签名部分进行安全比较（使用 hmac.compare_digest 防止时序攻击）。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:215-220
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中计算了 HMAC 签名，但没有与任何预期值进行比较，导致签名验证完全失效。
- **建议**: 使用 PyJWT 库进行完整的签名验证，或手动比较计算出的 HMAC 值与 Token 中的签名部分。

### 案例 3
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: high
- **描述**: 装饰器中计算了 HMAC 签名，但计算结果 expected 没有与任何值进行比较，导致签名验证完全失效。攻击者可以伪造任意 JWT Token 通过认证。
- **建议**: 在计算 HMAC 后，应使用 hmac.compare_digest 将计算结果与 Token 中的签名部分进行比较。如果验证失败，应立即拒绝请求。

### 案例 4
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:204-205
- **严重程度**: high
- **描述**: auth_require_permission 装饰器中计算了 HMAC 签名，但计算结果（expected 变量）没有被用于任何比较操作，导致签名验证完全无效。同时 expected 变量被赋值但从未使用。
- **建议**: 删除无用的 HMAC 计算代码，使用 PyJWT 库进行完整的签名验证。或者，如果手动实现，需要将计算出的签名与 token 中的签名进行比较。

### 案例 5
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:204-210
- **严重程度**: high
- **描述**: 代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较。这导致签名验证完全无效，任何 Token 都会被接受。同时，expected 变量被赋值但从未使用。
- **建议**: 使用 jwt.decode 进行完整的签名验证，或手动比较 HMAC 结果：if not hmac.compare_digest(expected, token_signature): raise ValueError('Invalid signature')

### 案例 6
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:210-211
- **严重程度**: medium
- **描述**: 代码计算了 HMAC 签名，但计算结果 expected 没有被用于任何比较操作。这导致签名验证完全失效，攻击者可以任意伪造 Token。
- **建议**: 删除未使用的 expected 变量，或实现真正的签名验证逻辑。如果使用 PyJWT 库，签名验证会自动处理。

### 案例 7
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-168
- **严重程度**: medium
- **描述**: 代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较，导致签名验证完全失效。任何 Token 都会被接受。
- **建议**: 1) 使用成熟的 JWT 库（如 PyJWT）进行验证；2) 如果手动实现，必须将计算出的 HMAC 与 Token 中的签名部分进行安全比较（使用 hmac.compare_digest 防止时序攻击）。

### 案例 8
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:207-209
- **严重程度**: high
- **描述**: 代码计算了 HMAC 签名（expected = hmac.new(...)），但从未将计算结果与 Token 中的签名进行比较。这导致签名验证完全无效，任何人都可以伪造 Token。
- **建议**: 使用标准的 JWT 库进行验证，或手动比较计算出的 HMAC 与 Token 中的签名部分。例如：token_signature = token.split('.')[2]; if not hmac.compare_digest(expected, token_signature): raise ValueError('Invalid signature')

### 案例 9
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-201
- **严重程度**: high
- **描述**: 代码计算了 HMAC 签名（expected），但没有与 Token 中的签名进行比较，导致签名验证完全无效。任何 Token 都会被接受。
- **建议**: 1) 使用 PyJWT 库自动处理签名验证；2) 如果手动实现，必须比较 expected 与 Token 中的签名：token_signature = token.split('.')[2]; if not hmac.compare_digest(expected, token_signature): raise ValueError('Invalid signature')

### 案例 10
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:208-210
- **严重程度**: high
- **描述**: 代码计算了 HMAC 签名（expected = hmac.new(...)），但计算结果没有被用于任何比较或验证。这导致签名验证完全无效，任何 Token 都会被接受。
- **建议**: 1. 使用 PyJWT 库进行完整的 Token 验证。2. 如果手动实现，需要将计算出的 HMAC 与 Token 中的签名部分进行比较：actual_signature = token.split('.')[2]; expected_signature = base64.urlsafe_b64encode(hmac.new(secret.encode(), token.split('.')[0] + '.' + token.split('.')[1], hashlib.sha256).digest()).decode(); if actual_signature != expected_signature: raise ValueError('Invalid signature')

### 案例 11
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:207-208
- **严重程度**: medium
- **描述**: 代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较。这导致签名验证完全失效，任何 Token 都会被接受。
- **建议**: 使用 jwt.decode() 自动完成签名验证，或手动比较计算出的 HMAC 与 Token 中的签名。例如：expected = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest(); if expected != token_signature: raise ValueError('Invalid signature')。
