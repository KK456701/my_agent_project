---
name: "AES CBC 模式使用固定 IV 不安全"
description: "所有加密操作都使用相同的初始化向量 ENCRYPTION_IV。在 CBC 模式下，固定 IV 会导致相同的明文产生相同的密文，且降低了加密的安全性。"
---

## 历史案例

### 案例 1
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:240
- **描述**: 所有加密操作都使用相同的初始化向量 ENCRYPTION_IV。在 CBC 模式下，固定 IV 会导致相同的明文产生相同的密文，且降低了加密的安全性。
- **修复**: 每次加密时生成随机 IV，并将 IV 与密文一起存储（如 IV + 密文）。修改为：iv = os.urandom(16); cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv); ...; return base64.b64encode(iv + encrypted).decode()

