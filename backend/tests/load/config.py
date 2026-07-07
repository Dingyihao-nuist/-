"""压测配置中心 — 所有可调参数集中于此，支持环境变量覆盖"""

import os
from dataclasses import dataclass, field


@dataclass
class LoadTestConfig:
    # ============ 目标服务 ============
    backend_base_url: str = os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8000")

    # ============ 测试规模 ============
    total_users: int = int(os.getenv("LOAD_TEST_USERS", "100"))
    spawn_rate: int = int(os.getenv("LOAD_TEST_SPAWN_RATE", "5"))  # 每秒启动用户数
    run_time: str = os.getenv("LOAD_TEST_RUN_TIME", "10m")       # "10m", "300s", "1h"

    # ============ 用户类型配比 ============
    regular_user_ratio: float = 0.85  # 85% 普通已注册用户
    new_user_ratio: float = 0.10      # 10% 新用户注册流程
    admin_user_ratio: float = 0.05    # 5% 管理员

    # ============ RegularUser 任务权重 ============
    weight_ask_question: int = 8       # SSE 流式问答（核心路径，40%）
    weight_browse_sessions: int = 3    # 浏览会话列表（15%）
    weight_view_messages: int = 3      # 查看消息历史（15%）
    weight_create_session: int = 2     # 创建新会话（10%）
    weight_give_feedback: int = 2      # 消息反馈（10%）
    weight_export_session: int = 1     # 导出对话（5%）
    weight_refresh_token: int = 1      # 刷新 Token（5%）

    # ============ AdminUser 任务权重 ============
    weight_list_documents: int = 4     # 查看文档列表
    weight_view_stats: int = 3         # 查看统计数据
    weight_upload_document: int = 1    # 上传文档（低频）
    weight_view_chunks: int = 1        # 查看分块
    weight_popular: int = 1            # 热门问题

    # ============ 思考时间（秒） ============
    think_time_min: float = float(os.getenv("LOAD_TEST_THINK_MIN", "2.0"))
    think_time_max: float = float(os.getenv("LOAD_TEST_THINK_MAX", "8.0"))
    # 提问后模拟阅读回复的额外等待
    reading_time_min: float = 5.0
    reading_time_max: float = 15.0

    # ============ 预创建数据路径 ============
    pre_created_users_file: str = os.path.join(
        os.path.dirname(__file__), "data", "test_users.json"
    )
    questions_pool_file: str = os.path.join(
        os.path.dirname(__file__), "questions_pool.json"
    )
    test_docs_dir: str = os.path.join(os.path.dirname(__file__), "test_docs")

    # ============ 压测场景 ============
    scenario: str = os.getenv("LOAD_TEST_SCENARIO", "full")
    # "full"           — 真实 DashScope + 真实 Embedding/Reranker（全链路）
    # "mock_llm_only"  — Mock LLM + 真实 Embedding/Reranker（隔离 DB+检索瓶颈）
    # "mock_all"       — Mock LLM + 预计算向量（纯 HTTP+DB 瓶颈）

    # ============ Token 管理 ============
    token_refresh_buffer: int = 300  # Token 距过期不足 5 分钟时自动刷新


# 全局单例
config = LoadTestConfig()
