---
name: "装饰器中使用 time.sleep 模拟频率限制"
description: "auth_require_permission 装饰器中使用 time.sleep(0.01) 来模拟频率限制，这会阻塞当前线程 10ms。在高并发场景下，每个请求都 sleep 会严重降低吞吐量，导致请求排队。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:218-219
- **描述**: auth_require_permission 装饰器中使用 time.sleep(0.01) 来模拟频率限制，这会阻塞当前线程 10ms。在高并发场景下，每个请求都 sleep 会严重降低吞吐量，导致请求排队。
- **修复**: 使用异步频率限制方案（如令牌桶算法）或专门的限流中间件（如 Flask-Limiter），避免同步阻塞。

