# 模式: 审计/调试日志使用 print 而非 logging

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
改为 logging.getLogger(__name__).info/debug/warning/error()

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:212
- **严重程度**: medium
- **描述**: Skills 规则命中: print\(.*\)
- **建议**: 改为 logging.getLogger(__name__).info/debug/warning/error()

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
