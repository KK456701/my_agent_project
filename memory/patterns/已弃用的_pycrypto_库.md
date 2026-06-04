---
name: "已弃用的 pyCrypto 库"
description: "from Crypto.Cipher import AES 使用了已弃用的 pyCrypto 库。该库不再维护，可能存在已知安全漏洞。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:2
- **描述**: from Crypto.Cipher import AES 使用了已弃用的 pyCrypto 库。该库不再维护，可能存在已知安全漏洞。
- **修复**: 改用 pyca/cryptography 库：from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

