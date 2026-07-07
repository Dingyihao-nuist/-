# 🤖 电商知识库 RAG 问答系统

基于 **LangChain** + **阿里云百炼（通义千问）** + **FastAPI** + **React** 构建的企业级 RAG 知识库问答系统。

## 功能特性

### 核心功能
- 🔐 **用户认证**：注册、登录、JWT Token 鉴权、修改密码
- 👑 **角色权限**：Admin（admin/123456）独占知识库管理；普通用户仅可问答
- 📁 **知识库管理**（Admin）：上传文档（PDF/Word/Excel/TXT/Markdown）→ 自动分块 → BGE-M3 向量化 → ChromaDB 存储
- 💬 **RAG 智能问答**：混合检索（向量 + BM25）+ BGE-Reranker 精排 + 流式生成 + 来源引用
- 📝 **多会话管理**：每个用户独立会话，历史记录持久化
- 👍 **回答反馈**：点赞/点踩，评估 RAG 回答质量
- 📊 **统计仪表盘**（Admin）：用户数、问答量、好评率、热门问题
- 📥 **对话导出**：导出为 Markdown/PDF 文件

### 技术亮点
- **混合检索**：Dense（BGE-M3 向量 70%）+ Sparse（BM25 30%）→ RRF 融合
- **精排 Reranker**：BGE-Reranker Cross-Encoder 重排序
- **Query Rewriting**：MultiQueryRetriever 多查询改写
- **SSE 流式输出**：首 Token 延迟 < 1.5s
- **抗幻觉机制**：相关性阈值过滤 + 低温生成 + 严格 Prompt 约束
- **嵌入缓存**：LRU 缓存热点查询向量

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.11+) |
| RAG 框架 | LangChain 1.x |
| LLM | 阿里云百炼 DashScope（qwen-plus，OpenAI 兼容） |
| Embedding | BGE-M3（本地，1024维，免费） |
| 向量数据库 | ChromaDB（嵌入式） |
| 业务数据库 | SQLite |
| 前端 | React 18 + Vite + Ant Design 5 |
| 状态管理 | Zustand |
| 文档解析 | PyPDF2 / python-docx / openpyxl |

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- Windows（推荐）

### 方式一：双击 `start.bat`（推荐）

双击项目根目录下的 `start.bat`，脚本自动完成：
1. 创建 Python 虚拟环境并安装依赖
2. 安装前端 npm 依赖
3. 启动后端（端口 8000）和前端（端口 5173）
4. 自动打开浏览器

### 方式二：手动启动

```bash
# 终端 1 - 后端
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 终端 2 - 前端
cd frontend
npm install
npm run dev
```

### 配置

编辑 `.env` 文件（或 `backend/.env`）：

```env
# 必填：阿里云百炼 API Key（在 https://dashscope.console.aliyun.com 获取）
DASHSCOPE_API_KEY=sk-your-api-key-here

# 可选：切换模型
LLM_MODEL=qwen-plus   # qwen-plus / qwen-max / qwen-turbo
```

## 访问地址

- 前端页面：http://localhost:5173
- API 文档（Swagger）：http://localhost:8000/docs

## 默认账号

| 角色 | 用户名 | 密码 | 权限 |
|------|--------|------|------|
| 管理员 | admin | 123456 | 知识库管理 + 问答 + 统计 |
| 普通用户 | （自行注册） | - | 仅问答 |

## 使用流程

1. 用 `admin / 123456` 登录
2. 进入「知识库管理」→ 上传电商商品文档（PDF/Word/Excel 等）
3. 等待文档处理完成（状态变为"就绪"）
4. 切换到「知识库问答」→ 输入问题开始对话
5. 回答中会显示 `[来源N]` 引用，点击可查看原文片段

## 项目结构

```
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 应用入口
│   │   ├── config.py        # 配置管理
│   │   ├── dependencies.py  # 依赖注入（JWT 鉴权）
│   │   ├── routers/         # API 路由
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── schemas/         # Pydantic 校验
│   │   ├── services/        # 业务逻辑
│   │   ├── rag/             # RAG Pipeline
│   │   │   ├── ingestion.py # 文档处理流水线
│   │   │   ├── retriever.py # 混合检索+精排
│   │   │   ├── generator.py # LLM 流式生成
│   │   │   └── chain.py     # RAG 编排
│   │   └── database/        # 数据库配置
│   └── requirements.txt
├── frontend/                # React 前端
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 通用组件
│   │   ├── stores/          # Zustand 状态
│   │   ├── api/             # API 客户端
│   │   └── utils/           # 工具函数
│   └── package.json
├── start.bat                # Windows 一键启动
├── .env                     # 环境配置
└── README.md
```

## API 概览

### 认证 `/api/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录 |
| GET | `/api/auth/me` | 当前用户 |
| PUT | `/api/auth/change-password` | 修改密码 |

### 知识库 `/api/kb`（Admin）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/kb/upload` | 上传文档 |
| GET | `/api/kb/documents` | 文档列表 |
| DELETE | `/api/kb/documents/{id}` | 删除文档 |
| GET | `/api/kb/stats` | KB 统计 |

### 问答 `/api/chat`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/chat/sessions` | 会话列表 |
| POST | `/api/chat/sessions` | 创建会话 |
| POST | `/api/chat/sessions/{id}/stream` | SSE 流式问答 |
| GET | `/api/chat/sessions/{id}/export` | 导出对话 |
