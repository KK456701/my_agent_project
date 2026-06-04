---
name: "装饰器中使用 time.sleep() 模拟频率限制 — 阻塞调用线程"
description: "auth_require_permission 装饰器中使用 time.sleep(0.01) 来模拟频率限制。这会阻塞当前线程，在同步 Web 服务器（如 Flask 默认）中会阻塞整个 worker 进程，降低并发处理能力。对于 1000 个并发请求，每个 sleep 10ms，总延迟达 10 秒。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:226-228
- **描述**: auth_require_permission 装饰器中使用 time.sleep(0.01) 来模拟频率限制。这会阻塞当前线程，在同步 Web 服务器（如 Flask 默认）中会阻塞整个 worker 进程，降低并发处理能力。对于 1000 个并发请求，每个 sleep 10ms，总延迟达 10 秒。
- **修复**: 1. 使用异步频率限制库（如 aioredis + 令牌桶算法）。2. 如果必须同步，使用非阻塞的计数器方案（如 Redis INCR + EXPIRE）。3. 移除这个模拟 sleep，改用真正的频率限制中间件。

