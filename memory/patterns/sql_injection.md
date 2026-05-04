# 模式: SQL 注入漏洞

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

## 审查次数: 16

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:42
- **严重程度**: critical
- **描述**: 在 login_user 函数中，username 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 username 参数，例如 ' OR '1'='1，来绕过身份验证或执行任意 SQL 命令。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:73
- **严重程度**: high
- **描述**: 在 get_user_orders_n_plus_1 函数中，user_id 变量通过 f-string 直接拼接到 SQL 查询中。虽然 user_ids 参数被声明为 list[int]，但如果调用方传入非预期的数据，仍可能导致 SQL 注入。
- **建议**: 使用参数化查询。修改为：cursor.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))

### 案例 3
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: medium
- **描述**: sanitize_user_input_batch 函数中的正则表达式 re.sub(r'(SELECT|INSERT|DELETE|DROP|UNION)\s', '', value, flags=re.IGNORECASE) 试图通过删除 SQL 关键字来防止注入。这种方法极易被绕过（例如使用大小写混合、注释符、URL 编码等），并且会破坏包含这些单词的正常文本。
- **建议**: 不要依赖黑名单或关键字过滤来防止 SQL 注入。始终使用参数化查询或 ORM 框架。

### 案例 4
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:268
- **严重程度**: critical
- **描述**: 在 save_user_data_encrypted 函数中，user['id'] 和 encoded 变量通过 f-string 直接拼接到 SQL 查询中。攻击者可以控制 user['id'] 的值，从而执行 SQL 注入攻击。
- **建议**: 使用参数化查询。修改为：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))

### 案例 5
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:297
- **严重程度**: high
- **描述**: 在 get_config_with_cache 函数中，key 变量通过 f-string 直接拼接到 SQL 查询中。攻击者可以控制 key 参数，从而执行 SQL 注入攻击。
- **建议**: 使用参数化查询。修改为：cursor.execute("SELECT value FROM config WHERE key = ?", (key,))

### 案例 6
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:80-93
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数在循环内逐条执行 SQL 查询，当 user_ids 列表长度为 N 时，会产生 N+1 次数据库查询。每次查询都有网络往返和 SQL 解析开销，时间复杂度 O(N) 次查询，而非 O(1) 次。对于 1000 个用户，将产生 1000 次查询，而使用 IN 子句只需 1 次。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单，将时间复杂度从 O(N) 次查询降为 O(1) 次查询。同时使用参数化查询防止 SQL 注入。

### 案例 7
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: medium
- **描述**: 所有函数直接依赖具体的 sqlite3 连接和文件系统，没有通过接口或抽象类解耦。这使得： 1. 单元测试需要真实的数据库文件，无法轻松 mock。 2. 未来切换数据库（如从 SQLite 迁移到 PostgreSQL）需要修改所有函数。 3. 加密、缓存等横切关注点与业务逻辑紧密耦合。
- **建议**: 1. 为数据库操作定义 Repository 接口（如 UserRepository, OrderRepository）。

### 案例 8
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: low
- **描述**: 部分函数名与实际行为不完全匹配： 1. get_user_orders_n_plus_1 名字暴露了实现细节（N+1），应该叫 get_user_orders。 2. sanitize_user_input_batch 实际做了 XSS 过滤和 SQL 关键字过滤，但名字只说了“清洗”。 3. hash_password 返回的是 salt+hash 的拼接字符串，不是纯哈希值。
- **建议**: 1. 使用描述行为而非实现的命名：get_user_orders_by_ids。

### 案例 9
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:42
- **严重程度**: critical
- **描述**: 在 login_user 函数中，username 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 username 参数，例如 ' OR '1'='1，来绕过身份验证或执行任意 SQL 命令。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

### 案例 10
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:73
- **严重程度**: high
- **描述**: 在 get_user_orders_n_plus_1 函数中，user_id 变量通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意的 user_id 参数，执行任意 SQL 命令。
- **建议**: 使用参数化查询。修改为：cursor.execute("SELECT * FROM orders WHERE user_id = ?", (user_id,))

### 案例 11
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:155-175
- **严重程度**: high
- **描述**: 在 save_user_data_encrypted 函数中，user['id'] 变量通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意的 user['id'] 参数，执行任意 SQL 命令。
- **建议**: 使用参数化查询。修改为：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))

### 案例 12
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:280-290
- **严重程度**: high
- **描述**: 在 get_config_with_cache 函数中，key 变量通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意的 key 参数，执行任意 SQL 命令。
- **建议**: 使用参数化查询。修改为：cursor.execute("SELECT value FROM config WHERE key = ?", (key,))

### 案例 13
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:73-85
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数中，对 user_ids 列表中的每个 user_id 都执行一次独立的 SQL 查询。如果 user_ids 有 N 个元素，就会产生 N 次数据库查询（加上一次连接），时间复杂度为 O(N) 次网络往返。对于 1000 个用户，就是 1000 次查询，而使用 IN 子句只需 1 次。
- **建议**: 使用 SQL 的 IN 子句一次查询所有用户的订单，将循环查询改为批量查询。修改为：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join('?' * len(user_ids))})", user_ids)

### 案例 14
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: high
- **描述**: 整个文件将数据库操作、认证逻辑、业务计算、输入清洗、加密、缓存、装饰器等多种职责混合在一个模块中。这导致模块高度耦合，难以独立测试、维护和扩展。例如，login_user 函数同时处理了数据库连接、SQL 查询、密码比较和结果格式化。
- **建议**: 按照职责进行模块拆分：将数据库连接封装为独立的 Data Access Layer（如 db.py），将认证逻辑封装为 auth.py，将业务计算封装为 order.py，将输入清洗封装为 sanitizer.py，将加密逻辑封装为 crypto.py，将缓存逻辑封装为 cache.py。每个模块只负责一个明确的职责。

### 案例 15
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:175-195
- **严重程度**: high
- **描述**: 在 save_user_data_encrypted 函数中，user['id'] 通过 f-string 直接拼接到 SQL 查询中，存在 SQL 注入风险。攻击者可以通过构造恶意的 user['id'] 来执行任意 SQL 命令。
- **建议**: 使用参数化查询：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))

### 案例 16
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:210-230
- **严重程度**: high
- **描述**: get_config_with_cache 函数使用全局字典 _CONFIG_CACHE 作为缓存，存在以下架构问题：1) 无 TTL 和淘汰策略，导致内存泄漏；2) 线程不安全；3) 缓存中可能存储敏感配置（如 API Key），无访问控制；4) 存在 SQL 注入漏洞。
- **建议**: 1) 使用带 TTL 的线程安全缓存，如 cachetools.TTLCache。2) 对敏感配置进行加密存储或使用专门的配置服务。3) 使用参数化查询修复 SQL 注入。4) 考虑使用 Redis 等外部缓存服务，便于集中管理和过期。
