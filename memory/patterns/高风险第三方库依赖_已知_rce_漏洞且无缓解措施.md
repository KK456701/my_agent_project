---
name: "高风险第三方库依赖 — 已知 RCE 漏洞且无缓解措施"
description: "old-crypto-lib v1.2.3 存在 CVE-2024-5678 (CVSS 9.8, RCE via crafted ciphertext)，且 process_secure_transaction 每天被调用 500 万次。攻击面极大。虽然替换成本高，但当前代码没有任何缓解措施（如输入验证、沙箱隔离、WAF 规则），属于高风险暴露。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_110427
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:20-27
- **描述**: old-crypto-lib v1.2.3 存在 CVE-2024-5678 (CVSS 9.8, RCE via crafted ciphertext)，且 process_secure_transaction 每天被调用 500 万次。攻击面极大。虽然替换成本高，但当前代码没有任何缓解措施（如输入验证、沙箱隔离、WAF 规则），属于高风险暴露。
- **修复**: 1. 立即在 decrypt_payload 调用前增加密文格式校验和长度限制。2. 在解密后增加完整性校验（HMAC）。3. 启动迁移计划，优先替换此库。4. 考虑使用 sidecar 或独立进程隔离此库，限制 RCE 影响范围。

