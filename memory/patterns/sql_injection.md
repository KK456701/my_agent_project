# 模式: SQL 注入漏洞

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
使用参数化查询（prepared statement）来防止 SQL 注入。对于 sqlite3，应使用 ? 占位符。修改为：cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

## 审查次数: 48

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
