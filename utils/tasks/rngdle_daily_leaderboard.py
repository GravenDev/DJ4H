import asyncio
from datetime import time, timezone
from io import BytesIO

import discord
from discord.ext import tasks

from config import LOGGER
from utils.database.dao.rngdle import (
    RNGdleDao,
    RNGdleGuildConfigDao,
    get_yesterday_range,
)
from utils.database.schema import RNGdle as RNGdleCol
from utils.image_generator import LeaderboardGenerator, RNGdleLeaderboardUser
from utils.tasks.rngdle_sync import rngdle_fetch_task
from utils.tasks.users_cache_update import get_or_fetch_user, init_user_cache


# Task runs at 1AM UTC because rngdle.com is unavailable around 0AM
@tasks.loop(time=time(hour=1, minute=0, tzinfo=timezone.utc))
async def rngdle_daily_leaderboard_task(bot: discord.Bot) -> None:
    configs = await RNGdleGuildConfigDao.get_all_configured_guilds()

    for config in configs:
        if config.leaderboard_channel_id is None:
            continue

        guild = bot.get_guild(config.guild_id)
        if guild is None:
            continue

        channel = guild.get_channel(config.leaderboard_channel_id)
        if channel is None or not isinstance(channel, discord.TextChannel):
            continue

        await rngdle_fetch_task()

        start_ts, end_ts = get_yesterday_range()
        scores = await RNGdleDao.get_scores_in_range(config.guild_id, start_ts, end_ts)

        if not scores:
            continue

        leaderboard_users: list[RNGdleLeaderboardUser] = []

        async def add_ldb_user(score_col: RNGdleCol, rank: int):
            user = await get_or_fetch_user(bot, int(score_col.user_id))
            if user is None:
                return

            score = int(score_col.score)
            number = int(score_col.number)
            u = await RNGdleLeaderboardUser.create_user_instance(user, score, number, rank)
            leaderboard_users.append(u)

        async with asyncio.TaskGroup() as tg:
            for index, score_col in enumerate(scores):
                tg.create_task(add_ldb_user(score_col, index + 1))

        generator = LeaderboardGenerator()
        generated = await generator.generate_leaderboard(leaderboard_users)
        buffer = BytesIO()
        generated.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename="leaderboard.png")

        top_score = scores[0].score
        top_users = [
            leaderboard_users[i].user for i, score in enumerate(scores) if score.score == top_score
        ]
        mentions = " ".join(
            u.mention if u.id != 610843701861679108 else "TnTube" for u in top_users
        )

        await channel.send(
            content=f"🏆 Daily RNGDLE leaderboard — Félicitations à {mentions} !",
            file=file,
        )

        LOGGER.info(f"Daily leaderboard sent to guild {config.guild_id} ({channel.name})")


@rngdle_daily_leaderboard_task.error
async def on_daily_leaderboard_error(exc: Exception) -> None:
    LOGGER.error(f"Daily leaderboard task error: {exc}")


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

        await init_user_cache()

        await rngdle_daily_leaderboard_task(bot)
        # Send a second time to test cache
        await rngdle_daily_leaderboard_task(bot)
        await bot.close()

    bot.run(BOT_TOKEN)
