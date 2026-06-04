---
name: "高风险第三方库依赖 — 已知 RCE 漏洞"
description: "process_secure_transaction 函数依赖 old-crypto-lib v1.2.3，该版本存在 CVE-2024-5678（CVSS 9.8，远程代码执行）。每天 500 万次调用，攻击面极大。虽然替换成本高（重写加密层、性能降 15 倍），但 RCE 漏洞可被远程利用，风险不可接受。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-18_105740
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:23-28
- **描述**: process_secure_transaction 函数依赖 old-crypto-lib v1.2.3，该版本存在 CVE-2024-5678（CVSS 9.8，远程代码执行）。每天 500 万次调用，攻击面极大。虽然替换成本高（重写加密层、性能降 15 倍），但 RCE 漏洞可被远程利用，风险不可接受。
- **修复**: 1. 短期：在 old-crypto-lib 外层加 WAF/输入过滤，拦截可疑密文（如长度异常、非预期模式）。2. 中期：评估是否可仅替换解密函数为安全实现（如 libsodium），保留加密部分以维持性能。3. 长期：规划加密层重写，使用现代库（如 cryptography 或 libsodium），并做性能回归测试。

