# 模式: 不必要的中间列表 — 先 append 再遍历

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
直接在循环中累加 total，省去 prices 列表：total = 0; for item in items: total += item['price'] * item['quantity'] * 0.15; return total。

## 审查次数: 1

## 历史案例

### 案例 1
- **日期**: 2026-05-19_101230
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:88-101
- **严重程度**: medium
- **描述**: calculate_order_amount 函数先构建 prices 列表，再遍历求和。这浪费了 O(n) 的额外内存（n 为 items 数量）。对于大量订单项，内存占用翻倍。
- **建议**: 直接在循环中累加 total，省去 prices 列表：total = 0; for item in items: total += item['price'] * item['quantity'] * 0.15; return total。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。
