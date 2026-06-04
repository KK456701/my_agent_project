---
name: "使用 print 进行审计日志记录"
description: "审计日志使用 print() 函数输出，而不是使用 Python 的 logging 模块。print() 无法控制日志级别、无法配置输出目标（文件/网络）、无法进行日志轮转，且在生产环境中可能被重定向或丢失。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:212-213
- **描述**: 审计日志使用 print() 函数输出，而不是使用 Python 的 logging 模块。print() 无法控制日志级别、无法配置输出目标（文件/网络）、无法进行日志轮转，且在生产环境中可能被重定向或丢失。
- **修复**: 使用 logging 模块。修改为：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")

