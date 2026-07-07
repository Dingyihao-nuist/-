---
name: security-audit
description: "代码安全审计: 检查敏感信息泄漏、SQL注入、XSS、CSRF、不安全的加密、权限漏洞、配置风险等安全隐患。"
---

# /security-audit — 代码安全审计

对代码进行全面的安全漏洞扫描，输出风险分级报告和修复方案。

## 审计维度

### 维度 1：硬编码敏感信息

**检查对象：** 所有源文件（`.py` `.js` `.jsx` `.ts` `.tsx` `.java` `.go` `.yml` `.yaml` `.json` `.xml` `.properties` `.env` `.conf`）

**检查模式：**

| 类型 | 匹配模式 | 风险 |
|------|----------|------|
| 密码 | `password\s*=\s*["'][^"']+["']` `passwd` `pwd` | 🔴 严重 |
| API 密钥 | `api[_-]?key\s*=\s*["'][^"']{20,}["']` `secret\s*=\s*["'][^"']{20,}["']` | 🔴 严重 |
| Token | `token\s*=\s*["'][A-Za-z0-9_\-.]{15,}["']` `access_key` `auth_token` | 🔴 严重 |
| 私钥 | `-----BEGIN (RSA |EC )?PRIVATE KEY-----` | 🔴 严重 |
| 数据库连接串 | `jdbc:` `mongodb://` `mysql://` `postgresql://` 含用户名密码 | 🔴 严重 |
| 内网地址 | `10\.\d{1,3}\.\d{1,3}\.\d{1,3}` `172\.(1[6-9]\|2\d\|3[01])` `192\.168\.` | 🟡 中等 |
| 邮箱/手机号 | 开发者的个人邮箱或真实手机号 | 🟡 中等 |

**检查规则：**
- 命中后检查是否从环境变量读取（`os.environ` / `process.env`）→ 安全
- 命中后检查是否在 `.gitignore` 排除文件中 → 安全
- 命中后检查是否使用了 `__prefix__` 或占位符模式 → 酌情

### 维度 2：注入漏洞

#### 2.1 SQL 注入

**Python 后端：**
```python
# ❌ 危险模式
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute("SELECT * FROM users WHERE name = '" + name + "'")
session.execute(text(f"SELECT * FROM users WHERE id = {user_id}"))

# ✅ 安全模式
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
session.execute(select(User).where(User.id == user_id))
session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
```

#### 2.2 NoSQL 注入
- MongoDB `$where` `$eval` 操作符
- 未经过滤的用户输入直接传入 `find()` 的 `$where` 子句

#### 2.3 命令注入
- `os.system(user_input)` / `os.popen(user_input)`
- `subprocess.call(user_input, shell=True)`
- `eval(user_input)` / `exec(user_input)`
- Python `pickle.loads(user_input)` 反序列化

#### 2.4 路径遍历
- 用户输入拼接到文件路径：`open(f"/data/{user_filename}")`
- 未使用 `os.path.abspath` / `pathlib.Path.resolve()` 规范化路径

### 维度 3：配置文件敏感信息

| 检查项 | 说明 |
|--------|------|
| `.env` 提交到 Git | `.env` 不在 `.gitignore` 中 |
| `settings.json` 含密钥 | 直接写入了 API Key / Secret |
| `config.py` 含密钥 | 默认值用了真实密钥而非占位符 |
| `.yaml` / `.yml` 明文密码 | 数据库密码、Redis 密码未加密 |
| Dockerfile 泄露 | `ENV` 或 `ARG` 中有硬编码密钥 |
| CI/CD 配置 | `github/workflows/*.yml` 中的 Secrets 是否规范使用 |

### 维度 4：认证与权限

| 检查项 | 风险 |
|--------|------|
| JWT Secret 强度不足 | 🔴 `"secret"` `"changeme"` `"123456"` 等弱密钥 |
| Token 过期时间过长 | 🔴 超过 24h 的 access token |
| 密码未哈希 | 🔴 明文存储密码 |
| 弱哈希算法 | 🟡 MD5 / SHA1 用于密码 |
| 缺少权限校验 | 🔴 敏感接口无 `@require_admin` 或类似装饰器 |
| IDOR 风险 | 🟡 用户可访问其他用户的资源（按 ID 查询时未校验所有权） |
| 缺少 CSRF 保护 | 🟡 状态变更接口无 CSRF Token |

### 维度 5：其他安全隐患

| 检查项 | 风险 | 说明 |
|--------|------|------|
| XSS | 🔴 | 用户输入未转义直接渲染到 HTML |
| CORS 配置过宽 | 🟡 | `allow_origins=["*"]` 且 `allow_credentials=True` |
| Debug 模式开启 | 🔴 | `DEBUG=True` 在生产环境 |
| 错误信息暴露 | 🟡 | 异常堆栈直接返回给前端 |
| 文件上传无校验 | 🔴 | 未限制文件类型/大小/MIME |
| 不安全的反序列化 | 🔴 | `pickle.loads()` `yaml.load()` 用 `SafeLoader` |
| SSRF 风险 | 🔴 | 用户可控的 URL 被服务端请求 |
| 弱随机数 | 🟡 | `random.random()` 用于安全场景（应用 `secrets` 模块） |
| 依赖版本漏洞 | 🟡 | `requirements.txt` / `package.json` 中过时有 CVE 的包 |
| 日志泄露 | 🟡 | 日志中打印了 Token、密码、身份证号等敏感信息 |
| 速率限制缺失 | 🟡 | 登录/注册接口无 rate limit |
| HTTPS 未强制 | 🟡 | 生产环境允许 HTTP 明文传输 |

## 工作流程

### 输入
- 用户指定检查范围：文件、目录或 git diff
- 默认扫描整个项目源码目录

### 执行步骤

1. **收集目标文件** — 识别所有源码、配置、脚本文件
2. **逐维度扫描** — 读取文件内容，按各维度规则匹配
3. **误报排除** — 对命中项二次确认（环境变量读取、`.gitignore`、测试 mock 数据等）
4. **风险定级** — 按 🔴严重 / 🟡中等 / 🟢轻微 分级
5. **生成报告** — 输出问题清单 + 具体行号 + 修复代码示例

### 排除规则（避免误报）

- `tests/` 目录下的测试 mock 数据 → 标记但降级
- `.gitignore` 中已排除的文件 → 安全
- 从环境变量读取的值（如 `os.getenv("SECRET_KEY")`）→ 安全
- 示例代码/文档中的 `your-key-here` 等占位符 → 安全
- `node_modules/` `venv/` `__pycache__/` `.git/` → 跳过

## 输出格式

```
## 🔒 安全审计报告

**检查范围：** X 个文件，Y 行代码
**审计时间：** 2026-07-07
**风险等级分布：** 🔴 X 个 | 🟡 X 个 | 🟢 X 个

---

### 🔴 严重风险（必须立即修复）

| # | 文件:行号 | 类型 | 问题 | 修复建议 |
|---|-----------|------|------|----------|
| 1 | config.py:12 | 硬编码密钥 | `SECRET_KEY = "sk-abc123..."` | 改为 `os.getenv("SECRET_KEY")` |
| 2 | user.py:34 | SQL注入 | `execute(f"SELECT * WHERE id={uid}")` | 使用参数化查询 |

```python
# ❌ 当前代码 (config.py:12)
SECRET_KEY = "sk-abc123def456"

# ✅ 修复后
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY 环境变量未设置")
```

### 🟡 中等风险（建议尽快修复）

| # | 文件:行号 | 类型 | 问题 | 修复建议 |

### 🟢 轻微风险（可选修复）

| # | 文件:行号 | 类型 | 问题 | 修复建议 |

### 📊 统计摘要

| 维度 | 扫描数 | 问题数 | 通过率 |
|------|--------|--------|--------|
| 硬编码敏感信息 | 45 | 3 | 93% |
| 注入漏洞 | 28 | 1 | 96% |
| 配置文件泄漏 | 12 | 2 | 83% |
| 认证与权限 | 15 | 1 | 93% |
| 其他隐患 | 30 | 4 | 87% |

### 🛡️ 安全评分：72/100  (需改进)
```
