# 模式: Token 缓存无过期时间 — 无法处理 Token 吊销场景

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用带 TTL 的缓存实现，例如 cachetools.TTLCache： ```python from cachetools import TTLCache _TOKEN_CACHE = TTLCache(maxsize=1000, ttl=300)  # 5 分钟过期 ``` 或者每次从缓存返回前检查 Token 的 exp 声明是否已过期。

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: medium
- **描述**: _TOKEN_CACHE 字典缓存了 JWT 验证结果，但没有设置 TTL（过期时间）。这意味着即使 Token 已过期或被吊销，缓存中的旧数据仍然会被使用，直到进程重启。这违反了安全最佳实践，可能导致已注销的用户仍然可以访问系统。
- **建议**: 使用带 TTL 的缓存实现，例如 cachetools.TTLCache： ```python from cachetools import TTLCache _TOKEN_CACHE = TTLCache(maxsize=1000, ttl=300)  # 5 分钟过期 ``` 或者每次从缓存返回前检查 Token 的 exp 声明是否已过期。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
