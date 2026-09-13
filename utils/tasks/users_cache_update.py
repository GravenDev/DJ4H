import asyncio

import discord
from discord.ext import tasks

from config import LOGGER, USER_CACHE_SYNC_INTERVAL
from utils.database.dao.rngdle import RNGdleDao

USER_CACHE: dict[int, discord.User | None] = {}


async def init_user_cache():
    users = await RNGdleDao.get_all_registered_users()
    if not users:
        return
    for user in users:
        USER_CACHE[int(user.user_id)] = None


@tasks.loop(seconds=USER_CACHE_SYNC_INTERVAL)
async def user_cache_sync_task(bot: discord.Bot):

    async def update_user(user_id: int):
        user = await fetch_user(bot, user_id)
        if user and USER_CACHE.get(user_id) != user:
            USER_CACHE[user_id] = user
            return 1
        return 0

    LOGGER.info("Users cache sync: starting sync")

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(update_user(user_id)) for user_id in USER_CACHE.keys()]

    n_updated = sum(task.result() for task in tasks)

    LOGGER.info(f"Users cache sync: sync done (updated {n_updated})")


async def fetch_user(bot: discord.Bot, user_id: int) -> discord.User | None:
    try:
        user = await bot.fetch_user(user_id)
    except discord.NotFound:
        return None
    return user


async def get_or_fetch_user(bot: discord.Bot, user_id: int) -> discord.User | None:
    """Get a user from the bot's cache or fetch from Discord API."""
    # Try the bot cache (fast and reliable)
    user = bot.get_user(user_id)
    if user:
        return user

    # Try local cache (fast but may be outdated)
    user = USER_CACHE.get(user_id)
    if user:
        return user

    # Fetch the user entirely
    user = await fetch_user(bot, user_id)
    USER_CACHE[user_id] = user
    return user


if __name__ == "__main__":
    from config import DEBUG_GUILD_ID, setup_logging, BOT_TOKEN
    from utils.database import init_db

    setup_logging()

    bot = discord.AutoShardedBot(
        intents=discord.Intents.default(),
        help_command=None,  # Disable the default help command
        debug_guilds=[DEBUG_GUILD_ID] if DEBUG_GUILD_ID else None,
    )

    @bot.event
    async def on_ready():
        LOGGER.info("Testing locally")
        LOGGER.info("------")
        await init_db()
        LOGGER.info("Database initialized successfully.")
        LOGGER.info("------")

        bot_user = bot.user
        assert bot_user is not None
        USER_CACHE[bot_user.id] = None
        LOGGER.info(f"Cache: {USER_CACHE}")
        await user_cache_sync_task(bot)
        LOGGER.info(f"Cache: {USER_CACHE}")
        await bot.close()

    bot.run(BOT_TOKEN)
