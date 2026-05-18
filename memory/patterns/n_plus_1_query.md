# 模式: 过于激进的输入清洗可能导致功能异常

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
根据上下文进行更精确的清洗。例如，如果是为了防止 XSS，应使用专门的 HTML 转义库（如 html.escape）而不是直接删除字符。如果是为了防止 SQL 注入，应使用参数化查询，而不是依赖输入清洗。

## 审查次数: 18

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
