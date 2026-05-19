# 模式: 使用 print 进行审计日志

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 logging 模块：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] ...")

## 审查次数: 2

## 历史案例

### 案例 1
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-197
- **严重程度**: medium
- **描述**: 装饰器中使用 print(f"[AUDIT] ...") 记录审计日志。print 函数不适合生产环境日志记录，因为它缺乏日志级别、时间戳格式化、输出目标控制等功能。
- **建议**: 使用 logging 模块：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] ...")

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:214-215
- **严重程度**: medium
- **描述**: 装饰器中使用 print() 函数记录审计日志，而不是使用 logging 模块。print() 无法控制日志级别、输出目标、格式化等，不适合生产环境。
- **建议**: 使用 logging 模块：import logging; logger = logging.getLogger(__name__); logger.info(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")。
