---
name: "Token 缓存无过期时间 — 无法处理 Token 吊销场景"
description: "_TOKEN_CACHE 字典缓存了 JWT 验证结果，但没有设置 TTL（过期时间）。这意味着即使 Token 已过期或被吊销，缓存中的旧数据仍然会被使用，直到进程重启。这违反了安全最佳实践，可能导致已注销的用户仍然可以访问系统。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:128-155
- **描述**: _TOKEN_CACHE 字典缓存了 JWT 验证结果，但没有设置 TTL（过期时间）。这意味着即使 Token 已过期或被吊销，缓存中的旧数据仍然会被使用，直到进程重启。这违反了安全最佳实践，可能导致已注销的用户仍然可以访问系统。
- **修复**: 使用带 TTL 的缓存实现，例如 cachetools.TTLCache： ```python from cachetools import TTLCache _TOKEN_CACHE = TTLCache(maxsize=1000, ttl=300)  # 5 分钟过期 ``` 或者每次从缓存返回前检查 Token 的 exp 声明是否已过期。


### 案例 2
- **日期**: 2026-06-04 17292
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:88-95
- **描述**: getRemainingTime 方法在 token 无效或已过期时返回 -1，但调用方无法区分是 token 无效还是 token 已过期。如果调用方需要针对不同情况做不同处理（如 token 无效时要求重新登录，过期时尝试刷新），则当前设计不够友好。此外，该方法每次调用都会解析 token 并计算时间差，如果高频调用（如每几秒轮询一次），会带来不必要的性能开销。
- **修复**: 1) 考虑返回 Optional<Long> 或自定义结果对象，区分无效和过期两种状态；2) 如果该方法会被高频调用，建议在 JwtUtil 或调用方增加缓存机制，避免重复解析同一 token；3) 或者将方法签名改为返回剩余秒数（更常见），并明确文档说明返回值的含义。

### 案例 3
- **日期**: 2026-06-04 17384
- **来源 PR**: My feature prtest
- **文件**: src/main/java/com/study/room/utils/JwtUtil.java`:84-101
- **描述**: getRemainingTime 方法在 token 过期或解析异常时均返回 -1。从调用方角度看，无法区分是 token 已过期还是 token 格式无效/解析失败。这种设计将两种不同的语义（'过期' vs '无效'）合并为一个返回值，可能导致调用方做出错误的业务判断。例如，对于已过期的 token，调用方可能希望执行刷新操作；而对于无效的 token，则应该要求用户重新登录。
- **修复**: 建议将方法拆分为两个：1) isTokenExpired(String token) 返回 boolean，明确判断是否过期；2) 保留 getRemainingTime 但使用 Optional<Long> 或抛出特定异常来表示无效 token。或者使用自定义结果对象（如 Result<Long, ErrorCode>）来携带更丰富的语义信息。
