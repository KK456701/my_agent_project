---
name: "HMAC 签名验证形同虚设"
description: "在 auth_require_permission 装饰器中，代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较。这导致签名验证步骤完全无效，攻击者可以伪造任意 Token。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:210-212
- **描述**: 在 auth_require_permission 装饰器中，代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较。这导致签名验证步骤完全无效，攻击者可以伪造任意 Token。
- **修复**: 使用 JWT 库进行完整的签名验证。如果手动实现，必须将计算出的 HMAC 值与 Token 中的签名部分进行安全比较（使用 hmac.compare_digest 防止时序攻击）。

### 案例 2
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:215-220
- **描述**: auth_require_permission 装饰器中计算了 HMAC 签名，但没有与任何预期值进行比较，导致签名验证完全失效。
- **修复**: 使用 PyJWT 库进行完整的签名验证，或手动比较计算出的 HMAC 值与 Token 中的签名部分。

### 案例 3
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:128-155
- **描述**: 装饰器中计算了 HMAC 签名，但计算结果 expected 没有与任何值进行比较，导致签名验证完全失效。攻击者可以伪造任意 JWT Token 通过认证。
- **修复**: 在计算 HMAC 后，应使用 hmac.compare_digest 将计算结果与 Token 中的签名部分进行比较。如果验证失败，应立即拒绝请求。

### 案例 4
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:204-205
- **描述**: auth_require_permission 装饰器中计算了 HMAC 签名，但计算结果（expected 变量）没有被用于任何比较操作，导致签名验证完全无效。同时 expected 变量被赋值但从未使用。
- **修复**: 删除无用的 HMAC 计算代码，使用 PyJWT 库进行完整的签名验证。或者，如果手动实现，需要将计算出的签名与 token 中的签名进行比较。

### 案例 5
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:204-210
- **描述**: 代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较。这导致签名验证完全无效，任何 Token 都会被接受。同时，expected 变量被赋值但从未使用。
- **修复**: 使用 jwt.decode 进行完整的签名验证，或手动比较 HMAC 结果：if not hmac.compare_digest(expected, token_signature): raise ValueError('Invalid signature')

### 案例 6
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:210-211
- **描述**: 代码计算了 HMAC 签名，但计算结果 expected 没有被用于任何比较操作。这导致签名验证完全失效，攻击者可以任意伪造 Token。
- **修复**: 删除未使用的 expected 变量，或实现真正的签名验证逻辑。如果使用 PyJWT 库，签名验证会自动处理。

### 案例 7
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-168
- **描述**: 代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较，导致签名验证完全失效。任何 Token 都会被接受。
- **修复**: 1) 使用成熟的 JWT 库（如 PyJWT）进行验证；2) 如果手动实现，必须将计算出的 HMAC 与 Token 中的签名部分进行安全比较（使用 hmac.compare_digest 防止时序攻击）。

### 案例 8
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:207-209
- **描述**: 代码计算了 HMAC 签名（expected = hmac.new(...)），但从未将计算结果与 Token 中的签名进行比较。这导致签名验证完全无效，任何人都可以伪造 Token。
- **修复**: 使用标准的 JWT 库进行验证，或手动比较计算出的 HMAC 与 Token 中的签名部分。例如：token_signature = token.split('.')[2]; if not hmac.compare_digest(expected, token_signature): raise ValueError('Invalid signature')

### 案例 9
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-201
- **描述**: 代码计算了 HMAC 签名（expected），但没有与 Token 中的签名进行比较，导致签名验证完全无效。任何 Token 都会被接受。
- **修复**: 1) 使用 PyJWT 库自动处理签名验证；2) 如果手动实现，必须比较 expected 与 Token 中的签名：token_signature = token.split('.')[2]; if not hmac.compare_digest(expected, token_signature): raise ValueError('Invalid signature')

### 案例 10
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:208-210
- **描述**: 代码计算了 HMAC 签名（expected = hmac.new(...)），但计算结果没有被用于任何比较或验证。这导致签名验证完全无效，任何 Token 都会被接受。
- **修复**: 1. 使用 PyJWT 库进行完整的 Token 验证。2. 如果手动实现，需要将计算出的 HMAC 与 Token 中的签名部分进行比较：actual_signature = token.split('.')[2]; expected_signature = base64.urlsafe_b64encode(hmac.new(secret.encode(), token.split('.')[0] + '.' + token.split('.')[1], hashlib.sha256).digest()).decode(); if actual_signature != expected_signature: raise ValueError('Invalid signature')

### 案例 11
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:207-208
- **描述**: 代码计算了 HMAC 签名，但没有将计算结果与 Token 中的签名进行比较。这导致签名验证完全失效，任何 Token 都会被接受。
- **修复**: 使用 jwt.decode() 自动完成签名验证，或手动比较计算出的 HMAC 与 Token 中的签名。例如：expected = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest(); if expected != token_signature: raise ValueError('Invalid signature')。


### 案例 12
- **日期**: 2026-06-04 17202
- **来源 PR**: feat: 增加两个新方法
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:76-83
- **描述**: isTokenValid 方法捕获了 Exception 顶级异常，这意味着任何异常（包括潜在的解析性能问题、网络超时等）都会被静默吞掉并返回 false。在性能调优或故障排查时，这种宽泛的异常处理会掩盖真正的性能瓶颈（如 JWT 签名验证耗时过长、密钥加载失败等），导致问题难以定位。
- **修复**: 建议捕获更具体的异常类型，例如：SignatureException（签名无效）、ExpiredJwtException（已过期）、MalformedJwtException（格式错误）。对于非预期的异常，至少应记录日志以便排查。
