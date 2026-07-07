---
name: rebuild-app
description: "构建并打包整个项目: 编译前端 Vite, 导出 Python 依赖, 生成可发布的 dist 目录。"
---

# /rebuild-app — 项目构建与打包

将整个 LangChainRAG 项目（前端 + 后端）构建并打包到一个可直接分发的 `dist/` 目录中。

## 前置条件

- Node.js 18+（前端构建）
- Python 3.11+（后端依赖导出）
- 项目根目录下的 `backend/` 和 `frontend/` 子目录

## 构建流程

### 步骤 1：构建前端

```bash
cd frontend
npm install              # 如果 node_modules 不存在
npm run build            # Vite 生产构建 → frontend/dist/
cd ..
```

前端构建产物默认输出到 `frontend/dist/`。

### 步骤 2：准备后端

```bash
cd backend
# 导出当前虚拟环境的精确依赖版本
.\venv\Scripts\python.exe -m pip freeze > requirements-freeze.txt 2>NUL || python -m pip freeze > requirements-freeze.txt
cd ..
```

### 步骤 3：组装发布包

```bash
# 如果存在旧的 dist 目录，先清理
rm -rf dist 2>NUL || rmdir /s /q dist 2>NUL

# 创建发布目录结构
mkdir dist\app\backend
mkdir dist\app\frontend
mkdir dist\app\data

# 复制后端源码和依赖声明
xcopy backend\app dist\app\backend\app /E /I /Y
xcopy backend\requirements.txt dist\app\backend\ /Y
xcopy backend\requirements-freeze.txt dist\app\backend\ /Y 2>NUL

# 复制前端构建产物
xcopy frontend\dist dist\app\frontend /E /I /Y

# 复制启动脚本
copy start.bat dist\ /Y
```

### 步骤 4：验证

确认 `dist/` 目录结构完整：

```
dist/
├── start.bat
└── app/
    ├── backend/
    │   ├── app/          # Python 后端源码
    │   ├── requirements.txt
    │   └── requirements-freeze.txt
    ├── frontend/         # Vite 构建产物
    └── data/             # 运行时的数据目录
```

## 输出

| 产物 | 路径 | 说明 |
|------|------|------|
| 前端构建 | `frontend/dist/` | Vite 生产构建（静态 HTML/JS/CSS） |
| 后端依赖快照 | `backend/requirements-freeze.txt` | 当前 venv 的精确版本锁定 |
| 发布包 | `dist/` | 可直接分发的完整项目包 |

## 注意事项

- 前端 `npm run build` 会在 `frontend/dist/` 生成压缩优化后的静态文件
- 后端 `pip freeze` 导出的 `requirements-freeze.txt` 用于在新环境精确还原依赖
- `dist/` 中的 `start.bat` 可能需要根据目标环境调整路径
- `.env` 文件不会自动复制到 dist，需要单独配置
