# 模式: 硬编码密钥

## 代码特征
（自动从首次发现中提取，后续审查会逐步丰富）

## 标准修复
将密钥移至环境变量或安全的密钥管理服务中，例如：SECRET_KEY = os.environ.get('SECRET_KEY')。如果密钥必须存储在代码中，应使用配置文件并确保其不被提交到版本控制系统。

## 审查次数: 49

## 历史案例

### 案例 1
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:24
- **严重程度**: critical
- **描述**: SECRET_KEY 被硬编码在源代码中。攻击者可以通过访问源代码或反编译获取此密钥，进而伪造 JWT Token 或解密敏感数据。
- **建议**: 将密钥移至环境变量或安全的密钥管理服务中，例如：SECRET_KEY = os.environ.get('SECRET_KEY')。如果密钥必须存储在代码中，应使用配置文件并确保其不被提交到版本控制系统。

---
> 本文件由 Agent 自动维护，后续同类问题会自动追加案例。

### 案例 2
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:48
- **严重程度**: high
- **描述**: login_user 函数中，将用户输入的密码与数据库中存储的密码进行直接的字符串比较。这意味着密码是以明文或可逆形式存储的，一旦数据库泄露，所有用户的密码将直接暴露。
- **建议**: 使用安全的哈希算法（如 bcrypt、argon2）存储密码。在注册时对密码进行哈希，登录时对用户输入的密码进行相同的哈希运算并与数据库中的哈希值比较。例如，使用 bcrypt：if bcrypt.checkpw(password.encode('utf-8'), stored_password):

### 案例 3
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:119
- **严重程度**: high
- **描述**: hash_password 函数使用 MD5 算法进行密码哈希。MD5 已被证明存在碰撞漏洞，且计算速度过快，容易受到暴力破解和彩虹表攻击，不适合用于密码存储。
- **建议**: 使用 bcrypt、scrypt 或 argon2 等专门用于密码哈希的算法。例如，使用 bcrypt：hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

### 案例 4
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:249
- **严重程度**: critical
- **描述**: ENCRYPTION_KEY 和 ENCRYPTION_IV 被硬编码在源代码中。攻击者可以获取这些值，从而解密所有使用此密钥加密的敏感数据。
- **建议**: 将加密密钥存储在安全的密钥管理服务（如 AWS KMS、HashiCorp Vault）或环境变量中。初始化向量（IV）对于每条加密记录应该是唯一的、随机的，并与密文一起存储。

### 案例 5
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:249-268
- **严重程度**: critical
- **描述**: save_user_data_encrypted 函数在循环内为每条用户数据创建新的 AES cipher 对象。AES 密钥扩展（Key Expansion）是计算密集型操作，每次初始化都需要 10 轮（AES-128）或 14 轮（AES-256）的密钥调度。对于 10000 条记录，将执行 10000 次密钥扩展，严重拖慢写入性能。
- **建议**: 1. 将 cipher 对象创建移到循环外，复用同一个 cipher 对象（注意 CBC 模式需要不同的 IV）。2. 考虑使用数据库透明加密（TDE）或列级加密，避免应用层逐行加密。3. 如果必须应用层加密，使用更高效的加密模式如 GCM，并批量处理数据。

### 案例 6
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: high
- **描述**: 整个文件将所有功能（数据库操作、认证逻辑、业务计算、安全校验、缓存管理）混杂在单一模块和函数中，没有遵循分层架构（如 Controller/Service/Repository 模式）。这导致代码难以维护、测试和扩展。例如，login_user 函数同时处理了数据库查询、密码比较和返回用户信息，违反了单一职责原则。
- **建议**: 重构为分层架构：

### 案例 7
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: high
- **描述**: 代码中使用了多个模块级全局变量（_TOKEN_CACHE, _CONFIG_CACHE, ENCRYPTION_KEY, ENCRYPTION_IV, SECRET_KEY）作为缓存或配置存储。这些全局可变状态在多线程/多进程环境下存在竞态条件，且没有过期、淘汰或访问控制机制。此外，硬编码的密钥和 IV 使得安全配置无法在部署时动态调整，违反了开闭原则。
- **建议**: 1. 使用依赖注入或配置管理库（如 pydantic-settings）管理配置和密钥。

### 案例 8
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: medium
- **描述**: 多个函数（get_db, login_user, get_user_orders_n_plus_1, save_user_data_encrypted, get_config_with_cache）直接创建和关闭数据库连接，但存在以下问题： 1. 连接没有在 finally 块中关闭，异常时可能导致连接泄漏。 2. 没有使用连接池，每次调用都创建新连接，性能差。 3. 连接参数（DATABASE_PATH）硬编码，无法适应不同环境。
- **建议**: 1. 使用数据库连接池（如 sqlite3 的 connection pool 或 SQLAlchemy 的 engine）。

### 案例 9
- **日期**: 2026-05-04_112647
- **来源 PR**: 第一次审查: 用户登录模块
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: medium
- **描述**: 代码中存在多个魔法数字（如 0.15 的税率、0.01 的 sleep 时间、16 的填充长度）和硬编码路径（/tmp/app.db），这些值没有定义为有意义的常量或配置项。这导致： 1. 业务规则变更时需要搜索替换所有出现位置。 2. 不同环境（开发/测试/生产）无法使用不同配置。 3. 代码可读性差，0.15 的含义不明确。
- **建议**: 1. 将所有魔法数字定义为有意义的常量（如 TAX_RATE = 0.15）。

### 案例 10
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:24
- **严重程度**: critical
- **描述**: SECRET_KEY 被硬编码在源代码中。攻击者可以通过访问源代码或反编译获取此密钥，进而伪造 JWT Token 或解密敏感数据。
- **建议**: 将密钥移至环境变量或安全的密钥管理服务中，例如：SECRET_KEY = os.environ.get('SECRET_KEY')。如果密钥必须存储在代码中，应使用配置文件并确保其不被提交到版本控制系统。

### 案例 11
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:48
- **严重程度**: high
- **描述**: login_user 函数中，将用户输入的密码与数据库中存储的密码进行直接的字符串比较。这意味着密码是以明文或可逆形式存储的，一旦数据库泄露，所有用户的密码将直接暴露。
- **建议**: 使用安全的哈希算法（如 bcrypt、argon2）存储密码。在注册时对密码进行哈希，登录时对用户输入的密码进行相同的哈希运算后与存储的哈希值比较。

### 案例 12
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:108-112
- **严重程度**: high
- **描述**: hash_password 函数使用 MD5 算法进行密码哈希。MD5 已被证明存在碰撞攻击，不再安全，容易受到彩虹表攻击。
- **建议**: 使用 bcrypt 或 argon2 等专门用于密码哈希的算法。例如：import bcrypt; hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

### 案例 13
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:155-175
- **严重程度**: critical
- **描述**: ENCRYPTION_KEY 和 ENCRYPTION_IV 被硬编码在源代码中。攻击者可以获取这些密钥，解密所有加密的用户数据。
- **建议**: 将密钥和 IV 移至环境变量或安全的密钥管理服务中。例如：ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY').encode()

### 案例 14
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:245-260
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在循环内每次迭代都创建新的 AES cipher 对象。AES 初始化涉及密钥扩展等计算密集型操作，对于 10000 行数据，就是 10000 次重复初始化，而实际上只需要一次。
- **建议**: 将 cipher 对象的创建移到循环外部，复用同一个 cipher 对象。注意：CBC 模式需要为每条记录使用不同的 IV，但可以复用密钥扩展后的 cipher 对象，只需更新 IV。

### 案例 15
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:175-195
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在应用层对每行数据单独进行 AES 加密。这导致：1) 每行都创建新的 cipher 对象，性能开销大；2) 手动实现 PKCS7 填充，容易出错；3) 加密密钥和 IV 硬编码在代码中。更好的架构是使用数据库的透明数据加密（TDE）或列级加密。
- **建议**: 1) 如果数据库支持，使用数据库的透明数据加密（TDE）功能，对应用层完全透明。2) 如果必须在应用层加密，应使用更高效的方案：复用 cipher 对象（CBC 模式需要不同的 IV），或使用更快的加密模式（如 GCM）。3) 将加密密钥移至密钥管理服务（KMS）或环境变量。4) 使用成熟的加密库（如 cryptography）而不是手动实现填充。

### 案例 16
- **日期**: 2026-05-04_112825
- **来源 PR**: 第二次审查: 相同代码
- **文件**: demo/sample_pr.py:175-195
- **严重程度**: critical
- **描述**: ENCRYPTION_KEY 和 ENCRYPTION_IV 被硬编码在源代码中。任何能够访问源代码的人都可以解密所有加密数据。此外，在 CBC 模式下使用固定的 IV 会降低加密强度，相同的明文块会产生相同的密文块。
- **建议**: 将加密密钥存储在环境变量或密钥管理服务（如 AWS KMS、HashiCorp Vault）中。对于 CBC 模式，应为每条记录生成随机的 IV，并将其与密文一起存储（通常作为密文的前缀）。

### 案例 17
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:22
- **严重程度**: high
- **描述**: Skills 规则命中: SECRET_KEY\s*=\s*["\x27]
- **建议**: 改为 os.environ.get('SECRET_KEY') 从环境变量读取

### 案例 18
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:22
- **严重程度**: high
- **描述**: Skills 规则命中: SECRET_KEY\s*=\s*["\x27]
- **建议**: 改为 os.environ.get('SECRET_KEY') 从环境变量读取

### 案例 19
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:228-230
- **严重程度**: high
- **描述**: ENCRYPTION_KEY 和 ENCRYPTION_IV 被硬编码在源代码中。攻击者通过访问源代码即可解密所有加密数据。此外，AES-CBC 模式下 IV 应该是随机生成的，固定 IV 会降低加密强度。
- **建议**: 1. 将密钥移至环境变量：ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY').encode()。2. 每次加密时随机生成 IV 并随密文一起存储。3. 考虑使用 pyca/cryptography 库替代已弃用的 pycryptodome。

### 案例 20
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:238-260
- **严重程度**: high
- **描述**: save_user_data_encrypted 函数在每次循环中都创建新的 AES.new() 对象。AES 初始化涉及密钥扩展等计算密集型操作，对于 10000 条记录，会执行 10000 次初始化，造成严重的 CPU 开销。
- **建议**: 将 cipher 对象的创建移到循环外部，复用同一个 cipher 对象。注意：CBC 模式需要为每条记录使用不同的 IV，但可以复用密钥扩展后的 cipher 对象。修改为：cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC); for user in users: cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, os.urandom(16)); ...

### 案例 21
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: high
- **描述**: 整个文件将数据库操作、认证逻辑、订单计算、密码哈希、输入清洗、JWT验证、权限控制、加密存储、配置缓存等完全无关的功能全部塞在一个模块中。这导致模块内聚性极差，任何功能的修改都可能影响其他部分，且无法独立测试或复用。
- **建议**: 按业务领域拆分为独立模块：auth.py（登录、JWT、权限）、db.py（数据库连接、CRUD）、order.py（订单计算）、security.py（密码哈希、加密、输入清洗）、config.py（配置管理）。每个模块只负责一个明确的职责。

### 案例 22
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:44-45
- **严重程度**: medium
- **描述**: login_user 函数中，用户输入的密码与数据库中存储的密码直接进行字符串比较。这表明密码很可能以明文形式存储在数据库中，一旦数据库泄露，所有用户密码将直接暴露。
- **建议**: 1. 使用 bcrypt 或 argon2 等安全的密码哈希算法存储密码。2. 比较时使用哈希后的值进行比较：if bcrypt.checkpw(password.encode(), stored_hash)。

### 案例 23
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:120-125
- **严重程度**: medium
- **描述**: hash_password 函数虽然使用了盐值，但盐值是通过字符串拼接的方式与密码组合后哈希。这种方式容易被长度扩展攻击利用。更安全的方式是使用专门的密码哈希函数（如 bcrypt）自动处理盐值。
- **建议**: 使用 bcrypt 库：hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())，它会自动生成并存储盐值。

### 案例 24
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:295
- **严重程度**: medium
- **描述**: get_config_with_cache 函数将数据库查询结果缓存到全局字典 _CONFIG_CACHE 中。如果配置项包含敏感信息（如第三方 API Key、数据库密码等），这些信息将长期驻留在内存中，且无访问控制。
- **建议**: 1. 对敏感配置项进行加密存储和读取。2. 为缓存添加 TTL 和淘汰策略。3. 考虑使用专门的配置管理服务（如 Vault）来管理敏感配置。

### 案例 25
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:234-260
- **严重程度**: medium
- **描述**: save_user_data_encrypted 在应用层手动实现AES加密，存在以下架构问题：1) 加密逻辑与业务逻辑耦合，违反单一职责；2) 手动处理PKCS7填充和序列化，容易出错；3) 每行数据都创建新的cipher对象，性能差；4) 加密密钥硬编码在代码中。
- **建议**: 1) 优先使用数据库透明加密(TDE)或存储引擎级加密，应用层无需关心加密细节。2) 如果必须应用层加密，使用专门的加密库（如 cryptography.fernet）封装加密逻辑，通过依赖注入提供密钥。3) 批量加密时复用cipher对象，或使用更快的加密模式（如GCM）。

### 案例 26
- **日期**: 2026-05-18
- **来源 PR**: test
- **文件**: demo/sample_pr.py:88-101
- **严重程度**: low
- **描述**: 0.15 这个税率/折扣率直接硬编码在循环中，可读性差且难以维护。如果税率变更，需要修改所有出现的地方。
- **建议**: 将 0.15 定义为模块级常量，如 TAX_RATE = 0.15，然后在计算时引用该常量。

### 案例 27
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:254-270
- **严重程度**: critical
- **描述**: save_user_data_encrypted 函数在每次循环中都创建新的 AES.new() 对象。AES 初始化涉及密钥扩展等计算密集型操作，对于 10000 条记录，会执行 10000 次 AES 初始化，而实际上只需要 1 次。
- **建议**: 将 cipher 对象的创建移到循环外部，复用同一个 cipher 对象。注意：CBC 模式需要为每条记录生成随机 IV，但 cipher 对象本身可以复用。修改为：cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC); for user in users: cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, os.urandom(16))

### 案例 28
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:22
- **严重程度**: high
- **描述**: Skills 规则命中: SECRET_KEY\s*=\s*["\x27]
- **建议**: 改为 os.environ.get('SECRET_KEY') 从环境变量读取

### 案例 29
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:48-50
- **严重程度**: high
- **描述**: login_user 函数中，用户输入的密码直接与数据库中存储的密码进行字符串比较。这意味着数据库中的密码是以明文形式存储的，一旦数据库泄露，所有用户的密码将直接暴露。
- **建议**: 使用安全的哈希算法（如 bcrypt、argon2）存储和验证密码。修改为：if bcrypt.checkpw(password.encode(), stored_password.encode()):

### 案例 30
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:120-121
- **严重程度**: high
- **描述**: hash_password 函数使用 hashlib.md5() 进行密码哈希。MD5 已被证明存在碰撞攻击，不适合用于密码存储。攻击者可以快速破解 MD5 哈希值。
- **建议**: 使用 bcrypt 或 argon2 等专门用于密码哈希的算法。修改为：hashed = bcrypt.hashpw((password + salt).encode(), bcrypt.gensalt())

### 案例 31
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:228-229
- **严重程度**: high
- **描述**: ENCRYPTION_KEY 和 ENCRYPTION_IV 被硬编码在源代码中。攻击者可以通过访问源代码获取密钥，从而解密所有加密数据。
- **建议**: 将密钥移至环境变量或安全的密钥管理服务中。修改为：ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY').encode()

### 案例 32
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:22
- **严重程度**: high
- **描述**: SECRET_KEY 被硬编码在源代码中。攻击者可以通过访问源代码或反编译获取此密钥，进而伪造 JWT Token 或解密敏感数据。
- **建议**: 将密钥移至环境变量或安全的密钥管理服务中。修改为：SECRET_KEY = os.environ.get('SECRET_KEY')

### 案例 33
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:1-301
- **严重程度**: high
- **描述**: 整个模块将数据库连接、用户认证、订单处理、密码哈希、输入清洗、JWT认证、加密存储、配置缓存等完全不相关的功能全部塞在一个文件中。这导致模块内聚性极差，任何功能的修改都可能影响其他部分，且无法独立测试或复用。例如，login_user 函数同时处理了数据库操作、密码比较和返回用户信息，职责不单一。
- **建议**: 按业务领域拆分为多个模块：auth.py（认证相关）、db.py（数据库连接管理）、order.py（订单处理）、crypto.py（加密/哈希）、middleware.py（装饰器/中间件）、config.py（配置管理）。每个模块只负责一个明确的职责。

### 案例 34
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:128-155
- **严重程度**: high
- **描述**: 该装饰器同时承担了4种职责：JWT解析、权限校验、审计日志记录、频率限制。这违反了单一职责原则，导致：1) 任何职责的变化都需要修改装饰器；2) 无法单独测试某个职责（如权限校验）；3) 难以扩展（如添加新的认证方式）。此外，装饰器内部还包含了全局缓存和硬编码的日志输出，进一步增加了耦合。
- **建议**: 拆分为多个独立的装饰器或中间件：@jwt_required（解析和验证JWT）、@require_permission('admin')（权限校验）、@audit_log（日志记录）、@rate_limit（频率限制）。使用装饰器组合或中间件链来实现。

### 案例 35
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:233-240
- **严重程度**: medium
- **描述**: save_user_data_encrypted 在应用层手动实现 AES 加密，每行数据都创建新的 cipher 对象，并手动处理 PKCS7 填充。这种设计存在多个问题：1) 性能差，10000 行数据需要 10000 次 AES 初始化；2) 手动填充容易出错（如填充值计算错误）；3) 加密密钥硬编码在代码中；4) 应用层加密不如数据库透明加密（TDE）安全且简洁。架构上应该选择更合适的抽象
- **建议**: 1. 优先考虑数据库级别的透明加密（TDE），如 SQLite 的加密扩展或使用 SQLCipher。2. 如果必须应用层加密，使用更高级的加密库（如 cryptography 的 Fernet），它封装了密钥管理、加密模式和填充。3. 将加密逻辑封装为独立的服务类，并注入密钥管理。

### 案例 36
- **日期**: 2026-05-18_104408
- **来源 PR**: Demo: 用户登录模块
- **文件**: demo/sample_pr.py:97-108
- **严重程度**: low
- **描述**: 0.15 作为税率或折扣率直接硬编码在循环中，可读性差，且修改时需要搜索所有出现位置。
- **建议**: 在文件顶部定义常量 TAX_RATE = 0.15，并在循环中使用。

### 案例 37
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:48-52
- **严重程度**: critical
- **描述**: 使用 SHA256 和硬编码的固定 salt 进行密码验证，容易受到彩虹表攻击和暴力破解。同时，每次验证都重新计算哈希，在高并发场景下（5000 QPS）CPU 开销较大。
- **建议**: 1. 使用 bcrypt 或 argon2 进行密码哈希，它们内置了 salt 和可调的工作因子。2. 如果必须保持高性能，考虑使用缓存（如 Redis）缓存已验证的密码哈希结果，设置合理的 TTL。3. 将 salt 改为随机生成并存储在数据库中。

### 案例 38
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:44-47
- **严重程度**: high
- **描述**: SALT = "hardcoded-salt-123" 被硬编码在源代码中。所有用户使用相同的固定 salt，这破坏了 salt 的核心安全目的（防止彩虹表攻击和相同密码产生相同哈希）。攻击者获取源码后可以预计算彩虹表。
- **建议**: 为每个用户生成唯一的随机 salt，并存储在数据库中。修改为：salt = os.urandom(16).hex(); digest = hashlib.sha256((password + salt).encode()).hexdigest()，并将 salt 与哈希一起存储。

### 案例 39
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:46
- **严重程度**: high
- **描述**: 使用 SHA256 进行密码验证。SHA256 是快速哈希函数，攻击者可以每秒尝试数十亿次密码，不适合密码存储场景。即使使用 salt，也无法抵御暴力破解。
- **建议**: 改用 bcrypt、argon2 或 scrypt 等专用密码哈希算法。修改为：import bcrypt; bcrypt.checkpw(password.encode(), stored_hash.encode())

### 案例 40
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:76
- **严重程度**: high
- **描述**: ENCRYPTION_KEY = "hardcoded-aes-key!!" 被硬编码在源代码中。攻击者可以通过访问源代码或反编译获取此密钥，从而解密所有加密的用户数据。
- **建议**: 将密钥移至环境变量或安全的密钥管理服务中。修改为：ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')。如果密钥必须存储在代码中，应使用配置文件并确保其不被提交到版本控制系统。

### 案例 41
- **日期**: 2026-05-18_104728
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:86-100
- **严重程度**: low
- **描述**: ENCRYPTION_KEY 和 IV 被硬编码在源代码中，攻击者可以通过访问源代码获取密钥，解密所有加密数据。
- **建议**: 将密钥移至环境变量或密钥管理服务（如 AWS KMS、HashiCorp Vault），IV 应为随机生成并随密文一起存储。

### 案例 42
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:38-44
- **严重程度**: high
- **描述**: verify_password_high_traffic 函数使用 hashlib.sha256() 对密码进行哈希，且盐值 SALT 是硬编码的固定值。SHA256 是快速哈希函数，专为计算效率设计，对 GPU/ASIC 暴力破解抵抗力极弱。固定盐值意味着所有用户使用相同的盐，彩虹表攻击可以一次性破解所有密码。该函数注释明确说明这是高并发登录接口（每秒数千次），但安全风险远高于性能收益。
- **建议**: 使用 bcrypt 或 argon2 等专用密码哈希算法。对于高并发场景，可以适当降低 bcrypt 的 cost 值（如从 12 降到 8-10），或使用 argon2 并调整内存/时间参数。修改为：import bcrypt; computed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=8))。注意：存储时需保存完整的 hash 输出（包含盐值），验证时使用 bcrypt.checkpw()。

### 案例 43
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:62
- **严重程度**: high
- **描述**: ENCRYPTION_KEY 被硬编码为字符串 'hardcoded-key-1234'。攻击者通过源代码泄露即可获取此密钥，进而解密所有用户敏感数据。这是严重的安全隐患，违反了密钥管理的黄金法则。
- **建议**: 将密钥移至环境变量或安全的密钥管理服务（如 AWS KMS、HashiCorp Vault）。修改为：ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')。如果必须使用配置文件，确保 .gitignore 排除该文件。

### 案例 44
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:31-42
- **严重程度**: high
- **描述**: 在高并发登录场景下，当前使用 SHA256 + 固定盐值进行密码哈希。虽然单次计算 < 1ms 性能极佳，但 SHA256 是通用哈希函数，设计上不是抗暴力破解的。攻击者可以使用 GPU 以每秒数十亿次的速度进行离线破解。固定盐值（SALT = 'company-wide-salt-2024'）进一步降低了安全性。这是一个典型的安全与性能的 trade-off：SHA256 快但不安全，bcryp
- **建议**: 使用 bcrypt 或 argon2 进行密码哈希。对于高并发场景，可以：1) 降低 bcrypt 的 cost factor（如从 12 降到 8-10），使单次哈希在 10-50ms 左右；2) 引入本地缓存（如 LRU cache）缓存最近验证成功的用户哈希结果，减少重复计算；3) 使用异步方式处理密码验证，避免阻塞事件循环。示例：import bcrypt; bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10))

### 案例 45
- **日期**: 2026-05-18_113651
- **来源 PR**: sample_real_conflict.py
- **文件**: sample_real_conflict.py:63-80
- **严重程度**: medium
- **描述**: ENCRYPTION_KEY = 'hardcoded-key-1234' 被硬编码在源代码中。虽然这是性能问题，但硬编码密钥会导致：1) 密钥泄露风险（代码被提交到版本控制）；2) 密钥轮换困难（需要修改代码重新部署）；3) 所有环境使用相同密钥。
- **建议**: 将加密密钥移至环境变量或密钥管理服务（如 AWS KMS、HashiCorp Vault）。示例：ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')。如果必须使用固定密钥，应确保密钥文件不被提交到版本控制系统。

### 案例 46
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:42-43
- **严重程度**: high
- **描述**: 密码哈希使用的 salt 被硬编码为 'hardcoded-salt-123'。如果攻击者获取到源代码，可以预计算彩虹表，绕过密码验证。
- **建议**: 使用 bcrypt 或 argon2 等专用密码哈希库，它们会自动生成随机 salt 并存储在哈希结果中。例如：bcrypt.hashpw(password.encode(), bcrypt.gensalt())

### 案例 47
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:43
- **严重程度**: high
- **描述**: 使用 SHA256 对密码进行哈希，没有使用慢哈希函数（如 bcrypt、argon2、scrypt）。SHA256 是快速哈希，攻击者可以高速暴力破解密码。
- **建议**: 改用 bcrypt：bcrypt.hashpw(password.encode(), bcrypt.gensalt()) 进行存储，bcrypt.checkpw(password.encode(), stored_hash) 进行验证。

### 案例 48
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:55-60
- **严重程度**: high
- **描述**: 使用 SHA256 + 固定 salt 进行密码验证。SHA256 是快速哈希函数，攻击者可以每秒尝试数百万次密码。固定 salt 意味着所有用户使用相同的 salt，彩虹表攻击仍然有效。虽然性能好，但安全性严重不足。
- **建议**: 使用 bcrypt、scrypt 或 argon2 等专用密码哈希函数。如果性能是硬性要求，可以考虑使用 SHA256 进行多次迭代（如 10000 次以上），并使用每个用户独立的随机 salt。

### 案例 49
- **日期**: 2026-05-18_131226
- **来源 PR**: adversarial_test.py
- **文件**: adversarial_test.py:88-101
- **严重程度**: medium
- **描述**: ENCRYPTION_KEY = "hardcoded-aes-key!!" 被硬编码在源代码中。攻击者可以通过访问源代码或反编译获取此密钥，进而解密所有加密数据。
- **建议**: 将密钥移至环境变量或安全的密钥管理服务中，例如：ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')。
