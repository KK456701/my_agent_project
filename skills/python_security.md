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

---

## ⚡ 确定性匹配规则（Skills Cache）

> 以下规则经人工确认，命中后直接返回修复结论，跳过 Agent 审查。
> Agent 收到的 prompt 中会标注"以下问题已由 Skills Cache 确定处理"。

```yaml
rules:
  - pattern: 'execute\(f"'
    severity: critical
    title: "SQL 注入 — 使用 f-string 拼接 SQL 查询"
    fix: "使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))"

  - pattern: "execute\\(f'"
    severity: critical
    title: "SQL 注入 — 使用 f-string 拼接 SQL 查询"
    fix: "使用参数化查询: cursor.execute('SELECT ... WHERE x = ?', (val,))"

  - pattern: 'SECRET_KEY\s*=\s*["\x27]'
    severity: high
    title: "硬编码密钥"
    fix: "改为 os.environ.get('SECRET_KEY') 从环境变量读取"

  - pattern: 'hashlib\.md5\('
    severity: high
    title: "不安全的 MD5 哈希"
    fix: "改为 bcrypt.hashpw(password.encode(), bcrypt.gensalt())"

  - pattern: 'hashlib\.sha1\('
    severity: high
    title: "不安全的 SHA1 哈希"
    fix: "改为 hashlib.sha256() 或 bcrypt（密码场景）"

  - pattern: 'pickle\.loads?\('
    severity: critical
    title: "不安全的反序列化 — pickle 可执行任意代码"
    fix: "改用 json.loads() 或 yaml.safe_load()"

  - pattern: 'yaml\.load\('
    severity: high
    title: "不安全的 YAML 加载"
    fix: "改为 yaml.safe_load()"
```
