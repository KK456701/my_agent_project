# 模式: Token 缓存无过期机制 — 无法处理 Token 吊销

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用带 TTL 的缓存（如 cachetools.TTLCache）或 Redis 并设置合理的过期时间。修改为：from cachetools import TTLCache; _TOKEN_CACHE = TTLCache(maxsize=1000, ttl=300)

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:155
- **严重程度**: high
- **描述**: _TOKEN_CACHE 中的缓存条目没有设置 TTL（过期时间）。即使 Token 已被吊销或过期，缓存仍会返回旧的 payload，导致已失效的 Token 仍能通过权限检查。这是一个严重的安全漏洞。
- **建议**: 使用带 TTL 的缓存（如 cachetools.TTLCache）或 Redis 并设置合理的过期时间。修改为：from cachetools import TTLCache; _TOKEN_CACHE = TTLCache(maxsize=1000, ttl=300)

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
