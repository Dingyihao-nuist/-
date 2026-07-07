# LangChainRAG 压力测试

模拟 100 人同时使用的性能测试套件。

## 目录结构

```
backend/tests/load/
├── locustfile.py          # Locust 压测主脚本
├── config.py              # 压测配置中心
├── llm_mock.py            # 本地 LLM Mock 服务器
├── pre_create_users.py    # 预创建测试用户脚本
├── questions_pool.json    # 50 条中文电商问题池
├── data/
│   └── test_users.json    # 预创建用户凭据（脚本生成）
├── test_docs/             # 测试文档目录
├── reports/               # 压测报告输出
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install locust httpx
```

### 2. 启动后端服务

```bash
# 场景 A: 真实 DashScope（全链路压测，会产生 API 费用）
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

# 场景 B: Mock LLM（推荐日常使用，零费用）
# 先启动 Mock 服务器
python backend/tests/load/llm_mock.py
# 再启动后端，指向 Mock
DASHSCOPE_API_KEY=mock LLM_BASE_URL=http://localhost:8001/v1 \
  uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. 预创建测试用户

```bash
# 创建 100 用户 + 1 admin，并为每个用户创建会话
python backend/tests/load/pre_create_users.py \
  --count 100 \
  --admin-count 1 \
  --create-sessions \
  --upload-docs

# 预估耗时: ~22 分钟（100 注册 * 12s + 100 登录 * 6s）

# 断点续建（如果中断）
python backend/tests/load/pre_create_users.py --count 100 --resume

# 仅刷新 Token（用户已存在但 Token 过期）
python backend/tests/load/pre_create_users.py --only-tokens
```

### 4. 运行压测

```bash
cd backend/tests/load

# 方式 1: Web UI（推荐，可实时观察）
locust -f locustfile.py --web --host http://localhost:8000
# 打开 http://localhost:8089，输入 Users=100, Spawn rate=5

# 方式 2: Headless（CI/CD）
locust -f locustfile.py --headless \
  --users 100 --spawn-rate 5 --run-time 10m \
  --csv=reports/load --html=reports/load.html \
  --print-stats

# 方式 3: 阶梯式加压（找拐点）
locust -f locustfile.py --headless \
  --users 200 --spawn-rate 2 --step-users 10 --step-time 60s \
  --run-time 20m \
  --csv=reports/staircase
```

### 5. 查看报告

打开 `reports/load.html` 或分析 CSV：
```bash
# 快速查看关键指标
python -c "
import csv
with open('reports/load_stats.csv') as f:
    for row in csv.DictReader(f):
        if 'stream' in row['Name'] or 'Aggregated' in row['Name']:
            print(f\"{row['Name']}: avg={row['Average Response Time']}ms, p95={row['95%']}ms\")
"
```

## 虚拟用户行为

| 类型 | 占比 | 主要行为 |
|------|------|----------|
| RegularUser | 85% | 提问 SSE(40%) 浏览(15%) 查看消息(15%) 创建会话(10%) 反馈(10%) 导出(5%) 刷新Token(5%) |
| NewUserFlow | 10% | 注册 → 登录 → 创建会话 → 首次提问 → 追问 |
| AdminUser | 5% | 文档列表(40%) 统计(30%) 上传(10%) 分块(10%) 热门(10%) |

## 关键指标

| 指标 | 说明 | 目标 |
|------|------|------|
| SSE first_token | 首 Token 到达时间 (TTFT) | P95 < 3000ms |
| SSE full_response | 完整响应时间 | P95 < 10000ms |
| 错误率 | HTTP 4xx/5xx 占比 | < 1% |
| SQLite 锁错误 | "database is locked" 错误 | < 0.5% |

## Mock LLM 运行时调参

```bash
# 查看当前配置
curl http://localhost:8001/mock/config

# 调整延迟参数
curl -X POST http://localhost:8001/mock/config \
  -H "Content-Type: application/json" \
  -d '{"first_token_delay": 1.0, "inter_token_delay": 0.05, "error_rate": 0.02}'
```
