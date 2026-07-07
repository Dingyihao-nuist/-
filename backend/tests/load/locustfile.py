"""
LangChainRAG — 100 并发用户压力测试脚本

三种虚拟用户类型:
  RegularUser (85%) — 已注册用户核心流程：提问 SSE > 浏览 > 查看消息 > 创建会话
  NewUserFlow  (10%) — 新用户注册+首次对话
  AdminUser    (5%)  — 知识库管理+统计查询

自定义 SSE 指标:
  - SSE first_token:  首 token 到达时间 (TTFT)
  - SSE full_response: 完整响应时间

用法:
  locust -f locustfile.py --web --host http://localhost:8000
  locust -f locustfile.py --headless --users 100 --spawn-rate 5 --run-time 10m
"""

import json
import os
import random
import time
from locust import HttpUser, task, between, events
from locust.exception import StopUser

# ============ 加载预创建用户和问题池 ============

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "test_users.json")
QUESTIONS_FILE = os.path.join(os.path.dirname(__file__), "questions_pool.json")

TEST_USERS = []
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        TEST_USERS = json.load(f)

QUESTIONS = []
if os.path.exists(QUESTIONS_FILE):
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        QUESTIONS = json.load(f)


def load_users():
    """每次调用时重新加载用户文件（支持运行时更新）"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ============ SQLite 锁竞争监控 ============

DB_LOCK_ERRORS = 0
HTTP_500_ERRORS = 0
SSE_INTERRUPTS = 0


@events.request.add_listener
def monitor_db_locks(request_type, name, response_time, response_length,
                     exception, context=None, **kwargs):
    """捕获 SQLite 锁错误和 SSE 中断"""
    global DB_LOCK_ERRORS, HTTP_500_ERRORS, SSE_INTERRUPTS

    if exception:
        error_str = str(exception).lower()
        if any(kw in error_str for kw in [
            "database is locked", "database locked",
            "sqlite_busy", "operationalerror",
        ]):
            DB_LOCK_ERRORS += 1
        # SSE 流中断
        if "sse" in name.lower() and "token" not in name.lower():
            SSE_INTERRUPTS += 1

    if context is not None and hasattr(context, 'response') and context.response is not None:
        if context.response.status_code == 500:
            HTTP_500_ERRORS += 1


@events.test_stop.add_listener
def report_db_lock_stats(environment, **kwargs):
    """压测结束时输出汇总统计"""
    print("\n" + "=" * 60)
    print("  SQLite 锁竞争统计")
    print("=" * 60)
    total = environment.stats.total.num_requests
    print(f"  明确锁错误:     {DB_LOCK_ERRORS}")
    print(f"  HTTP 500 错误:  {HTTP_500_ERRORS}")
    print(f"  SSE 流中断:     {SSE_INTERRUPTS}")
    print(f"  总请求数:       {total}")
    if total > 0:
        print(f"  锁错误占比:     {DB_LOCK_ERRORS / total * 100:.2f}%")
        print(f"  500 错误占比:   {HTTP_500_ERRORS / total * 100:.2f}%")
    print("=" * 60 + "\n")


# ============ RegularUser (85%) ============


class RegularUser(HttpUser):
    """
    已注册用户 — 模拟真实用户的完整对话流程

    任务权重:
      ask_question     (40%) - SSE 流式问答
      browse_sessions  (15%) - 浏览会话列表
      view_messages    (15%) - 查看历史消息
      create_session   (10%) - 创建新会话
      give_feedback    (10%) - 消息反馈
      export_session   (5%)  - 导出对话
      refresh_token    (5%)  - 刷新 JWT Token
    """
    weight = 85
    wait_time = between(2.0, 8.0)

    def on_start(self):
        """初始化：加载用户凭据"""
        users = load_users()
        if not users:
            raise StopUser("没有可用的测试用户，请先运行 pre_create_users.py")

        self.user_data = random.choice(users)
        self.token = self.user_data["access_token"]
        self.refresh_token = self.user_data.get("refresh_token")
        self.token_obtained_at = time.time()
        self.session_ids = self.user_data.get("session_ids", [])

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _ensure_token_valid(self):
        """Token 距过期不足 5 分钟时自动刷新"""
        if time.time() - self.token_obtained_at > 25 * 60:
            with self.client.post(
                "/api/auth/refresh",
                json={"refresh_token": self.refresh_token},
                name="POST /api/auth/refresh (auto)",
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    self.token = data["access_token"]
                    self.refresh_token = data.get("refresh_token", self.refresh_token)
                    self.token_obtained_at = time.time()
                    self.headers["Authorization"] = f"Bearer {self.token}"
                else:
                    raise StopUser("Token 刷新失败")

    @task(8)
    def ask_question(self):
        """SSE 流式问答（核心路径）"""
        self._ensure_token_valid()

        # 如果没有会话，先创建一个
        if not self.session_ids:
            with self.client.post(
                "/api/chat/sessions",
                json={"title": "商品咨询"},
                headers=self.headers,
                name="POST /api/chat/sessions (auto-create)",
                catch_response=True,
            ) as resp:
                if resp.status_code == 201:
                    sid = resp.json().get("id")
                    if sid:
                        self.session_ids.append(sid)
                else:
                    return

        session_id = random.choice(self.session_ids)
        question_data = random.choice(QUESTIONS) if QUESTIONS else {"question": "这个产品怎么样？"}
        question = question_data["question"]

        # 自定义 SSE 流式请求
        self._measure_sse_stream(session_id, question)

        # 提问后模拟阅读回复
        reading_time = random.uniform(5.0, 15.0)
        time.sleep(reading_time)

    def _measure_sse_stream(self, session_id: int, question: str):
        """测量 SSE 流式端点：首 token 时间 + 完整响应时间"""
        url = f"/api/chat/sessions/{session_id}/stream"
        start_time = time.monotonic()
        first_token_time = None
        total_tokens = 0

        try:
            with self.client.post(
                url,
                json={"question": question},
                headers=self.headers,
                stream=True,
                timeout=120,
                catch_response=True,
                name="POST /api/chat/sessions/{id}/stream",
            ) as resp:
                if resp.status_code != 200:
                    events.request.fire(
                        request_type="POST",
                        name="stream (HTTP error)",
                        response_time=int((time.monotonic() - start_time) * 1000),
                        response_length=0,
                        exception=Exception(f"HTTP {resp.status_code}"),
                    )
                    return

                # 逐行解析 SSE 事件
                remaining = ""
                for chunk in resp.iter_content(chunk_size=1, decode_unicode=True):
                    if chunk is None:
                        continue
                    # 收集行
                    remaining += chunk
                    while "\n" in remaining:
                        line, remaining = remaining.split("\n", 1)
                        line = line.strip()
                        if not line or line.startswith(":"):
                            continue

                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                continue
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            event_type = data.get("type")

                            if event_type == "token" and first_token_time is None:
                                first_token_time = time.monotonic() - start_time
                                events.request.fire(
                                    request_type="SSE",
                                    name="first_token",
                                    response_time=int(first_token_time * 1000),
                                    response_length=0,
                                )
                                total_tokens += 1

                            elif event_type == "token":
                                total_tokens += 1

                            elif event_type == "done":
                                total_time = time.monotonic() - start_time
                                events.request.fire(
                                    request_type="SSE",
                                    name="full_response",
                                    response_time=int(total_time * 1000),
                                    response_length=total_tokens,
                                )

                            elif event_type == "error":
                                events.request.fire(
                                    request_type="SSE",
                                    name="full_response",
                                    response_time=int((time.monotonic() - start_time) * 1000),
                                    response_length=0,
                                    exception=Exception(data.get("message", "SSE error")),
                                )
                                return

                # 如果走到这里但没有 first_token，说明连接中断
                if first_token_time is None:
                    raise Exception("SSE stream ended without token events")

        except Exception as e:
            events.request.fire(
                request_type="SSE",
                name="full_response",
                response_time=0,
                response_length=0,
                exception=e,
            )

    @task(3)
    def browse_sessions(self):
        """浏览会话列表"""
        self._ensure_token_valid()
        self.client.get(
            "/api/chat/sessions?page=1",
            headers=self.headers,
            name="GET /api/chat/sessions",
        )

    @task(3)
    def view_messages(self):
        """查看历史消息"""
        self._ensure_token_valid()
        if self.session_ids:
            sid = random.choice(self.session_ids)
            self.client.get(
                f"/api/chat/sessions/{sid}/messages",
                headers=self.headers,
                name="GET /api/chat/sessions/{id}/messages",
            )

    @task(2)
    def create_session(self):
        """创建新会话"""
        self._ensure_token_valid()
        titles = ["商品咨询", "物流查询", "售后问题", "新品推荐", "价格了解"]
        with self.client.post(
            "/api/chat/sessions",
            json={"title": random.choice(titles)},
            headers=self.headers,
            name="POST /api/chat/sessions",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                sid = resp.json().get("id")
                if sid:
                    self.session_ids.append(sid)
                    # 限制本地缓存的会话数量
                    if len(self.session_ids) > 10:
                        self.session_ids = self.session_ids[-10:]

    @task(2)
    def give_feedback(self):
        """消息反馈"""
        self._ensure_token_valid()
        # 给一个随机 message_id 发反馈（用 1-1000 范围模拟）
        msg_id = random.randint(1, 1000)
        self.client.put(
            f"/api/chat/messages/{msg_id}/feedback",
            json={"feedback": random.choice([True, False])},
            headers=self.headers,
            name="PUT /api/chat/messages/{id}/feedback",
        )

    @task(1)
    def export_session(self):
        """导出对话"""
        self._ensure_token_valid()
        if self.session_ids:
            sid = random.choice(self.session_ids)
            self.client.get(
                f"/api/chat/sessions/{sid}/export?format=md",
                headers=self.headers,
                name="GET /api/chat/sessions/{id}/export",
            )

    @task(1)
    def refresh_token(self):
        """手动刷新 Token"""
        with self.client.post(
            "/api/auth/refresh",
            json={"refresh_token": self.refresh_token},
            headers={"Content-Type": "application/json"},
            name="POST /api/auth/refresh",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                self.token_obtained_at = time.time()
                self.headers["Authorization"] = f"Bearer {self.token}"
            # 400+也继续（不影响用户状态）


# ============ NewUserFlow (10%) ============


class NewUserFlow(HttpUser):
    """新用户注册 + 首次对话的端到端流程"""
    weight = 10
    wait_time = between(3.0, 10.0)

    def on_start(self):
        """注册新用户"""
        # 分散注册时间（5/min 限流）
        delay = random.uniform(0, 20)
        time.sleep(delay)

        uid = uuid_short()
        self.username = f"loadtest_{uid}"
        self.password = "TestPass123!"

        # 注册
        with self.client.post(
            "/api/auth/register",
            json={
                "username": self.username,
                "email": f"{self.username}@load.test",
                "password": self.password,
            },
            name="POST /api/auth/register (new user)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 429:
                time.sleep(15)
                resp.success()
            elif resp.status_code == 201:
                pass
            elif resp.status_code == 409:
                pass  # 可能冲突，继续登录

        # 登录
        with self.client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
            name="POST /api/auth/login (new user)",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self.token = data["access_token"]
                self.refresh_token = data.get("refresh_token")
                self.headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                }
            elif resp.status_code == 429:
                time.sleep(10)
                resp.success()
            else:
                raise StopUser("新用户登录失败")

    @task(10)
    def first_chat_flow(self):
        """首次对话流程：创建会话 → 提问 → 追问"""
        # 创建会话
        with self.client.post(
            "/api/chat/sessions",
            json={"title": "首次咨询"},
            headers=self.headers,
            name="POST /api/chat/sessions (new user)",
            catch_response=True,
        ) as resp:
            if resp.status_code != 201:
                return
            session_id = resp.json().get("id")
            if not session_id:
                return

        # 首次提问
        question = random.choice([
            "你好，我想了解一下你们的产品",
            "有什么推荐的热门商品吗？",
            "请问怎么下单购买？",
            "新用户有什么优惠吗？",
        ])

        self._simple_sse(session_id, question, "first_question")

        # 追问
        time.sleep(random.uniform(3, 8))
        follow_up = random.choice([
            "价格方面能再说说吗？",
            "有优惠吗？",
            "好的谢谢",
        ])

        self._simple_sse(session_id, follow_up, "follow_up")

    def _simple_sse(self, session_id: int, question: str, label: str):
        """简化的 SSE 流式请求测量"""
        url = f"/api/chat/sessions/{session_id}/stream"
        start_time = time.monotonic()
        try:
            with self.client.post(
                url,
                json={"question": question},
                headers=self.headers,
                stream=True,
                timeout=30,
                catch_response=True,
                name=f"POST stream ({label})",
            ) as resp:
                if resp.status_code != 200:
                    return
                for line in resp.iter_lines(decode_unicode=True):
                    if line and "done" in line:
                        break
            events.request.fire(
                request_type="SSE",
                name=f"{label}_complete",
                response_time=int((time.monotonic() - start_time) * 1000),
                response_length=0,
            )
        except Exception:
            pass


# ============ AdminUser (5%) ============


class AdminUser(HttpUser):
    """管理员用户 — 知识库管理 + 统计查询"""
    weight = 5
    wait_time = between(3.0, 12.0)

    def on_start(self):
        users = load_users()
        admins = [u for u in users if u.get("role") == "admin"]
        if admins:
            admin = random.choice(admins)
        else:
            # 用第一个有 token 的用户（可能不是 admin，但至少能测试端点错误响应）
            admin = random.choice(users) if users else None
            if not admin:
                raise StopUser("没有管理员用户")

        self.token = admin["access_token"]
        self.refresh_token = admin.get("refresh_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @task(4)
    def list_documents(self):
        self.client.get(
            "/api/kb/documents?page=1&per_page=20",
            headers=self.headers,
            name="GET /api/kb/documents",
        )

    @task(3)
    def view_stats(self):
        self.client.get(
            "/api/stats/overview",
            headers=self.headers,
            name="GET /api/stats/overview",
        )

    @task(1)
    def upload_document(self):
        """上传测试文档（低频，重量级）"""
        # 使用已有的测试文档
        docs_dir = os.path.join(os.path.dirname(__file__), "test_docs")
        doc_path = os.path.join(docs_dir, "product_catalog.txt")
        if not os.path.exists(doc_path):
            return

        with open(doc_path, "rb") as f:
            files = {"files": ("load_test.txt", f, "text/plain")}
            self.client.post(
                "/api/kb/upload",
                files=files,
                headers={"Authorization": f"Bearer {self.token}"},
                name="POST /api/kb/upload",
                timeout=60,
            )

    @task(1)
    def view_chunks(self):
        """查看随机文档的分块"""
        doc_id = random.randint(1, 20)
        self.client.get(
            f"/api/kb/documents/{doc_id}/chunks",
            headers=self.headers,
            name="GET /api/kb/documents/{id}/chunks",
        )

    @task(1)
    def popular_questions(self):
        self.client.get(
            "/api/stats/popular?limit=10",
            headers=self.headers,
            name="GET /api/stats/popular",
        )


# ============ 辅助函数 ============


def uuid_short():
    """生成短 UUID"""
    import uuid
    return uuid.uuid4().hex[:8]
