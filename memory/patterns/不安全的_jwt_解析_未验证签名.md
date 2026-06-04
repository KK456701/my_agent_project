---
name: "不安全的 JWT 解析 — 未验证签名"
description: "auth_require_permission 装饰器中，JWT 的解析仅通过 base64 解码 payload 部分，完全没有验证签名。攻击者可以伪造任意 JWT Token，绕过认证和权限检查。此外，HMAC 计算结果未与任何预期值比较，形同虚设。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:128-155
- **描述**: auth_require_permission 装饰器中，JWT 的解析仅通过 base64 解码 payload 部分，完全没有验证签名。攻击者可以伪造任意 JWT Token，绕过认证和权限检查。此外，HMAC 计算结果未与任何预期值比较，形同虚设。
- **修复**: 使用成熟的 JWT 库（如 PyJWT）进行完整的签名验证。修改为：import jwt; payload = jwt.decode(token, secret, algorithms=['HS256'])


### 案例 2
- **日期**: 2026-06-04 17202
- **来源 PR**: feat: 增加两个新方法
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:75-83
- **描述**: isTokenValid 方法中 catch (Exception e) 捕获了所有类型的异常（包括 JWT 签名验证失败、过期、格式错误等），并统一返回 false。这种宽泛的异常捕获方式会隐藏具体的安全问题，例如：1) 如果 Token 被篡改（签名验证失败），调用方无法区分是过期还是被篡改；2) 如果 JWT 库本身存在漏洞或配置错误，异常也会被静默吞掉；3) 不利于安全审计和问题排查。
- **修复**: 建议区分不同类型的异常，至少记录日志以便安全审计。例如： ```java public static boolean isTokenValid(String token) {     try {         Claims claims = parseToken(token);         Date expiration = claims.getExpiration();         return !expiration.before(new Date());     } catch (ExpiredJwtException e) {         log.warn("Token已过期: {}", e.getMessage());         return false;     } catch (SignatureException e) {         log.warn("Token签名验证失败，可能被篡改: {}", e.getMessage());         return false;     } catch (Exception e) {       

### 案例 3
- **日期**: 2026-06-04 17202
- **来源 PR**: feat: 增加两个新方法
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:70-83
- **描述**: isTokenValid 方法使用 catch (Exception e) 捕获所有异常并返回 false，这是一种过于宽泛的异常处理策略。它会吞掉如 JWT 签名不匹配、token 格式错误、过期时间解析失败等不同类型的异常，导致调用方无法区分 token 无效的具体原因（是过期了？还是被篡改了？还是格式错误？）。这在架构上削弱了系统的可诊断性和可调试性。
- **修复**: 建议改为更细粒度的异常处理，或者返回一个包含原因的状态对象（如 TokenValidationResult 类），包含 isValid 布尔值和可选的错误原因字符串。或者至少区分 JWT 解析异常（如 ExpiredJwtException、SignatureException）和其他系统异常。
