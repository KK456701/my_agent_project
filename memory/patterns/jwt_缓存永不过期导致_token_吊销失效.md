# 模式: JWT 缓存永不过期导致 Token 吊销失效

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
为缓存添加 TTL 过期机制，例如使用 cachetools.TTLCache 或手动记录时间戳。TTL 应设置为 Token 的剩余有效期或更短。

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:26-35
- **严重程度**: high
- **描述**: _TOKEN_CACHE 缓存没有设置 TTL（过期时间），Token 一旦被缓存将永久有效。即使 Token 被吊销或过期，缓存中的 payload 仍然会被返回，导致认证绕过。
- **建议**: 为缓存添加 TTL 过期机制，例如使用 cachetools.TTLCache 或手动记录时间戳。TTL 应设置为 Token 的剩余有效期或更短。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
