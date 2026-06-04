---
name: "同步磁盘 I/O 写入导致性能瓶颈"
description: "handle_api_request 函数在峰值 5000 QPS 下，每请求写入 500 字节审计日志，产生 2.5MB/s 的同步磁盘 I/O。同步写入会阻塞请求处理线程，导致 P99 延迟飙升，且磁盘 I/O 成为系统瓶颈。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_110600
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:66-73
- **描述**: handle_api_request 函数在峰值 5000 QPS 下，每请求写入 500 字节审计日志，产生 2.5MB/s 的同步磁盘 I/O。同步写入会阻塞请求处理线程，导致 P99 延迟飙升，且磁盘 I/O 成为系统瓶颈。
- **修复**: 1. 使用异步日志写入：将日志写入操作放入后台队列（如 asyncio.Queue 或内存环形缓冲区），由专用消费者线程批量写入。2. 使用高性能日志库（如 structlog + 异步 Handler）替代直接文件写入。3. 考虑使用专用日志收集器（如 Fluentd/Logstash）或云日志服务（如 AWS CloudWatch Logs），将 I/O 压力转移到外部系统。

