# 模式: 不必要的中间列表和低效求和

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
直接累加，避免中间列表。修改为：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。将 0.15 定义为常量 TAX_RATE = 0.15。

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:96-108
- **严重程度**: medium
- **描述**: calculate_order_amount 函数先创建一个 prices 列表，再遍历求和。这导致 O(N) 的额外内存分配和两次遍历。同时，0.15 是魔法数字，应定义为常量。
- **建议**: 直接累加，避免中间列表。修改为：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。将 0.15 定义为常量 TAX_RATE = 0.15。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
