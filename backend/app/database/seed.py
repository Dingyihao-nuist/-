"""种子数据：创建默认管理员用户"""

import asyncio
import os
import secrets
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.user import User
from app.utils.security import hash_password
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def seed_admin():
    async with AsyncSessionLocal() as db:
        # 检查是否已存在 admin 用户
        result = await db.execute(select(User).where(User.username == "admin"))
        existing = result.scalar_one_or_none()
        if existing:
            logger.info("管理员用户已存在，跳过种子数据")
            return

        # 从环境变量读取初始密码，否则生成随机强密码
        admin_password = os.getenv(
            "ADMIN_INITIAL_PASSWORD",
            secrets.token_urlsafe(16)
        )

        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password(admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        logger.info("管理员用户创建成功，请妥善保管密码")


if __name__ == "__main__":
    asyncio.run(seed_admin())
