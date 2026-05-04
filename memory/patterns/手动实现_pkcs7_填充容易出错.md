# 模式: 手动实现 PKCS7 填充容易出错

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 pycryptodome 库自带的填充功能。例如：from Crypto.Util.Padding import pad; raw_data = pad(raw_data, 16)

## 审查次数: 1

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
