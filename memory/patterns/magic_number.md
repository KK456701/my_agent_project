# 模式: 不必要的中间列表和低效求和

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
直接累加，避免中间列表。修改为：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。将 0.15 定义为常量 TAX_RATE = 0.15。

## 审查次数: 3

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

### 案例 2
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:70-90
- **严重程度**: low
- **描述**: 函数先创建 prices 列表再求和，可以简化为直接累加。0.15 是魔法数字，应该定义为模块级常量（如 TAX_RATE = 0.15）。这违反了代码可维护性原则：魔法数字难以理解和修改，且容易在多个地方不一致。
- **建议**: 1) 定义常量 TAX_RATE = 0.15。2) 使用 sum() 和生成器表达式简化：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。

### 案例 3
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:100-112
- **严重程度**: low
- **描述**: 该函数先构建 prices 列表，再遍历求和，可以合并为一次遍历。0.15 是魔法数字，应定义为模块级常量（如 TAX_RATE = 0.15）。虽然是小问题，但反映了代码可维护性方面的不足。
- **建议**: 1. 将 0.15 定义为常量 TAX_RATE。2. 使用 sum() 和生成器表达式简化：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。
