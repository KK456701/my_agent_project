# 模式: 过于激进的输入清洗可能导致功能异常

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
根据上下文进行更精确的清洗。例如，如果是为了防止 XSS，应使用专门的 HTML 转义库（如 html.escape）而不是直接删除字符。如果是为了防止 SQL 注入，应使用参数化查询，而不是依赖输入清洗。

## 审查次数: 46

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: medium
- **描述**: sanitize_user_input_batch 函数中的正则表达式 re.sub(r'[<>"\']', '', value) 会移除所有尖括号、双引号和单引号。这可能会破坏用户输入中的合法内容，例如包含数学表达式（如 1 < 2）或引号的文本。
- **建议**: 根据上下文进行更精确的清洗。例如，如果是为了防止 XSS，应使用专门的 HTML 转义库（如 html.escape）而不是直接删除字符。如果是为了防止 SQL 注入，应使用参数化查询，而不是依赖输入清洗。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:155-175
- **严重程度**: high
- **描述**: sanitize_user_input_batch 函数对每条记录的每个字符串字段执行 3 次正则替换。对于 10000 条记录、每条 10 个字段，将执行 300000 次正则操作。正则编译和匹配开销大，导致 O(N*M) 的时间复杂度（N=记录数，M=字段数）。
- **建议**: 1. 预编译正则表达式为常量，避免每次循环重新编译。2. 合并多个正则替换为一次替换。3. 考虑使用更高效的 HTML 转义库如 bleach。4. 对于批量操作，使用参数化查询而非字符串清洗来防止注入。

### 案例 3
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: medium
- **描述**: sanitize_user_input_batch 函数中的正则表达式 re.sub(r'[<>"\']', '', value) 会移除所有尖括号、双引号和单引号。这可能会破坏用户输入中的合法内容，例如包含数学表达式（如 1 < 2）或引号的文本。
- **建议**: 根据上下文进行更精确的清洗。例如，如果是为了防止 XSS，应使用专门的 HTML 转义库（如 html.escape）而不是直接删除字符。如果是为了防止 SQL 注入，应使用参数化查询，而不是依赖输入清洗。

### 案例 4
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:148-175
- **严重程度**: high
- **描述**: sanitize_user_input_batch 函数对每条记录的每个字符串字段执行 3 次正则替换。对于 10000 条记录、每条 10 个字段，就是 300000 次正则操作。每次 re.sub 都需要编译正则表达式（即使未指定 re.compile，内部也会缓存，但仍有开销），且正则回溯可能导致性能退化。
- **建议**: 1. 使用预编译正则：将正则表达式移到循环外，用 re.compile 预编译。2. 合并正则：将多个替换合并为一个，或使用更高效的字符串方法（如 str.replace）。3. 考虑使用专门的清洗库（如 bleach）或基于白名单的校验。

### 案例 5
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: high
- **描述**: sanitize_user_input_batch 函数对每条记录的每个字符串字段都执行 3 次正则替换。对于 10000 条记录、每条 10 个字段，就是 300000 次正则匹配。正则编译开销大，且每次匹配都重新编译模式，导致 CPU 密集型操作。
- **建议**: 1. 使用预编译正则对象（re.compile）在函数外部编译一次。2. 合并多个正则替换为一次遍历。3. 对于批量场景，考虑使用更高效的清洗策略（如白名单过滤）。修改为：SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE); DANGEROUS_CHARS = re.compile(r'[<>"\']'); SQL_KEYWORDS = re.compile(r'(SELECT|INSERT|DELETE|DROP|UNION)\s', re.IGNORECASE); 然后在循环内使用这些预编译对象。

### 案例 6
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: medium
- **描述**: sanitize_user_input_batch 函数中的正则表达式 re.sub(r'[<>"\']', '', value) 会移除所有尖括号、双引号和单引号。这过于激进，会破坏包含这些字符的正常数据（如用户姓名 O'Brien、公司名 AT&T、HTML 格式的富文本内容等）。
- **建议**: 根据上下文进行更精确的清洗。例如，如果是为了防止 XSS，应使用专门的 HTML 转义库（如 html.escape）而不是直接删除字符。如果是为了防止 SQL 注入，应使用参数化查询，而不是依赖输入清洗。

### 案例 7
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:196-210
- **严重程度**: medium
- **描述**: 在 auth_require_permission 装饰器中，使用 time.sleep(0.01) 来模拟频率限制。这会阻塞当前线程，如果应用是异步的，会阻塞整个事件循环。即使不是异步，也会降低吞吐量。
- **建议**: 使用异步的 asyncio.sleep()（如果框架支持），或者使用真正的频率限制中间件（如令牌桶算法），而不是 sleep。如果只是日志记录，移除 sleep。

### 案例 8
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:40-60
- **严重程度**: medium
- **描述**: login_user 和 get_user_orders_n_plus_1 函数中，数据库连接没有在 finally 块中关闭。如果函数中途抛出异常，连接将永远不会归还给连接池，导致连接泄漏。get_user_orders_n_plus_1 在循环结束后才关闭连接，但循环中的异常会导致连接泄漏。
- **建议**: 使用上下文管理器（with语句）管理数据库连接：with get_db() as conn:。或者使用 try/finally 确保连接始终被关闭。考虑使用连接池（如 SQLAlchemy 的连接池）替代每次创建新连接。

### 案例 9
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:72-82
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数中 conn.close() 在循环之后，如果循环中发生异常，连接将永远不会关闭，导致连接泄漏。
- **建议**: 使用 with 语句或 try-finally 确保连接被关闭。修改为：conn = get_db(); try: ... finally: conn.close()

### 案例 10
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: high
- **描述**: sanitize_user_input_batch 函数对每条记录的每个字符串字段都执行 3 次正则替换。对于 10000 条记录，如果每条记录有 10 个字段，将执行 300000 次正则操作，时间复杂度 O(N*M*K)，其中 N=记录数，M=字段数，K=正则数。
- **建议**: 1. 预编译正则表达式为模块级常量（如 RE_SCRIPT = re.compile(...)）。2. 如果业务允许，只对特定字段（如 name, bio）做清洗，而非所有字段。3. 考虑使用专门的 HTML 转义库（如 html.escape）替代多个正则。

### 案例 11
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:254-270
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数对每条记录执行单独的 INSERT 语句。对于 10000 条记录，会产生 10000 次数据库写入操作，每次都有事务开销。
- **建议**: 使用 executemany 批量插入，或构建单个 INSERT 语句插入多条记录。修改为：cursor.executemany("INSERT INTO users_encrypted (id, data) VALUES (?, ?)", [(user['id'], encoded) for user in users])

### 案例 12
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:148-155
- **严重程度**: medium
- **描述**: sanitize_user_input_batch 函数中的正则表达式 re.sub(r'[<>"\']', '', value) 会移除所有尖括号、双引号和单引号。这可能会破坏正常的用户输入，例如用户名中包含单引号（如 O'Brien）或包含 HTML 标签的富文本内容。
- **建议**: 根据上下文进行更精确的清洗。例如，如果是为了防止 XSS，应使用专门的 HTML 转义库（如 html.escape）而不是直接删除字符。如果是为了防止 SQL 注入，应使用参数化查询，而不是依赖输入清洗。

### 案例 13
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-210
- **严重程度**: medium
- **描述**: 在 auth_require_permission 装饰器中，使用 time.sleep(0.01) 模拟频率限制。这会阻塞当前线程，在高并发场景下（如 1000 QPS）会导致严重的性能瓶颈，因为每个请求都要等待 10ms。
- **建议**: 使用异步限流库（如 asyncio 环境下的 aioredis 限流）或基于计数器的内存限流（如令牌桶算法），避免阻塞。如果必须同步，考虑使用非阻塞的计数器检查。

### 案例 14
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:107-114
- **严重程度**: high
- **描述**: get_users_orders 函数在 for 循环内逐条执行数据库查询，导致 N+1 次数据库往返（N 为 usernames 列表长度）。如果 usernames 有 1000 个元素，将产生 1000 次独立的数据库查询，P99 延迟会急剧上升。同时，逐条 extend 结果列表也增加了 Python 层面的开销。
- **建议**: 使用批量查询（IN 子句）一次性获取所有用户的订单。结合参数化查询，修改为：placeholders = ','.join(['?'] * len(usernames)); cursor.execute(f"SELECT * FROM orders WHERE username IN ({placeholders})", usernames); orders = cursor.fetchall()。注意：IN 子句的参数化在不同数据库中语法略有差异，但 sqlite3 支持此方式。

### 案例 15
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:63-80
- **严重程度**: high
- **描述**: batch_export_users 函数对每个用户的 20 个字段全部调用 _encrypt_field，包括昵称（nickname）、头像 URL（avatar_url）等非敏感字段。对于 1000 条用户数据，这导致 20000 次加密操作。昵称和头像 URL 通常不是 PII（个人身份信息），加密它们不仅浪费 CPU，还会导致后续查询无法使用这些字段进行索引或模糊匹配。
- **建议**: 只对真正的 PII 字段进行加密：手机号、身份证号、银行卡号。昵称、头像 URL 等非敏感字段无需加密。address 字段视业务需求决定（如果包含详细地址则加密，如果只是城市级别则可不加密）。优化后加密次数从 20000 次降至 3000-4000 次，性能提升 5-6 倍。

### 案例 16
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:64-80
- **严重程度**: medium
- **描述**: batch_export_users 函数对用户的所有字段都进行了加密，包括 nickname（昵称）和 avatar_url（头像URL）等非敏感字段。这些字段不包含个人身份信息（PII），加密它们不仅浪费计算资源（每批 1000 条 × 20 字段 = 20000 次加密操作），还增加了后续解密和搜索的复杂度。address（地址）字段是否加密存在争议，取决于业务场景。
- **建议**: 仅对 PII 敏感字段进行加密：手机号、身份证号、银行卡号。昵称和头像URL 不需要加密。地址字段建议根据数据分类标准决定：如果地址包含具体门牌号则加密，仅城市级别则不加密。修改为：user["phone"] = _encrypt_field(user["phone"]); user["id_card"] = _encrypt_field(user["id_card"]); 移除 nickname 和 avatar_url 的加密。

### 案例 17
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:100-115
- **严重程度**: medium
- **描述**: 在 get_users_orders 函数中，orders.extend(cursor.fetchall()) 在每次循环中都会扩展列表。对于大量数据，多次 extend 会导致列表多次重新分配内存。虽然这不是最严重的性能问题，但在大数据量下会有影响。
- **建议**: 使用列表推导式或 itertools.chain 一次性收集所有结果：all_orders = list(itertools.chain.from_iterable(cursor.fetchall() for _ in usernames))。或者使用批量查询后直接返回结果。

### 案例 18
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:88-101
- **严重程度**: high
- **描述**: 在 save_user_data_encrypted 函数中，AES.new() 在循环外创建一次，但每次加密都使用相同的 IV（固定 IV）。更严重的是，AES 的 CBC 模式要求每个加密操作使用不同的 IV，否则会降低安全性。此外，循环内执行数据库插入操作，导致 N+1 次数据库往返。
- **建议**: 1. 为每条记录生成随机 IV，并将 IV 与密文一起存储。2. 使用批量插入替代逐条插入，将 N 次数据库往返降为 1 次。3. 考虑使用数据库级别的加密功能（如 TDE）替代应用层加密。

### 案例 19
- **日期**: 2026-05-18_131922
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:87-93
- **严重程度**: medium
- **描述**: 在循环中重复使用同一个 cipher 对象进行加密。AES-CBC 模式要求每个加密操作使用不同的 IV 或重新初始化 cipher 对象，否则加密结果不安全。
- **建议**: 在每次循环中重新创建 cipher 对象：cipher = AES.new(ENCRYPTION_KEY.encode(), AES.MODE_CBC, os.urandom(16))，并将 IV 与密文一起存储。

### 案例 20
- **日期**: 2026-05-18_134209
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:108-115
- **严重程度**: high
- **描述**: get_users_orders 函数在 for 循环内对每个 username 执行单独的数据库查询。当 usernames 列表有 N 个元素时，会产生 N+1 次数据库查询（1 次连接 + N 次查询），导致严重的性能问题。
- **建议**: 使用批量查询（IN 子句）一次性获取所有用户的订单。同时结合参数化查询防止 SQL 注入。修改为：placeholders = ','.join(['?'] * len(usernames)); query = f'SELECT * FROM orders WHERE username IN ({placeholders})'; cursor.execute(query, usernames); orders = cursor.fetchall()

### 案例 21
- **日期**: 2026-05-18_134209
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:70-84
- **严重程度**: high
- **描述**: 在 batch_export_users 函数中，每批 1000 条用户数据，每条数据对 20 个字段全部调用 _encrypt_field。其中 nickname（昵称）和 avatar_url（头像URL）属于非敏感字段，加密毫无意义。1000 × 20 = 20000 次加密操作导致 P99 延迟 300ms+。如果只加密 phone、id_card 等真正敏感的 PII 字段，加密次数可减
- **建议**: 仅对 PII 敏感字段（phone, id_card, bank_card）进行加密，nickname、avatar_url 等非敏感字段直接透传。address 字段根据业务需求决定是否加密。优化后加密次数从 20000 次降至约 4000-6000 次，延迟可降低 60-70%。

### 案例 22
- **日期**: 2026-05-18_134209
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:68-84
- **严重程度**: medium
- **描述**: batch_export_users 函数对 nickname 和 avatar_url 等非敏感字段也进行了加密。这些字段通常不包含 PII（个人身份信息），加密它们不仅浪费计算资源（1000条 × 20字段 = 20000次加密），还可能导致后续功能（如搜索、排序）无法正常使用。
- **建议**: 只加密真正敏感的 PII 字段（手机号、身份证、银行卡、地址）。昵称和头像URL 不需要加密。修改为：移除 user['nickname'] 和 user['avatar_url'] 的 _encrypt_field 调用。

### 案例 23
- **日期**: 2026-05-18_134209
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:108-118
- **严重程度**: medium
- **描述**: 在循环中每次调用 orders.extend(cursor.fetchall())，每次 extend 都会触发列表的重新分配和复制。当 usernames 数量较大时（如 10000），这种逐条 extend 的方式会导致 O(n²) 级别的内存复制开销。
- **建议**: 批量查询后直接一次赋值：orders = cursor.fetchall()。如果必须分批查询，使用 list.extend 合并结果，但应尽量减少 extend 调用次数。

### 案例 24
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:218-249
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在应用层逐行进行 AES 加密，存在三个架构问题：1) 每次循环都创建新的 cipher 对象，10000 行数据需要 10000 次 AES 初始化，性能极差；2) 手动实现 PKCS7 填充容易出错；3) 应用层加密不如使用数据库透明加密（TDE）或列级加密。
- **建议**: 1) 考虑使用数据库内置加密功能（如 SQLite 的加密扩展）；2) 如果必须应用层加密，应复用 cipher 对象并批量处理；3) 使用成熟的加密库（如 cryptography）替代手动实现。

### 案例 25
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:88-101
- **严重程度**: medium
- **描述**: calculate_order_amount 函数先构建 prices 列表（O(n) 内存），再遍历求和。对于大量 items，这浪费了 O(n) 的额外内存。可以直接在循环中累加，将空间复杂度从 O(n) 降为 O(1)。
- **建议**: 直接在循环中累加 total：total += item['price'] * item['quantity'] * 0.15，移除 prices 列表。

### 案例 26
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:211-213
- **严重程度**: medium
- **描述**: 装饰器中使用 time.sleep(0.01) 模拟频率限制。time.sleep 是同步阻塞调用，会阻塞整个线程/事件循环。在异步框架（如 FastAPI）中，这将阻塞所有其他请求的处理。
- **建议**: 使用异步频率限制库（如 slowapi）或基于计数器的非阻塞频率限制。如果必须同步，考虑使用 asyncio.sleep 或基于令牌桶的算法。

### 案例 27
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:62-76
- **严重程度**: medium
- **描述**: get_user_orders_n_plus_1 函数中 conn.close() 在函数末尾执行，但如果循环中发生异常，连接将不会关闭，导致连接泄漏。长期运行可能耗尽数据库连接池。
- **建议**: 使用 with 语句或 try-finally 确保连接始终关闭：with get_db() as conn: 或 try: ... finally: conn.close()。

### 案例 28
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:82-99
- **严重程度**: medium
- **描述**: 0.15 作为税率是魔法数字，应定义为模块级常量。同时，创建中间列表 prices 再累加是冗余操作，可直接在循环中累加。这违反了可维护性和代码简洁性原则。
- **建议**: 定义常量 TAX_RATE = 0.15，并直接累加：total = sum(item['price'] * item['quantity'] * TAX_RATE for item in items)

### 案例 29
- **日期**: 2026-05-19_092955
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:131-149
- **严重程度**: medium
- **描述**: sanitize_user_input_batch 函数使用多个正则表达式逐字段清洗，存在三个问题：1) 正则表达式过于激进，可能误杀正常字符（如用户名中的引号）；2) 每次调用都重新编译正则，性能差；3) 清洗逻辑与业务逻辑耦合，难以扩展。
- **建议**: 1) 预编译正则表达式为模块级常量；2) 使用专门的 HTML 转义库（如 html.escape）替代手动正则；3) 将清洗逻辑抽象为独立的 Sanitizer 类，支持策略模式扩展。

### 案例 30
- **日期**: 2026-05-19_093920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:210
- **严重程度**: medium
- **描述**: auth_require_permission 装饰器中使用 time.sleep(0.01) 模拟频率限制。如果应用是异步框架（如 FastAPI/Quart），这会阻塞整个事件循环，导致所有并发请求排队等待。即使不是异步应用，sleep 也会阻塞当前线程，降低吞吐量。
- **建议**: 1. 如果使用异步框架，替换为 await asyncio.sleep(0.01)。2. 更推荐使用令牌桶算法（如 aioredis 实现）进行频率限制，而不是 sleep。3. 如果只是日志审计，移除 sleep 直接记录即可。

### 案例 31
- **日期**: 2026-05-19_094200
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:245-260
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在循环内逐条执行 INSERT 语句。对于 10000 条数据，将产生 10000 次数据库往返。每次 INSERT 都有事务日志、索引更新等开销。
- **建议**: 使用 executemany 或构建批量 INSERT 语句（如 INSERT INTO users_encrypted (id, data) VALUES (?, ?), (?, ?), ...），将 10000 次数据库往返降为 1 次。

### 案例 32
- **日期**: 2026-05-19_094200
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:65-79
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数在循环结束后调用 conn.close()，但如果循环中发生异常，连接将永远不会关闭。此外，get_db() 函数每次调用都创建新连接，没有连接池复用，在高并发场景下会耗尽数据库连接。
- **建议**: 1) 使用 with sqlite3.connect(DATABASE_PATH) as conn: 确保自动关闭；2) 引入连接池（如 SQLAlchemy 的 pool）或使用 contextlib.contextmanager 管理连接生命周期；3) 将数据库连接作为参数注入，而非在函数内部创建。

### 案例 33
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:131-148
- **严重程度**: high
- **描述**: sanitize_user_input_batch 函数对每条记录的每个字符串字段执行 3 次正则替换。对于 10000 条记录、每条 10 个字段，共执行 300000 次正则匹配。Python 的 re.sub 每次都会编译正则（除非使用 re.compile 预编译），导致 CPU 密集型操作。
- **建议**: 1. 使用 re.compile 预编译正则表达式（在函数外部定义）。2. 合并多个正则替换为一次遍历。3. 考虑使用专门的 HTML 转义库（如 html.escape）替代正则。4. 对于批量场景，可考虑使用 C 扩展（如 regex 库）或异步处理。

### 案例 34
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:244-245
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在每次循环迭代中都创建新的 AES cipher 对象。对于大量用户数据，这会带来巨大的性能开销。
- **建议**: 将 cipher 对象的创建移到循环外部。如果使用 CBC 模式，需要为每个记录生成唯一的 IV，但可以复用 cipher 对象或使用更高效的加密模式（如 GCM）。

### 案例 35
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:89-103
- **严重程度**: medium
- **描述**: calculate_order_amount 函数先构建 prices 列表，再遍历求和。这浪费了 O(n) 的内存和一次额外的循环。对于 10000 个商品，多分配约 80KB 内存（假设每个 float 8 字节）。
- **建议**: 直接在循环中累加 total，省去中间列表：total = 0; for item in items: total += item['price'] * item['quantity'] * 0.15

### 案例 36
- **日期**: 2026-05-19_095239
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:168-199
- **严重程度**: medium
- **描述**: time.sleep(0.01) 在装饰器 wrapper 函数中同步阻塞 10ms。如果此装饰器用于异步视图函数（如 FastAPI/Starlette），会阻塞整个事件循环，导致所有并发请求排队等待。对于 100 个并发请求，总延迟增加 1 秒。
- **建议**: 如果需要在异步上下文中使用，应使用 asyncio.sleep(0.01)。如果是在同步上下文中，考虑使用令牌桶算法或漏桶算法实现更精确的频率限制，而不是简单的 sleep。

### 案例 37
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:63-78
- **严重程度**: high
- **描述**: get_user_orders_n_plus_1 函数在循环内逐条查询每个用户的订单，导致 N+1 次数据库查询。同时，数据库连接在 finally 块外关闭，如果查询过程中抛出异常，连接将不会被释放，造成资源泄漏。
- **建议**: 1) 使用 IN 子句一次查询所有用户的订单：cursor.execute("SELECT * FROM orders WHERE user_id IN ({})".format(','.join('?' * len(user_ids))), user_ids)；2) 使用 with 语句或 try/finally 确保连接被关闭。

### 案例 38
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:196-224
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在应用层对每行数据单独进行 AES 加密，每次循环都创建新的 cipher 对象。对于 10000 行数据，需要 10000 次 AES 初始化，性能极差。同时，手动实现 PKCS7 填充容易出错。
- **建议**: 1) 使用数据库的透明加密（TDE）功能，对应用层透明；2) 如果必须应用层加密，使用流式加密（如 AES-GCM）或批量加密模式，复用 cipher 对象；3) 使用成熟的加密库（如 cryptography）避免手动实现填充。

### 案例 39
- **日期**: 2026-05-19_095920
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:240-248
- **严重程度**: medium
- **描述**: 在 save_user_data_encrypted 函数中，每次循环都创建新的 AES.new() 对象。对于大量用户数据，这会导致不必要的性能开销。
- **建议**: 将 cipher 对象的创建移到循环外部。但更根本的解决方案是使用数据库透明加密（TDE）或使用更高效的加密方案（如使用相同的 cipher 对象进行多次加密）。

### 案例 40
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:207
- **严重程度**: medium
- **描述**: time.sleep(0.01) 在装饰器中用于模拟频率限制，但这是同步阻塞调用。在异步框架（如 FastAPI/Quart）或高并发场景下，这会阻塞整个事件循环或线程池，降低吞吐量。
- **建议**: 1. 使用异步 sleep（asyncio.sleep）如果上下文是异步的。2. 使用专门的限流库（如 slowapi 或令牌桶算法）替代 sleep。3. 如果必须同步阻塞，考虑将限流逻辑移到中间件层，使用非阻塞的计数器或 Redis 实现。

### 案例 41
- **日期**: 2026-05-19_100321
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:72-84
- **严重程度**: medium
- **描述**: get_user_orders_n_plus_1 函数中 conn.close() 在函数末尾执行，但如果循环中发生异常，连接将不会被关闭，导致连接泄漏。长期运行可能耗尽数据库连接池。
- **建议**: 使用 with 语句管理连接：with sqlite3.connect(DATABASE_PATH) as conn: cursor = conn.cursor(); ...。with 块退出时自动关闭连接，即使发生异常。

### 案例 42
- **日期**: 2026-05-19_101524
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:204
- **严重程度**: medium
- **描述**: auth_require_permission 装饰器中使用 time.sleep(0.01) 模拟频率限制。如果该装饰器用于异步 Web 框架（如 FastAPI），time.sleep() 会阻塞整个事件循环，导致所有并发请求等待。即使用于同步框架，sleep 也会阻塞当前线程，降低吞吐量。
- **建议**: 1. 如果用于异步框架，使用 asyncio.sleep(0.01)。2. 如果用于同步框架，考虑使用令牌桶算法（如 pyrate-limiter）或 Redis 限流，避免使用 sleep。3. 如果只是模拟，移除 sleep 或使用更轻量的计数器。

### 案例 43
- **日期**: 2026-05-19_103513
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:73-74
- **严重程度**: medium
- **描述**: get_user_orders_n_plus_1 函数在循环结束后调用 conn.close()，但如果循环中发生异常，连接将永远不会被关闭，导致数据库连接泄漏。这违反了资源管理的异常安全原则。
- **建议**: 使用 with 语句或 try/finally 块确保连接被正确关闭。例如：with get_db() as conn: 或 try: ... finally: conn.close()

### 案例 44
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:240-268
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在应用层对每行数据单独进行 AES 加密。这导致：1) 每次循环都创建新的 cipher 对象，性能开销大；2) 手动实现 PKCS7 填充，容易出错；3) 代码复杂度高，难以维护。
- **建议**: 使用数据库的透明加密（TDE）功能，或使用 ORM 的自动加密功能。如果必须在应用层加密，应使用更高级的加密库（如 cryptography 的 Fernet），它封装了密钥管理、IV 生成和填充逻辑。

### 案例 45
- **日期**: 2026-05-19_103843
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:108-120
- **严重程度**: medium
- **描述**: calculate_order_amount 函数先构建一个 prices 列表，再遍历该列表求和。这浪费了 O(n) 的额外内存，并且多了一次不必要的循环。对于大量 items，这种模式会显著增加内存占用和 CPU 时间。
- **建议**: 直接在循环中累加 total，省去中间列表。修改为：total = 0; for item in items: total += item['price'] * item['quantity'] * 0.15; return total。或者使用 sum() 生成器表达式：return sum(item['price'] * item['quantity'] * 0.15 for item in items)。

### 案例 46
- **日期**: 2026-05-19_104435
- **来源 PR**: stalemate_test.py
- **文件**: stalemate_test.py:66-76
- **严重程度**: high
- **描述**: handle_api_request 在请求处理路径中同步写入审计日志，每请求 500 字节，峰值 5000 QPS 时产生 2.5MB/s 的磁盘写入。同步 I/O 会阻塞事件循环或线程池，导致请求延迟增加，在高并发下可能引发背压和请求超时。
- **建议**: 1. 使用异步日志写入（如 aiologger）或生产者-消费者模式，将日志写入放入后台线程/进程。2. 使用高性能日志库（如 structlog + 异步处理器）或集中式日志服务（如 ELK、Loki）。3. 如果合规允许，对日志进行采样或压缩后再写入。
