# 模式: 手动实现 PKCS7 填充容易出错

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 pycryptodome 库自带的填充功能。例如：from Crypto.Util.Padding import pad; raw_data = pad(raw_data, 16)

## 审查次数: 4

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:155-175
- **严重程度**: medium
- **描述**: save_user_data_encrypted 函数手动实现了 PKCS7 填充逻辑。手动实现加密填充容易出错，可能导致数据无法正确解密或产生安全漏洞。
- **建议**: 使用 pycryptodome 库自带的填充功能。例如：from Crypto.Util.Padding import pad; raw_data = pad(raw_data, 16)

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:247-250
- **严重程度**: medium
- **描述**: 代码手动实现了 PKCS7 填充逻辑。手动实现加密原语容易出错，可能导致数据损坏或安全漏洞。
- **建议**: 使用 pycryptodome 库自带的填充工具：from Crypto.Util.Padding import pad; raw_data = pad(raw_data, 16)

### 案例 3
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:237-238
- **严重程度**: medium
- **描述**: save_user_data_encrypted 函数中手动实现了 PKCS7 填充逻辑。手动实现加密填充容易出错，可能导致解密失败或安全漏洞。
- **建议**: 使用 pycryptodome 库自带的填充工具。修改为：from Crypto.Util.Padding import pad; raw_data = pad(json.dumps(user).encode('utf-8'), 16)

### 案例 4
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:249-252
- **严重程度**: medium
- **描述**: 代码手动实现了 PKCS7 填充逻辑，但未处理边界情况（如数据长度恰好是 16 的倍数时需要填充一个完整的块）。手动实现加密填充是常见的错误来源。
- **建议**: 使用 pycryptodome 库自带的填充工具：from Crypto.Util.Padding import pad; raw_data = pad(raw_data, 16)。
