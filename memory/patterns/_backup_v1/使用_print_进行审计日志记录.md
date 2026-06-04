# 模式: 使用 print 进行审计日志记录

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 logging 模块。修改为：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:212-213
- **严重程度**: low
- **描述**: 审计日志使用 print() 函数输出，而不是使用 Python 的 logging 模块。print() 无法控制日志级别、无法配置输出目标（文件/网络）、无法进行日志轮转，且在生产环境中可能被重定向或丢失。
- **建议**: 使用 logging 模块。修改为：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
