---
name: "审计/调试日志使用 print 而非 logging"
description: "Skills 规则命中: print\(.*\)"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:212
- **描述**: Skills 规则命中: print\(.*\)
- **修复**: 改为 logging.getLogger(__name__).info/debug/warning/error()

### 案例 2
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:212
- **描述**: Skills 规则命中: print\(.*\)
- **修复**: 改为 logging.getLogger(__name__).info/debug/warning/error()

