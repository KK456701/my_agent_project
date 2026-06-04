---
name: "审计日志使用 print 而非 logging 模块"
description: "第 200 行使用 print() 记录审计日志，违反了日志管理最佳实践。print 无法控制日志级别、无法配置输出目标、不支持结构化日志，在生产环境中难以进行日志聚合和分析。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:200-201
- **描述**: 第 200 行使用 print() 记录审计日志，违反了日志管理最佳实践。print 无法控制日志级别、无法配置输出目标、不支持结构化日志，在生产环境中难以进行日志聚合和分析。
- **修复**: 使用 logging 模块：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")。

