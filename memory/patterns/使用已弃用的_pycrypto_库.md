---
name: "使用已弃用的 pycrypto 库"
description: "save_user_data_encrypted 函数中使用了 Crypto.Cipher.AES（pycrypto 库）。该库已不再维护，存在已知的安全漏洞。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:228-229
- **描述**: save_user_data_encrypted 函数中使用了 Crypto.Cipher.AES（pycrypto 库）。该库已不再维护，存在已知的安全漏洞。
- **修复**: 使用 pyca/cryptography 库替代。修改为：from cryptography.fernet import Fernet

### 案例 2
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:228-262
- **描述**: 代码使用 Crypto.Cipher.AES（pyCrypto/pycryptodome 库）。虽然 pycryptodome 仍在维护，但建议考虑使用更现代的 cryptography 库，它提供了更安全的默认值和更简洁的 API。
- **修复**: 考虑使用 cryptography 库：from cryptography.fernet import Fernet。Fernet 提供了简单且安全的对称加密方案，自动处理密钥派生、IV 生成和认证。

