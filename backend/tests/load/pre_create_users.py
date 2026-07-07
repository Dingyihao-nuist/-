"""
预创建测试用户脚本 — 批量注册、登录、创建会话，导出 Token 供 Locust 使用

用法:
  python pre_create_users.py --count 100 --admin-count 1 --create-sessions --upload-docs
  python pre_create_users.py --count 100 --resume          # 断点续建
  python pre_create_users.py --only-tokens                 # 仅刷新已创建用户的 Token
"""

import asyncio
import argparse
import json
import os
import sys
import uuid
from datetime import datetime
import httpx

# 默认配置
DEFAULT_BASE_URL = os.getenv("LOAD_TEST_BASE_URL", "http://localhost:8000")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "test_users.json")
REGISTER_LIMIT_DELAY = 12  # 遵守 5/min 限流：5/min → 至少 12 秒间隔
LOGIN_LIMIT_DELAY = 6      # 遵守 10/min 限流：10/min → 至少 6 秒间隔


async def register_user(client: httpx.AsyncClient, base_url: str, index: int, username_override: str = None) -> dict:
    """注册单个用户"""
    username = username_override or f"testuser_{index:04d}"
    payload = {
        "username": username,
        "email": f"{username}@test.com",
        "password": "TestPass123!",
    }
    resp = await client.post(f"{base_url}/api/auth/register", json=payload)
    if resp.status_code == 409:
        return {"status": "exists", "username": username}
    if resp.status_code != 201:
        raise Exception(f"注册失败 [{username}]: HTTP {resp.status_code} {resp.text}")
    data = resp.json()
    return {"status": "created", "username": username, "user_id": data.get("user_id")}


async def login_user(client: httpx.AsyncClient, base_url: str, username: str) -> dict:
    """登录用户获取 Token"""
    resp = await client.post(f"{base_url}/api/auth/login", json={
        "username": username,
        "password": "TestPass123!",
    })
    if resp.status_code != 200:
        raise Exception(f"登录失败 [{username}]: HTTP {resp.status_code} {resp.text}")
    data = resp.json()
    return {
        "username": username,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


async def create_sessions(client: httpx.AsyncClient, base_url: str, user: dict, count: int):
    """为用户创建 N 个聊天会话"""
    session_ids = []
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    titles = ["商品咨询", "物流查询", "退换货问题", "售后维修", "价格对比"]

    for i in range(min(count, len(titles))):
        resp = await client.post(
            f"{base_url}/api/chat/sessions",
            json={"title": titles[i]},
            headers=headers,
        )
        if resp.status_code == 201:
            session_ids.append(resp.json().get("id"))
        await asyncio.sleep(0.1)

    return session_ids


async def upload_test_document(client: httpx.AsyncClient, base_url: str, admin_user: dict):
    """上传测试文档到知识库"""
    # 创建测试文档
    docs_dir = os.path.join(os.path.dirname(__file__), "test_docs")
    os.makedirs(docs_dir, exist_ok=True)

    test_doc = os.path.join(docs_dir, "product_catalog.txt")
    if not os.path.exists(test_doc):
        with open(test_doc, "w", encoding="utf-8") as f:
            f.write("""# 电商平台商品目录

## 电子产品
1. 智能手表 Pro — ¥299 — 支持心率监测、血氧检测、GPS定位、IP68防水
2. 蓝牙耳机 Air — ¥159 — 主动降噪、续航24小时、Type-C充电
3. 无线充电板 — ¥79 — 15W快充、兼容iPhone和Android

## 家居用品
4. 乳胶枕头 — ¥199 — 天然乳胶、人体工学设计、透气防螨
5. 智能台灯 — ¥249 — 无蓝光危害、多档色温调节、触控开关
6. 空气炸锅 — ¥399 — 5.5L大容量、360度热风循环、LED触控屏

## 服饰鞋包
7. 运动跑鞋 — ¥359 — 缓震科技、透气网面、耐磨橡胶底
8. 双肩背包 — ¥189 — 防水面料、USB充电口、防盗设计
9. 防晒冲锋衣 — ¥429 — UV50+防晒、防风防水、可收纳帽兜

## 品质保障
- 全部商品支持7天无理由退货
- 质量问题30天内免费换新
- 全国联保，品牌授权经销
- 顺丰/京东物流配送，最快次日达

## 支付方式
- 支持支付宝、微信支付、银行卡、花呗分期（3/6/12期）
- 货到付款（部分地区）
""")

    headers = {"Authorization": f"Bearer {admin_user['access_token']}"}
    with open(test_doc, "rb") as f:
        files = {"files": ("product_catalog.txt", f, "text/plain")}
        resp = await client.post(
            f"{base_url}/api/kb/upload",
            files=files,
            headers=headers,
            timeout=60,
        )
    if resp.status_code == 200:
        print(f"  [OK] 测试文档上传成功")
    else:
        print(f"  [WARN] 文档上传: HTTP {resp.status_code}")


async def main():
    parser = argparse.ArgumentParser(description="预创建压测用户")
    parser.add_argument("--count", type=int, default=100, help="普通用户数量")
    parser.add_argument("--admin-count", type=int, default=1, help="管理员数量")
    parser.add_argument("--output", type=str, default=OUTPUT_FILE, help="输出文件路径")
    parser.add_argument("--base-url", type=str, default=DEFAULT_BASE_URL, help="后端地址")
    parser.add_argument("--create-sessions", action="store_true", help="为每个用户创建会话")
    parser.add_argument("--upload-docs", action="store_true", help="上传测试文档到知识库")
    parser.add_argument("--resume", action="store_true", help="从已有文件断点续建")
    parser.add_argument("--only-tokens", action="store_true", help="仅刷新已有用户的 Token")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    # 加载已有用户（断点续建）
    existing_users = []
    if args.resume or args.only_tokens:
        if os.path.exists(args.output):
            with open(args.output, "r", encoding="utf-8") as f:
                existing_users = json.load(f)
            print(f"加载已有用户记录: {len(existing_users)} 人")

    if args.only_tokens:
        # 仅刷新 Token
        new_users = []
        async with httpx.AsyncClient(timeout=30) as client:
            for i, user in enumerate(existing_users):
                try:
                    token_data = await login_user(client, args.base_url, user["username"])
                    user["access_token"] = token_data["access_token"]
                    user["refresh_token"] = token_data["refresh_token"]
                    new_users.append(user)
                    if (i + 1) % 10 == 0:
                        print(f"  刷新 Token: {i + 1}/{len(existing_users)}")
                except Exception as e:
                    print(f"  [ERROR] {e}")
                    new_users.append(user)  # 保留旧的 token
                await asyncio.sleep(LOGIN_LIMIT_DELAY)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(new_users, f, ensure_ascii=False, indent=2)
        print(f"\nToken 刷新完成: {len(new_users)} 人 → {args.output}")
        return

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: 注册管理员
        print("\n===== Step 1: 注册管理员 =====")
        admin_user = None
        for i in range(args.admin_count):
            try:
                admin_name = f"testuser_admin_{i}"
                result = await register_user(client, args.base_url, 0, username_override=admin_name)
                print(f"  {admin_name}: {result['status']}")
                await asyncio.sleep(REGISTER_LIMIT_DELAY)
            except Exception as e:
                print(f"  [ERROR] admin_{i}: {e}")

        # 登录管理员
        admin_data = await login_user(client, args.base_url, "testuser_admin_0")
        admin_user = {
            "username": "testuser_admin_0",
            "password": "TestPass123!",
            "access_token": admin_data["access_token"],
            "refresh_token": admin_data["refresh_token"],
            "role": "admin",
            "user_id": admin_data.get("user_id"),
        }
        print(f"  管理员登录成功: {admin_user['username']}")
        await asyncio.sleep(LOGIN_LIMIT_DELAY)

        # Step 2: 注册普通用户
        print(f"\n===== Step 2: 注册 {args.count} 个普通用户 ({args.count * REGISTER_LIMIT_DELAY // 60} 分钟) =====")
        start_index = len(existing_users)
        all_users = list(existing_users)

        for i in range(start_index, args.count):
            try:
                result = await register_user(client, args.base_url, i)
                if i % 10 == 0:
                    print(f"  进度: {i + 1}/{args.count} ({result['status']})")
            except Exception as e:
                print(f"  [ERROR] user_{i}: {e} (跳过)")

            if i < args.count - 1:
                await asyncio.sleep(REGISTER_LIMIT_DELAY)

        print(f"\n  注册完成: {args.count} 人")

        # Step 3: 登录所有用户获取 Token
        print(f"\n===== Step 3: 登录获取 Token ({args.count * LOGIN_LIMIT_DELAY // 60} 分钟) =====")
        for i in range(len(all_users), args.count):
            username = f"testuser_{i:04d}"
            try:
                token_data = await login_user(client, args.base_url, username)
                user_record = {
                    "username": username,
                    "password": "TestPass123!",
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data["refresh_token"],
                    "role": "user",
                    "user_id": i + 2,  # admin=1, users start from 2
                }
                all_users.append(user_record)

                if (i + 1) % 10 == 0:
                    print(f"  进度: {i + 1}/{args.count}")
                    # 每 10 个用户保存一次（防止中断丢失）
                    with open(args.output, "w", encoding="utf-8") as f:
                        json.dump(all_users, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  [ERROR] login {username}: {e}")

            await asyncio.sleep(LOGIN_LIMIT_DELAY)

        # 添加管理员到用户列表
        if admin_user:
            all_users.insert(0, admin_user)

        # 保存到文件
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(all_users, f, ensure_ascii=False, indent=2)
        print(f"\n  Token 保存完成: {len(all_users)} 人 → {args.output}")

        # Step 4: 为部分用户创建会话
        if args.create_sessions:
            print(f"\n===== Step 4: 创建会话 =====")
            count = 0
            for user in all_users:
                if user["role"] == "admin":
                    continue
                # 随机 2-5 个会话
                import random
                n = random.randint(2, 5)
                ids = await create_sessions(client, args.base_url, user, n)
                user["session_ids"] = ids
                count += 1
                if count % 10 == 0:
                    print(f"  进度: {count}/{args.count}")

            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(all_users, f, ensure_ascii=False, indent=2)
            print(f"  会话创建完成")

        # Step 5: 上传测试文档
        if args.upload_docs and admin_user:
            print(f"\n===== Step 5: 上传测试文档 =====")
            # 等待文档处理
            await upload_test_document(client, args.base_url, admin_user)
            await asyncio.sleep(10)  # 等待 Embedding 处理

    print(f"\n✅ 全部完成！共 {len(all_users)} 个用户")
    print(f"   输出文件: {args.output}")
    print(f"   管理员: {admin_user['username'] if admin_user else '无'}")
    print(f"   下一步: locust -f locustfile.py --web --host {args.base_url}")


if __name__ == "__main__":
    asyncio.run(main())
