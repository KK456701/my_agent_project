# 模式: 已弃用的 pyCrypto 库

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
改用 pyca/cryptography 库：from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:2
- **严重程度**: info
- **描述**: from Crypto.Cipher import AES 使用了已弃用的 pyCrypto 库。该库不再维护，可能存在已知安全漏洞。
- **建议**: 改用 pyca/cryptography 库：from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
