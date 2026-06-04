---
name: "JWT 缓存永不过期导致 Token 吊销失效"
description: "_TOKEN_CACHE 缓存没有设置 TTL（过期时间），Token 一旦被缓存将永久有效。即使 Token 被吊销或过期，缓存中的 payload 仍然会被返回，导致认证绕过。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:26-35
- **描述**: _TOKEN_CACHE 缓存没有设置 TTL（过期时间），Token 一旦被缓存将永久有效。即使 Token 被吊销或过期，缓存中的 payload 仍然会被返回，导致认证绕过。
- **修复**: 为缓存添加 TTL 过期机制，例如使用 cachetools.TTLCache 或手动记录时间戳。TTL 应设置为 Token 的剩余有效期或更短。

