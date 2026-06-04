# 模式: 手动 PKCS7 填充 — 使用标准库替代

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用 `from Crypto.Util.Padding import pad` 替代手动填充：`padded = pad(raw.encode(), 16)`。

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:86-100
- **严重程度**: low
- **描述**: 手动实现 PKCS7 填充容易出错（如 `chr(pad)` 在 Python 3 中返回 Unicode 字符而非字节）。应使用 `Crypto.Util.Padding.pad` 或 `cryptography` 库的自动填充。
- **建议**: 使用 `from Crypto.Util.Padding import pad` 替代手动填充：`padded = pad(raw.encode(), 16)`。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
