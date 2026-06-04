---
name: "手动 PKCS7 填充 — 使用标准库替代"
description: "手动实现 PKCS7 填充容易出错（如 `chr(pad)` 在 Python 3 中返回 Unicode 字符而非字节）。应使用 `Crypto.Util.Padding.pad` 或 `cryptography` 库的自动填充。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:86-100
- **描述**: 手动实现 PKCS7 填充容易出错（如 `chr(pad)` 在 Python 3 中返回 Unicode 字符而非字节）。应使用 `Crypto.Util.Padding.pad` 或 `cryptography` 库的自动填充。
- **修复**: 使用 `from Crypto.Util.Padding import pad` 替代手动填充：`padded = pad(raw.encode(), 16)`。

