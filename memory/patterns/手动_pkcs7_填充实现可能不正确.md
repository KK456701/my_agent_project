# 模式: 手动 PKCS7 填充实现可能不正确

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 pycryptodome 库的 pad 函数：from Crypto.Util.Padding import pad; padded = pad(raw.encode(), 16)

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:82-86
- **严重程度**: medium
- **描述**: 手动实现的 PKCS7 填充使用 chr(pad) * pad 生成填充字节。如果原始数据长度恰好是 16 的倍数，当前代码不会添加额外的 16 字节填充块，这违反了 PKCS7 标准（必须始终填充）。解密时可能无法正确去除填充。
- **建议**: 使用 pycryptodome 库的 pad 函数：from Crypto.Util.Padding import pad; padded = pad(raw.encode(), 16)

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
