@echo off
chcp 65001 >nul
title 电商RAG知识库问答系统 - 启动中...

echo ============================================
echo   电商RAG知识库问答系统
echo   正在启动...
echo ============================================

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查 Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

:: 检查 Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

:: 创建数据目录
if not exist "backend\data" mkdir backend\data
if not exist "backend\data\uploads" mkdir backend\data\uploads
if not exist "backend\data\chroma" mkdir backend\data\chroma

:: 复制 .env 到 backend 目录（如果 backend 下不存在）
if not exist "backend\.env" (
    if exist ".env" (
        copy ".env" "backend\.env" >nul
    )
)

echo [1/4] 检查后端依赖...
if not exist "backend\venv" (
    echo   创建 Python 虚拟环境...
    python -m venv backend\venv
    echo   安装 Python 依赖包...
    call backend\venv\Scripts\activate.bat
    pip install -r backend\requirements.txt -q
) else (
    call backend\venv\Scripts\activate.bat
)

echo [2/4] 检查前端依赖...
if not exist "frontend\node_modules" (
    echo   安装前端 npm 依赖包...
    cd frontend
    call npm install
    cd ..
)

echo [3/4] 启动后端服务 (端口 8000)...
start "RAG后端-API服务" cmd /c "cd /d %~dp0backend && %~dp0backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

:: 等待后端启动
timeout /t 3 /nobreak >nul

echo [4/4] 启动前端页面 (端口 5173)...
start "RAG前端-Web界面" cmd /c "cd /d %~dp0frontend && npm run dev"

:: 等待前端启动
timeout /t 3 /nobreak >nul

:: 打开浏览器
start http://localhost:5173

echo.
echo ============================================
echo   启动完成！
echo   前端页面: http://localhost:5173
echo   API文档:  http://localhost:8000/docs
echo   管理员账号: admin / 123456
echo ============================================
echo.
echo 提示：关闭本窗口不会停止服务。
echo       请分别关闭 "RAG后端-API服务" 和 "RAG前端-Web界面" 窗口来停止服务。
echo.
pause
