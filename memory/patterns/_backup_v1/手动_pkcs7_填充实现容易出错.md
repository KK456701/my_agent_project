# 模式: 手动 PKCS7 填充实现容易出错

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 pycryptodome 的 Crypto.Util.Padding.pad 和 unpad 函数，或者使用 cryptography 库的 padding 模块。修改为：from Crypto.Util.Padding import pad; raw_data = pad(raw_data, 16)

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:238-260
- **严重程度**: medium
- **描述**: 手动实现 PKCS7 填充逻辑，虽然当前实现正确，但增加了代码复杂度和出错风险。标准库提供了更可靠的方案。
- **建议**: 使用 pycryptodome 的 Crypto.Util.Padding.pad 和 unpad 函数，或者使用 cryptography 库的 padding 模块。修改为：from Crypto.Util.Padding import pad; raw_data = pad(raw_data, 16)

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
