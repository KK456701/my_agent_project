---
name: "模拟使用有已知高危CVE的第三方库"
description: "代码模拟了使用 old-crypto-lib v1.2.3 的场景，该库存在 CVE-2024-5678 (CVSS 9.8, RCE via crafted ciphertext)。这是故意设计的冲突场景，用于展示安全要求（立即移除）与架构/性能约束（替换成本高、性能下降）之间的矛盾。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_104435
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:19-20
- **描述**: 代码模拟了使用 old-crypto-lib v1.2.3 的场景，该库存在 CVE-2024-5678 (CVSS 9.8, RCE via crafted ciphertext)。这是故意设计的冲突场景，用于展示安全要求（立即移除）与架构/性能约束（替换成本高、性能下降）之间的矛盾。
- **修复**: 在真实生产环境中，应替换为受维护的加密库（如 pyca/cryptography），并评估性能影响。但此文件为测试用例，无需修改。

