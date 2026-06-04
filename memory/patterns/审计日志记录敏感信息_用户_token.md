---
name: "审计日志记录敏感信息（用户 Token）"
description: "`_write_audit_log` 函数将 `user_token` 直接记录到审计日志中。Token 是敏感的身份凭证，记录到日志中可能导致凭证泄露，尤其是在日志系统安全性不足或日志被不当访问的情况下。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_110427
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:62
- **描述**: `_write_audit_log` 函数将 `user_token` 直接记录到审计日志中。Token 是敏感的身份凭证，记录到日志中可能导致凭证泄露，尤其是在日志系统安全性不足或日志被不当访问的情况下。
- **修复**: 在记录日志前对 `user_token` 进行脱敏处理，例如只记录 Token 的前几位和后几位（如 `token_prefix****suffix`），或者记录 Token 的哈希值。

