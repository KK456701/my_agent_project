# 模式: 不必要的中间列表和低效求和

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
直接累加，避免中间列表。修改为：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。将 0.15 定义为常量 TAX_RATE = 0.15。

## 审查次数: 12

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

### 案例 4
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:78-95
- **严重程度**: medium
- **描述**: 0.15 作为税率是魔法数字，应定义为模块级常量以提高可读性和可维护性。同时，先收集 prices 列表再求和是不必要的中间步骤，可以直接累加。这违反了 DRY 原则和代码简洁性要求。
- **建议**: 1) 定义常量 TAX_RATE = 0.15；2) 使用 sum() 和生成器表达式简化：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。

### 案例 5
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:87-100
- **严重程度**: medium
- **描述**: calculate_order_amount 函数中，0.15 是一个魔法数字，应该定义为常量。此外，代码先创建一个中间列表 prices，然后再次遍历求和，这是不必要的。
- **建议**: 将 0.15 定义为模块级常量，例如 TAX_RATE = 0.15。使用 sum() 函数和生成器表达式简化计算：total = sum(item["price"] * item["quantity"] * TAX_RATE for item in items)

### 案例 6
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:95-107
- **严重程度**: medium
- **描述**: calculate_order_amount 函数中使用了魔法数字 0.15 作为税率。这降低了代码的可读性和可维护性，如果税率变更需要修改所有出现的位置。
- **建议**: 将税率定义为模块级常量：TAX_RATE = 0.15，并在计算时引用该常量。同时，可以使用 sum() 和生成器表达式简化计算：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)

### 案例 7
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:85-101
- **严重程度**: medium
- **描述**: 0.15 作为税率是魔法数字，应定义为模块级常量。同时，先收集所有价格再求和的做法引入了不必要的中间列表，增加了内存开销和代码复杂度。
- **建议**: 1) 定义常量 TAX_RATE = 0.15；2) 使用 sum() 和生成器表达式直接计算：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。

### 案例 8
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:82-97
- **严重程度**: medium
- **描述**: 0.15 作为税率是魔法数字，应定义为模块级常量以提高可维护性。同时，代码创建了不必要的中间列表 prices，然后再次遍历求和，违反了简洁性原则。
- **建议**: 1. 定义常量 TAX_RATE = 0.15。2. 使用 sum() 和生成器表达式简化：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。

### 案例 9
- **日期**: 2026-05-19_101230
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:86-101
- **严重程度**: medium
- **描述**: 0.15 作为税率是魔法数字，应定义为模块级常量以提高可维护性。同时，创建中间列表 prices 再求和是冗余操作，可以直接累加。这违反了代码清晰性和性能原则。
- **建议**: 1. 定义常量 TAX_RATE = 0.15。2. 使用 sum() 和生成器表达式简化：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。

### 案例 10
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:85-100
- **严重程度**: medium
- **描述**: calculate_order_amount 函数中存在两个架构问题：1) 0.15 是魔法数字，应定义为模块级常量（如 TAX_RATE = 0.15）；2) 不必要的中间列表 prices 增加了内存开销和代码复杂度，可以直接累加。
- **建议**: 1) 定义常量 TAX_RATE = 0.15；2) 使用 sum() 和生成器表达式简化：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)

### 案例 11
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:93-108
- **严重程度**: medium
- **描述**: calculate_order_amount 函数中使用了魔法数字 0.15（税率），且创建了不必要的中间列表 prices。这降低了代码的可读性和可维护性，且违反了 DRY 原则。
- **建议**: 1. 将 0.15 定义为模块级常量 TAX_RATE = 0.15。2. 使用 sum() 和生成器表达式简化计算：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)

### 案例 12
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:82-96
- **严重程度**: medium
- **描述**: calculate_order_amount 函数中存在两个架构问题：1) 0.15 是魔法数字，应定义为常量；2) 创建了不必要的中间列表 prices，可以直接累加。
- **建议**: 1) 定义模块级常量 TAX_RATE = 0.15。2) 使用 sum() 和生成器表达式简化：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)。
