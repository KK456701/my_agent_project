---
name: "审计日志使用 print 而非 logging"
description: "装饰器中使用 print 函数记录审计日志。print 不是线程安全的，且无法控制日志级别、输出目标或格式。在生产环境中，审计日志应使用标准 logging 模块或专门的日志库。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:128-155
- **描述**: 装饰器中使用 print 函数记录审计日志。print 不是线程安全的，且无法控制日志级别、输出目标或格式。在生产环境中，审计日志应使用标准 logging 模块或专门的日志库。
- **修复**: 使用 Python 的 logging 模块，配置适当的日志级别（如 INFO）和处理器（如文件处理器、SysLog 处理器）。

### 案例 2
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:212-213
- **描述**: auth_require_permission 装饰器中使用 print() 函数记录审计日志。print() 不支持日志级别、日志轮转、结构化输出等功能，不适合生产环境。
- **修复**: 使用 Python 的 logging 模块。修改为：logging.getLogger(__name__).info(f'[AUDIT] {payload.get("sub")} accessed')

### 案例 3
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-168
- **描述**: 装饰器中使用 print() 记录审计日志，这不符合生产环境要求。print() 无法控制日志级别、输出目标，也无法进行格式化。
- **修复**: 使用 logging 模块：logging.getLogger(__name__).info(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")

### 案例 4
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:206-206
- **描述**: 装饰器中使用 print() 输出审计日志，这不符合生产环境要求。print 无法控制日志级别、无法配置输出目标、不支持结构化日志。
- **修复**: 使用 logging 模块：logging.getLogger(__name__).info(f"[AUDIT] {payload.get('sub')} accessed at {time.time()}")。

