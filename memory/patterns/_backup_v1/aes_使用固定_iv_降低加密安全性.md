# 模式: AES 使用固定 IV — 降低加密安全性

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
为每次加密生成随机 IV，并与密文一起存储。修改为：iv = os.urandom(16); cipher = AES.new(key, AES.MODE_CBC, iv); 并将 iv 附加到密文前或单独存储。

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:80
- **严重程度**: high
- **描述**: AES.MODE_CBC 使用了固定的初始化向量 b"fixed-iv-1234567"。固定 IV 会导致相同明文产生相同密文，破坏了语义安全性，使攻击者能够识别重复的数据模式。
- **建议**: 为每次加密生成随机 IV，并与密文一起存储。修改为：iv = os.urandom(16); cipher = AES.new(key, AES.MODE_CBC, iv); 并将 iv 附加到密文前或单独存储。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
