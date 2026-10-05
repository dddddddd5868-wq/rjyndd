import asyncio
import os
import sys

from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()


async def main():
    url = sys.argv[1]
    bot = Bot(token=os.environ["BOT_TOKEN"])
    await bot.set_webhook(
        url,
        secret_token=os.environ.get("WEBHOOK_SECRET") or None,
        drop_pending_updates=True,
    )
    print(await bot.get_webhook_info())
    await bot.session.close()


asyncio.run(main())