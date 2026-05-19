# 模式: SQL 注入漏洞

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

## 审查次数: 81

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

### 案例 17
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:73
- **严重程度**: info
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 18
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:261
- **严重程度**: critical
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 19
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:295
- **严重程度**: critical
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 20
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:68-79
- **严重程度**: critical
- **描述**: 在 get_user_orders_n_plus_1 函数中，对 user_ids 列表中的每个 user_id 都执行一次独立的 SQL 查询。如果 user_ids 有 1000 个元素，就会产生 1000 次数据库往返（N+1 次查询），而实际上只需要 1 次查询即可。这会导致严重的性能瓶颈，尤其是在高并发场景下。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单，将 N+1 次查询降为 1 次。修改为：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)

### 案例 21
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:73
- **严重程度**: info
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 22
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:261
- **严重程度**: critical
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 23
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:295
- **严重程度**: critical
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 24
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:68-79
- **严重程度**: critical
- **描述**: 在 get_user_orders_n_plus_1 函数中，对 user_ids 列表中的每个 user_id 都执行一次独立的 SQL 查询。如果 user_ids 有 1000 个元素，就会产生 1000 次数据库往返（N+1 次查询），而实际上只需要 1 次查询即可。这会导致严重的性能瓶颈，尤其是在高并发场景下。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单，将 N+1 次查询降为 1 次。修改为：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)

### 案例 25
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:68-79
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数在循环结束后才关闭数据库连接，但如果循环中发生异常（如 SQL 执行失败），conn.close() 将不会执行，导致数据库连接泄漏。长期运行会耗尽连接池资源。
- **建议**: 使用 try-finally 或 with 语句确保连接始终被关闭。修改为：conn = get_db(); try: ... finally: conn.close()

### 案例 26
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: medium
- **描述**: sanitize_user_input_batch 函数同时处理了XSS过滤、字符清洗、SQL关键字过滤三种不同安全策略，且正则表达式硬编码在函数内部。这违反了单一职责和开闭原则：添加新的清洗规则需要修改函数本身，且无法复用单个清洗策略。
- **建议**: 1) 将清洗策略拆分为独立的函数/类：remove_xss()、sanitize_special_chars()、prevent_sql_injection()。2) 使用策略模式或责任链模式组合清洗规则。3) 将正则表达式提取为模块级常量或配置。

### 案例 27
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:73
- **严重程度**: info
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 28
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:261
- **严重程度**: critical
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 29
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:295
- **严重程度**: critical
- **描述**: Skills 规则命中: execute\(f"
- **建议**: 使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))

### 案例 30
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:44-45
- **严重程度**: critical
- **描述**: login_user 函数中，username 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 username 参数，例如 ' OR '1'='1，从而绕过认证并获取所有用户数据。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute('SELECT * FROM users WHERE username = ?', (username,))

### 案例 31
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:73-74
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数中，user_id 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 user_id 参数，例如 1; DROP TABLE orders;--，从而执行任意 SQL 命令。
- **建议**: 使用参数化查询。修改为：cursor.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))

### 案例 32
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:261-262
- **严重程度**: critical
- **描述**: save_user_data_encrypted 函数中，user['id'] 和 encoded 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 user['id'] 或加密数据，从而执行任意 SQL 命令。
- **建议**: 使用参数化查询。修改为：cursor.execute('INSERT INTO users_encrypted (id, data) VALUES (?, ?)', (user['id'], encoded))

### 案例 33
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:295-296
- **严重程度**: critical
- **描述**: get_config_with_cache 函数中，key 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 key 参数，例如 ' UNION SELECT password FROM users;--，从而窃取敏感数据。
- **建议**: 使用参数化查询。修改为：cursor.execute('SELECT value FROM config WHERE key = ?', (key,))

### 案例 34
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:72-82
- **严重程度**: critical
- **描述**: 在 get_user_orders_n_plus_1 函数中，对每个 user_id 都执行一次独立的 SQL 查询。如果 user_ids 有 1000 个元素，就会产生 1001 次数据库往返（1 次连接 + 1000 次查询），时间复杂度 O(N)。
- **建议**: 使用 SQL IN 子句一次查询所有订单，将数据库往返次数降为 2 次（连接 + 查询）。修改为：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)，然后按 user_id 分组。

### 案例 35
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:60-63
- **严重程度**: info
- **描述**: keyword 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 keyword 参数，例如 ' OR 1=1 --，导致 SQL 注入攻击，可能泄露、篡改或删除数据库中的所有数据。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM orders WHERE title LIKE ?", ('%' + keyword + '%',))

### 案例 36
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:82-86
- **严重程度**: critical
- **描述**: 在 save_user_data_encrypted 函数中，user['id'] 和 encrypted.hex() 通过 f-string 拼接到 SQL 查询中。虽然 encrypted.hex() 是十六进制字符串相对安全，但 user['id'] 来自用户数据，可能包含恶意 SQL 代码，导致 SQL 注入攻击。
- **建议**: 使用参数化查询。修改为：db.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encrypted.hex()))

### 案例 37
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:66-72
- **严重程度**: critical
- **描述**: search_orders 函数使用 f-string 直接将 keyword 拼接到 SQL 查询中，攻击者可以构造恶意 keyword 参数执行任意 SQL 命令。虽然注释提到参数化可能导致索引失效，但这是错误的假设：参数化查询不会导致索引失效，优化器会根据参数值选择执行计划。
- **建议**: 使用参数化查询：cursor.execute("SELECT * FROM orders WHERE title LIKE ?", (f'%{keyword}%',))。如果担心参数嗅探问题，可以使用 OPTION (RECOMPILE) 或查询提示。

### 案例 38
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:86-100
- **严重程度**: high
- **描述**: 1. 在循环外创建 cipher 对象，但 CBC 模式要求每个加密操作使用不同的 IV，固定 IV 会破坏加密安全性。2. 循环内每次执行 db.execute() 而不是批量插入，导致 10000 次数据库往返。3. 使用 f-string 拼接 SQL 存在注入风险。
- **建议**: 1. 为每条记录生成随机 IV 并存储。2. 使用 executemany() 批量插入：db.executemany("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", batch_data)。3. 使用参数化查询。4. 考虑使用数据库 TDE 替代应用层加密以减少性能开销。

### 案例 39
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:86-100
- **严重程度**: medium
- **描述**: 循环内每次调用 db.execute() 插入一条记录，对于 10000 条数据需要 10000 次数据库往返，网络延迟和事务开销巨大。
- **建议**: 收集所有加密后的数据，使用 executemany() 或批量 INSERT 语句一次提交：db.executemany("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", [(u['id'], enc.hex()) for u, enc in zip(users, encrypted_data)])

### 案例 40
- **日期**: 2026-05-18_105740
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:87-97
- **严重程度**: medium
- **描述**: create_order 函数在 API Gateway 已做完整校验的情况下，再次执行相同的校验逻辑（类型、长度、SQL 注入、XSS）。虽然深度防御是安全最佳实践，但这里的问题在于：1) 校验逻辑完全重复，没有增加新的安全价值；2) 消耗了 50% 的请求处理时间。
- **建议**: 优化深度防御策略：1) 应用层只校验 Gateway 无法校验的业务规则（如库存检查、价格计算）；2) 对 Gateway 已校验的字段使用轻量级校验（如类型检查），跳过重复的注入检测；3) 使用缓存或预编译的正则表达式减少校验开销；4) 考虑将校验逻辑下沉到 API Gateway 层，应用层只做业务校验。

### 案例 41
- **日期**: 2026-05-18_105740
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:93-100
- **严重程度**: medium
- **描述**: create_order 函数在 API Gateway 已做输入校验后，再次执行类型、长度、SQL 注入、XSS 等校验。根据描述，50% 的请求处理时间花在重复校验上。对于 3000 QPS 的峰值，这是显著的 CPU 浪费。
- **建议**: 1. 信任 API Gateway 的校验结果，移除应用层重复校验，仅在关键路径保留必要校验（如业务规则校验）。2. 如果深度防御是硬性要求，将校验逻辑移至中间件层统一处理，避免每个业务函数重复实现。3. 使用缓存校验结果（如对同一请求的校验结果做 memoization），减少重复计算。

### 案例 42
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:107-114
- **严重程度**: info
- **描述**: get_users_orders 函数中，username 变量通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意的 username 参数，例如 "' OR '1'='1"，导致查询所有用户的订单数据，造成数据泄露。这是最经典的 SQL 注入漏洞，严重程度为 critical。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM orders WHERE username = ?", (name,))。注意：参数化查询后，username 中的特殊字符会被自动转义，无需手动过滤。

### 案例 43
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:100-115
- **严重程度**: critical
- **描述**: get_users_orders 函数同时存在两个严重问题：1) SQL 注入：username 通过 f-string 直接拼接到 SQL 查询中，攻击者可以构造恶意 username 参数执行任意 SQL；2) N+1 查询：在 for 循环内逐条执行数据库查询，对于 1000 个用户名，会产生 1001 次数据库往返。这两个问题在同一行代码上（query = f"SELECT * FROM
- **建议**: 同时修复两个问题：使用参数化查询 + IN 子句批量查询。示例：placeholders = ','.join(['?'] * len(usernames)); cursor.execute(f"SELECT * FROM orders WHERE username IN ({placeholders})", usernames)。这样既防止了 SQL 注入（参数化查询），又将 N+1 次查询降为 1 次（批量查询）。注意：IN 子句的参数化在 SQLite 中支持，但在某些数据库（如 MySQL）中需要注意参数数量限制。

### 案例 44
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:82-87
- **严重程度**: critical
- **描述**: 在 save_user_data_encrypted 函数中，user['id'] 和 encrypted.hex() 直接通过 f-string 拼接到 SQL 查询中。虽然 encrypted.hex() 是十六进制字符串相对安全，但 user['id'] 来自用户输入，存在 SQL 注入风险。
- **建议**: 使用参数化查询：db.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encrypted.hex()))

### 案例 45
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:72-80
- **严重程度**: critical
- **描述**: 在 search_orders 函数中，keyword 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 keyword 参数，例如 ' OR 1=1 --'，从而执行任意 SQL 命令。这是最严重的安全漏洞之一。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于大多数数据库驱动，应使用 %s 或 ? 占位符。修改为：cursor.execute("SELECT * FROM orders WHERE title LIKE ?", (f'%{keyword}%',))

### 案例 46
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:88-101
- **严重程度**: critical
- **描述**: 在 save_user_data_encrypted 函数中，user['id'] 和 encrypted.hex() 直接通过 f-string 拼接到 INSERT 语句中。如果 user['id'] 来自用户输入，攻击者可以构造恶意 ID 执行 SQL 注入。
- **建议**: 使用参数化查询：db.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encrypted.hex()))

### 案例 47
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:68
- **严重程度**: info
- **描述**: 在 search_orders 函数中，keyword 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 keyword 参数，例如 ' OR 1=1 --，导致数据泄露或破坏。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM orders WHERE title LIKE ?", ('%' + keyword + '%',))

### 案例 48
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:93-94
- **严重程度**: critical
- **描述**: 在 save_user_data_encrypted 函数中，encrypted.hex() 直接通过 f-string 拼接到 SQL 查询字符串中。虽然 encrypted.hex() 只包含十六进制字符，但攻击者如果能够控制 user['id'] 或加密前的数据，仍可能通过构造特殊数据导致注入。
- **建议**: 使用参数化查询：db.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encrypted.hex()))

### 案例 49
- **日期**: 2026-05-18_134209
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:108-115
- **严重程度**: info
- **描述**: get_users_orders 函数中，username 变量通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意的 username 参数（如 "' OR '1'='1"）来执行任意 SQL 命令，导致数据泄露、篡改或删除。
- **建议**: 使用参数化查询（prepared statement）。对于 sqlite3，应使用 ? 占位符。修改为：query = 'SELECT * FROM orders WHERE username = ?'; cursor.execute(query, (name,))

### 案例 50
- **日期**: 2026-05-18_134209
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:108-118
- **严重程度**: critical
- **描述**: get_users_orders 函数存在双重问题：1) 在 for 循环内逐条执行数据库查询，如果 usernames 有 1000 个元素，将产生 1001 次数据库往返（1 次连接 + 1000 次查询），复杂度 O(n)。2) username 直接通过 f-string 拼接到 SQL 中，攻击者可构造恶意 username 如 "' OR '1'='1" 导致数据泄露。
- **建议**: 同时修复两个问题：使用参数化查询 + IN 子句批量查询。修改为：query = "SELECT * FROM orders WHERE username IN ({})".format(','.join(['?']*len(usernames))); cursor.execute(query, usernames)。这样将 1000 次查询降为 1 次，同时消除 SQL 注入风险。注意：如果 usernames 列表过大（>1000），应分批查询。

### 案例 51
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:62-76
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数在 for 循环内逐条执行 SQL 查询。如果 user_ids 有 1000 个元素，将产生 1000 次数据库往返（1 次初始 + 1000 次循环 = 1001 次查询），而使用 IN 子句仅需 2 次查询。时间复杂度从 O(1) 退化为 O(N)。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)，然后在 Python 中按 user_id 分组。

### 案例 52
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:33-56
- **严重程度**: high
- **描述**: login_user 函数同时承担了数据库连接管理、SQL 查询、密码验证和用户信息返回等多重职责。这种耦合导致：1) 难以单独测试认证逻辑；2) 数据库变更会影响认证流程；3) 密码比较逻辑与业务逻辑混在一起。
- **建议**: 将认证逻辑拆分为独立层：1) 创建 UserRepository 类处理数据库操作；2) 创建 AuthService 类处理密码验证和 Token 生成；3) 使用依赖注入传入数据库连接。

### 案例 53
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:67-80
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数在 for 循环内逐条执行 SQL 查询。如果 user_ids 有 1000 个元素，将产生 1000 次数据库往返（1 次初始查询 + 1000 次循环查询 = 1001 次）。每次查询都有网络 I/O 和 SQL 解析开销，导致 O(n) 的数据库连接次数，严重影响吞吐量。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)。这将把 N+1 次查询降为 2 次（1 次查询 + 1 次结果处理）。

### 案例 54
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:36-52
- **严重程度**: critical
- **描述**: login_user 函数同时承担了数据库连接管理、SQL 查询构建、密码验证、结果序列化等多重职责。这种耦合导致：1) 无法单独测试认证逻辑（必须依赖真实数据库）；2) 密码比较策略变更需要修改整个函数；3) 数据库连接未在 finally 中关闭，存在资源泄漏风险。
- **建议**: 1) 将数据库操作抽取为独立的 Repository 层；2) 使用参数化查询替代 f-string 拼接；3) 密码比较应使用专门的密码验证库（如 bcrypt.checkpw）；4) 使用上下文管理器管理数据库连接。

### 案例 55
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:248-248
- **严重程度**: critical
- **描述**: 第 248 行将 user['id'] 直接通过 f-string 拼接到 INSERT 语句中。攻击者可以构造恶意的 id 值执行任意 SQL 命令，导致数据泄露或破坏。
- **建议**: 使用参数化查询：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))。

### 案例 56
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:283-283
- **严重程度**: critical
- **描述**: 第 283 行将 key 参数直接拼接到 SQL 查询中。虽然配置键通常是内部值，但作为公共函数，攻击者仍可能通过构造恶意的 key 参数进行 SQL 注入。
- **建议**: 使用参数化查询：cursor.execute("SELECT value FROM config WHERE key = ?", (key,))。

### 案例 57
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:50-51
- **严重程度**: high
- **描述**: 密码以明文形式存储并与用户输入的密码直接进行字符串比较。如果数据库被泄露，所有用户的密码将直接暴露。即使数据库未泄露，攻击者也可能通过 SQL 注入获取密码哈希（如果使用哈希）或直接获取明文密码。
- **建议**: 使用 bcrypt 或 argon2 等安全的密码哈希算法。存储时使用 bcrypt.hashpw(password.encode(), bcrypt.gensalt())，验证时使用 bcrypt.checkpw(password.encode(), stored_hash.encode())

### 案例 58
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:253-270
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在循环内逐条执行 INSERT 语句。对于 10000 条记录，将产生 10000 次数据库往返。每次往返都有网络 I/O、SQL 解析、事务日志写入等开销。
- **建议**: 使用 executemany() 批量插入：cursor.executemany("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", [(user['id'], encoded) for user in users])。这将数据库往返从 N 次降为 1 次，性能提升 10-100 倍。

### 案例 59
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:57-72
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数在循环内逐用户执行 SQL 查询，导致 N+1 性能问题。同时，数据库连接在函数末尾关闭，但若中间发生异常则连接永远不会关闭（资源泄漏）。这违反了异常安全原则和资源管理最佳实践。
- **建议**: 1) 使用 IN 子句一次查询所有用户的订单：cursor.execute("SELECT * FROM orders WHERE user_id IN ({seq})".format(seq=','.join('?' * len(user_ids))), user_ids)；2) 使用 with 语句或 try/finally 确保连接关闭；3) 考虑使用 ORM 的预加载机制。

### 案例 60
- **日期**: 2026-05-19_094200
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:68-80
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数在 for 循环内逐条执行 SQL 查询。如果 user_ids 有 1000 个元素，会产生 1000 次数据库往返（1 次初始查询 + 1000 次循环查询 = 1001 次查询）。数据库连接和查询的建立/销毁开销极大，随着用户数增长，性能呈线性恶化。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)。将 N+1 次数据库往返降为 2 次（1 次查询 + 1 次结果获取）。

### 案例 61
- **日期**: 2026-05-19_094200
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:42-56
- **严重程度**: critical
- **描述**: login_user 函数同时负责数据库连接、SQL 查询、密码比较和结果组装。这种耦合导致：1) 无法单独测试认证逻辑；2) 修改数据库实现会影响认证逻辑；3) 密码比较策略（明文 vs 哈希）与查询逻辑绑定，难以切换。
- **建议**: 将认证逻辑拆分为三层：1) Repository 层负责数据库操作（参数化查询）；2) Service 层负责密码验证和业务逻辑；3) Controller 层负责请求响应。使用依赖注入传递数据库连接。

### 案例 62
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:69-80
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数在 for 循环内逐条执行 SQL 查询。如果 user_ids 有 N 个元素，将产生 N+1 次数据库往返（1 次连接 + N 次查询）。当 N=1000 时，数据库往返次数从 2 次（使用 IN 子句）增加到 1001 次，性能下降约 500 倍。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)，然后按 user_id 分组到 result 字典中。

### 案例 63
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:42-43
- **严重程度**: critical
- **描述**: 在 login_user 函数中，username 变量直接通过 f-string 拼接到 SQL 查询字符串中。攻击者可以构造恶意的 username 参数，例如 ' OR '1'='1，来绕过认证或获取所有用户数据。
- **建议**: 使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

### 案例 64
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:253-254
- **严重程度**: critical
- **描述**: 在 save_user_data_encrypted 函数中，user['id'] 和 encoded 变量直接通过 f-string 拼接到 SQL 查询中，存在 SQL 注入风险。
- **建议**: 使用参数化查询：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))

### 案例 65
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:224-252
- **严重程度**: high
- **描述**: user['id'] 通过 f-string 直接拼接到 SQL INSERT 语句中。虽然 user 来自内部数据，但如果数据源不可信（如用户上传的 CSV），攻击者可以构造恶意 ID 执行 SQL 注入。
- **建议**: 使用参数化查询：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))

### 案例 66
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:273-301
- **严重程度**: high
- **描述**: key 参数通过 f-string 直接拼接到 SQL 查询字符串中。如果 key 来自用户输入（如 HTTP 请求参数），攻击者可以构造恶意输入执行任意 SQL 命令。
- **建议**: 使用参数化查询：cursor.execute("SELECT value FROM config WHERE key = ?", (key,))

### 案例 67
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:63-76
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数在循环内对每个 user_id 执行单独的 SQL 查询。如果有 N 个用户，就会执行 N+1 次查询（1 次获取用户列表，N 次获取订单），导致严重的性能问题。
- **建议**: 使用单个 SQL 查询，通过 IN 子句一次性获取所有用户的订单。例如：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join('?' * len(user_ids))})", user_ids)。然后按 user_id 对结果进行分组。

### 案例 68
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:66-80
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数在 for 循环内逐条执行 SQL 查询。如果 user_ids 有 1000 个元素，将产生 1000 次数据库往返（1 次初始查询 + 1000 次子查询），而实际只需要 1 次批量查询。复杂度从 O(1) 数据库往返变为 O(N)。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)。将 N+1 次数据库往返降为 2 次。

### 案例 69
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-224
- **严重程度**: critical
- **描述**: 在 INSERT 语句中，user['id'] 通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意的 user['id'] 值，执行任意 SQL 命令。
- **建议**: 使用参数化查询：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))

### 案例 70
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:240-260
- **严重程度**: critical
- **描述**: 在 get_config_with_cache 函数中，key 变量通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意的 key 参数，执行任意 SQL 命令。
- **建议**: 使用参数化查询：cursor.execute("SELECT value FROM config WHERE key = ?", (key,))

### 案例 71
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:72-84
- **严重程度**: critical
- **描述**: get_user_orders_n_plus_1 函数在 for 循环内逐条执行 SQL 查询。如果 user_ids 有 1000 个元素，将产生 1000 次数据库往返（1 次初始查询 + N 次循环查询）。数据库连接和查询的开销远大于批量查询，随着用户数增长，性能呈线性恶化。
- **建议**: 使用 SQL IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join(['?']*len(user_ids))})", user_ids)。这将数据库往返次数从 N+1 降为 2 次（查询 + 获取结果）。

### 案例 72
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:42-42
- **严重程度**: critical
- **描述**: login_user 函数中，username 变量通过 f-string 直接拼接到 SQL 查询字符串中。攻击者可以构造恶意 username 参数（如 ' OR 1=1 --）绕过认证或窃取数据。这是最严重的安全漏洞之一，违反了安全编码规范。
- **建议**: 使用参数化查询：cursor.execute("SELECT * FROM users WHERE username = ?", (username,))。对于 sqlite3，应使用 ? 占位符。

### 案例 73
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:255-255
- **严重程度**: critical
- **描述**: save_user_data_encrypted 函数中，user['id'] 通过 f-string 拼接到 INSERT 语句中，存在 SQL 注入风险。
- **建议**: 使用参数化查询：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))。

### 案例 74
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:296-296
- **严重程度**: critical
- **描述**: get_config_with_cache 函数中，key 变量通过 f-string 拼接到 SQL 查询中，存在 SQL 注入风险。
- **建议**: 使用参数化查询：cursor.execute("SELECT value FROM config WHERE key = ?", (key,))。

### 案例 75
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:60-76
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数对每个 user_id 单独执行 SQL 查询，导致 N+1 次数据库往返。当 user_ids 列表较大时（如 1000 个用户），会产生 1000 次查询，严重影响性能。同时，数据库连接未在 finally 块中关闭，可能导致连接泄漏。
- **建议**: 1. 使用 IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join('?' * len(user_ids))})", user_ids)。2. 使用 with 语句或 try/finally 确保连接关闭。3. 考虑使用 ORM 的预加载功能。

### 案例 76
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:233-260
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在应用层对每行数据单独创建 cipher 对象进行 AES 加密。对于 10000 行数据，会产生 10000 次 AES 初始化开销。同时，手动实现 PKCS7 填充容易出错，且 SQL 注入风险依然存在。
- **建议**: 1. 考虑使用数据库透明加密（TDE）功能，将加密责任下放到数据库层。2. 如果必须应用层加密，应批量加密：先收集所有数据，使用同一个 cipher 对象（CBC 模式需注意 IV 管理）或使用 GCM 模式。3. 使用参数化查询插入数据。

### 案例 77
- **日期**: 2026-05-19_101230
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:63-78
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数在循环内对每个用户单独执行 SQL 查询，导致 N+1 性能问题。同时，数据库连接未在 finally 块中关闭，异常发生时可能导致连接泄漏。函数职责不清晰，混合了数据访问和结果组装。
- **建议**: 1. 使用 IN 子句一次查询所有用户的订单：cursor.execute("SELECT * FROM orders WHERE user_id IN ({seq})".format(seq=','.join('?' * len(user_ids))), user_ids)。2. 使用上下文管理器 with conn: 确保连接自动关闭。3. 将数据访问层与业务逻辑分离。

### 案例 78
- **日期**: 2026-05-19_101230
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:238-260
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在循环内对每行数据创建新的 AES cipher 对象，导致 10000 行数据需要 10000 次 AES 初始化，性能极差。同时，手动实现 PKCS7 填充容易出错，且 SQL 注入风险依然存在。应用层手动加密不如使用数据库透明加密（TDE）方案。
- **建议**: 1. 复用 cipher 对象或使用流式加密模式。2. 考虑使用数据库级别的透明加密（TDE）替代应用层加密。3. 使用参数化查询防止 SQL 注入。4. 使用成熟的加密库（如 cryptography）避免手动实现填充逻辑。

### 案例 79
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:254-254
- **严重程度**: critical
- **描述**: save_user_data_encrypted 函数中 user['id'] 直接通过 f-string 拼接到 SQL 查询中，存在 SQL 注入风险。攻击者可以构造恶意的 user_id 值。
- **建议**: 使用参数化查询：cursor.execute("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", (user['id'], encoded))

### 案例 80
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:295-295
- **严重程度**: critical
- **描述**: get_config_with_cache 函数中 key 变量直接通过 f-string 拼接到 SQL 查询中，存在 SQL 注入风险。攻击者可以构造恶意的 key 参数。
- **建议**: 使用参数化查询：cursor.execute("SELECT value FROM config WHERE key = ?", (key,))

### 案例 81
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:62-75
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数在循环内对每个 user_id 单独执行 SQL 查询，导致 N+1 查询问题。当 user_ids 列表较大时（如 1000 个用户），会产生 1000 次数据库往返，严重影响性能。
- **建议**: 使用 IN 子句一次查询所有用户的订单：cursor.execute(f"SELECT * FROM orders WHERE user_id IN ({','.join('?' * len(user_ids))})", user_ids)。同时考虑使用 JOIN 或子查询优化。
