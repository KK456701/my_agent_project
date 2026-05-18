# 模式: 审计日志使用 print 而非 logging

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 Python 的 logging 模块，配置适当的日志级别（如 INFO）和处理器（如文件处理器、SysLog 处理器）。

## 审查次数: 2

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: low
- **描述**: 装饰器中使用 print 函数记录审计日志。print 不是线程安全的，且无法控制日志级别、输出目标或格式。在生产环境中，审计日志应使用标准 logging 模块或专门的日志库。
- **建议**: 使用 Python 的 logging 模块，配置适当的日志级别（如 INFO）和处理器（如文件处理器、SysLog 处理器）。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:212-213
- **严重程度**: medium
- **描述**: auth_require_permission 装饰器中使用 print() 函数记录审计日志。print() 不支持日志级别、日志轮转、结构化输出等功能，不适合生产环境。
- **建议**: 使用 Python 的 logging 模块。修改为：logging.getLogger(__name__).info(f'[AUDIT] {payload.get("sub")} accessed')
