# -*- coding: utf-8 -*-
"""
@Time    : 2025/7/16 21:15
@Author  : QIN2DIM
@GitHub  : https://github.com/QIN2DIM
@Desc    :
"""
import json
import os
from pathlib import Path
from typing import List, Optional

from hcaptcha_challenger.agent import AgentConfig
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent
VOLUMES_DIR = PROJECT_ROOT.joinpath("volumes")

LOG_DIR = VOLUMES_DIR.joinpath("logs")
USER_DATA_DIR = VOLUMES_DIR.joinpath("user_data")

RUNTIME_DIR = VOLUMES_DIR.joinpath("runtime")
SCREENSHOTS_DIR = VOLUMES_DIR.joinpath("screenshots")
RECORD_DIR = VOLUMES_DIR.joinpath("record")
HCAPTCHA_DIR = VOLUMES_DIR.joinpath("hcaptcha")


class EpicAccount(BaseModel):
    email: str
    password: str

    def __str__(self):
        return self.email


class EpicSettings(AgentConfig):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

    EPIC_EMAIL: Optional[str] = Field(
        default=None,
        description="Epic 游戏账号（单账号模式，已弃用，请使用 EPIC_ACCOUNTS）",
    )

    EPIC_PASSWORD: Optional[SecretStr] = Field(
        default=None,
        description="Epic 游戏密码（单账号模式，已弃用，请使用 EPIC_ACCOUNTS）",
    )

    EPIC_ACCOUNTS: Optional[str] = Field(
        default=None,
        description="Epic 游戏账号列表（JSON 格式）",
    )

    DISABLE_BEZIER_TRAJECTORY: bool = Field(
        default=True, description="是否关闭贝塞尔曲线轨迹模拟，默认关闭，直接使用 Camoufox 的特性"
    )

    cache_dir: Path = HCAPTCHA_DIR.joinpath(".cache")
    challenge_dir: Path = HCAPTCHA_DIR.joinpath(".challenge")
    captcha_response_dir: Path = HCAPTCHA_DIR.joinpath(".captcha")

    ENABLE_APSCHEDULER: bool = Field(default=True, description="是否启用定时任务，默认启用")

    TASK_TIMEOUT_SECONDS: int = Field(
        default=900,  # 15 minutes
        description="Maximum execution time for browser tasks before force termination",
    )

    # Celery and Redis settings
    REDIS_URL: str = Field(
        default="redis://redis:6379/0", description="Redis URL for Celery broker and result backend"
    )

    CELERY_WORKER_CONCURRENCY: int = Field(
        default=1, description="Number of concurrent Celery workers"
    )

    CELERY_TASK_TIME_LIMIT: int = Field(
        default=1200,  # 20 minutes - slightly higher than TASK_TIMEOUT_SECONDS
        description="Celery task hard time limit in seconds",
    )

    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=900,  # 15 minutes - same as TASK_TIMEOUT_SECONDS
        description="Celery task soft time limit in seconds",
    )

    # APPRISE_SERVERS: str | None = Field(
    #     default="", description="System notification by Apprise\nhttps://github.com/caronc/apprise"
    # )

    def get_accounts(self) -> List[EpicAccount]:
        accounts = []

        if self.EPIC_ACCOUNTS:
            try:
                accounts_data = json.loads(self.EPIC_ACCOUNTS)
                if isinstance(accounts_data, list):
                    for acc in accounts_data:
                        if isinstance(acc, dict):
                            accounts.append(EpicAccount(
                                email=acc.get("email"),
                                password=acc.get("password")
                            ))
                        elif isinstance(acc, str):
                            parts = acc.split(":")
                            if len(parts) == 2:
                                accounts.append(EpicAccount(email=parts[0], password=parts[1]))
            except json.JSONDecodeError as e:
                raise ValueError(f"EPIC_ACCOUNTS JSON 格式错误: {e}")

        elif self.EPIC_EMAIL and self.EPIC_PASSWORD:
            accounts.append(EpicAccount(
                email=self.EPIC_EMAIL,
                password=self.EPIC_PASSWORD.get_secret_value()
            ))

        if not accounts:
            raise ValueError("未配置 Epic 账号，请设置 EPIC_ACCOUNTS 或 EPIC_EMAIL/EPIC_PASSWORD")

        return accounts

    def get_user_data_dir(self, email: str) -> Path:
        target_ = USER_DATA_DIR.joinpath(email)
        if not target_.is_dir():
            target_.mkdir(parents=True, exist_ok=True)
        return target_

    @property
    def user_data_dir(self) -> Path:
        accounts = self.get_accounts()
        if len(accounts) == 1:
            return self.get_user_data_dir(accounts[0].email)
        else:
            return USER_DATA_DIR


settings = EpicSettings()
settings.ignore_request_questions = ["Please drag the crossing to complete the lines"]
