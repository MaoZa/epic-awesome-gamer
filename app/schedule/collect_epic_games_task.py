# -*- coding: utf-8 -*-
"""
@Time    : 2025/7/16 21:57
@Author  : QIN2DIM
@GitHub  : https://github.com/QIN2DIM
@Desc    :
"""
import asyncio
import sys
from contextlib import suppress
from typing import List

from browserforge.fingerprints import Screen
from camoufox import AsyncCamoufox
from loguru import logger
from playwright.async_api import Page
from playwright.async_api import ViewportSize

from services.epic_authorization_service import EpicAuthorization
from services.epic_games_service import EpicAgent
from settings import LOG_DIR, RECORD_DIR, settings, EpicAccount
from utils import init_log
from extensions.ext_celery import ext_celery_app

init_log(
    runtime=LOG_DIR.joinpath("runtime.log"),
    error=LOG_DIR.joinpath("error.log"),
    serialize=LOG_DIR.joinpath("serialize.log"),
)


async def add_games_to_cart(page: Page, urls: List[str] | None = None):
    """
    检测点功能，在登录后，控制前往指定站点点击 Add To Cart 操作
    Args:
        page:
        urls:

    Returns:

    """
    agent = EpicAgent(page)

    urls = urls or [
        "https://store.epicgames.com/en-US/p/bloompunk-2fd3fd",
        "https://store.epicgames.com/en-US/p/fall-guys",
        "https://store.epicgames.com/en-US/p/lords-of-the-fallen-2-lords-of-the-fallen-free-coop-mode-81b41f",
        "https://store.epicgames.com/en-US/p/once-upon-a-puppet-08ad66",
    ]
    await agent.epic_games.add_promotion_to_cart(page, urls=urls)
    await page.goto("https://store.epicgames.com/en-US/cart", wait_until="networkidle")
    await page.wait_for_timeout(5000)


async def collect_games(page: Page):
    """
    采集周免游戏
    Args:
        page:

    Returns:

    """
    agent = EpicAgent(page)
    await agent.collect_epic_games()


async def authorize(page: Page, account: EpicAccount):
    agent = EpicAuthorization(page, account)
    await agent.invoke()


async def collect_games_for_account(account: EpicAccount):
    headless = "virtual" if "linux" in sys.platform else False
    user_data_dir = settings.get_user_data_dir(account.email)

    logger.info(f"Starting task for account: {account.email}")

    async with AsyncCamoufox(
        persistent_context=True,
        user_data_dir=user_data_dir,
        screen=Screen(max_width=1920, max_height=1080, min_height=1080, min_width=1920),
        record_video_dir=RECORD_DIR,
        record_video_size=ViewportSize(width=1920, height=1080),
        humanize=0.2,
        headless=headless,
    ) as browser:
        page = browser.pages[0] if browser.pages else await browser.new_page()

        agent = EpicAuthorization(page, account)
        await agent.invoke()

        game_page = await browser.new_page()
        agent = EpicAgent(game_page)
        await agent.collect_epic_games()

        with suppress(Exception):
            for p in browser.pages:
                await p.close()

        with suppress(Exception):
            await browser.close()

    logger.success(f"Task completed for account: {account.email}")


@ext_celery_app.task(queue="epic-awesome-gamer")
async def collect_epic_games_task():
    accounts = settings.get_accounts()
    logger.info(f"Found {len(accounts)} account(s) to process")

    for account in accounts:
        try:
            await collect_games_for_account(account)
        except Exception as e:
            logger.error(f"Failed to process account {account.email}: {e}")
            continue


if __name__ == '__main__':
    asyncio.run(collect_epic_games_task())
