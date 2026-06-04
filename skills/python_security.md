# Python 安全审查技能

## 常见漏洞清单

### SQL 注入
- **特征**: f-string / `%` / `+` 拼接 SQL 查询
- **检测**: `cursor.execute(f"...")`, `cursor.execute("...".format(...))`
- **修复**: 参数化查询 `cursor.execute("... WHERE x = ?", (val,))`
- **严重程度**: critical

### 硬编码密钥
- **特征**: 模块级 `SECRET_KEY = "..."` / `API_KEY = "..."` / `PASSWORD = "..."`
- **修复**: `os.environ.get("SECRET_KEY")` 或密钥管理服务
- **严重程度**: high

### 不安全的哈希
- **特征**: `hashlib.md5()`, `hashlib.sha1()`
- **修复**: `bcrypt` / `argon2` / `hashlib.pbkdf2_hmac()`
- **严重程度**: high

### 反序列化漏洞
- **特征**: `pickle.loads()`, `yaml.load()` (非 safe_load)
- **修复**: `yaml.safe_load()` / 避免 pickle
- **严重程度**: critical

### 路径遍历
- **特征**: `os.path.join(user_input, ...)` 未校验
- **修复**: `os.path.realpath()` + 白名单校验
- **严重程度**: high

### 不安全的随机数
- **特征**: `random.randint()` / `random.choice()` 用于安全场景
- **修复**: `secrets` 模块 / `os.urandom()`
- **严重程度**: medium
