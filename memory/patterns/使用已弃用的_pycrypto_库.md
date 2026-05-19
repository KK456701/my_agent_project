# 模式: 使用已弃用的 pycrypto 库

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 pyca/cryptography 库替代。修改为：from cryptography.fernet import Fernet

## 审查次数: 2

## 历史案例

### 案例 1
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:228-229
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数中使用了 Crypto.Cipher.AES（pycrypto 库）。该库已不再维护，存在已知的安全漏洞。
- **建议**: 使用 pyca/cryptography 库替代。修改为：from cryptography.fernet import Fernet

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:228-262
- **严重程度**: info
- **描述**: 代码使用 Crypto.Cipher.AES（pyCrypto/pycryptodome 库）。虽然 pycryptodome 仍在维护，但建议考虑使用更现代的 cryptography 库，它提供了更安全的默认值和更简洁的 API。
- **建议**: 考虑使用 cryptography 库：from cryptography.fernet import Fernet。Fernet 提供了简单且安全的对称加密方案，自动处理密钥派生、IV 生成和认证。
