import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO

import discord

from config import LOGGER
from utils import get_or_fetch_user
from utils.database.dao.rngdle import RNGdleDao, RNGdleGuildConfigDao, get_yesterday_range
from utils.image_generator import LeaderboardGenerator, LeaderboardUser


async def send_daily_leaderboard(bot: discord.Bot) -> None:
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

        start_ts, end_ts = get_yesterday_range()
        scores = await RNGdleDao.get_scores_in_range(config.guild_id, start_ts, end_ts)

        if not scores:
            continue

        users: list[discord.User] = []
        for score in scores:
            user = await get_or_fetch_user(bot, score.user_id)
            if user is not None:
                users.append(user)

        if not users:
            continue

        generator = LeaderboardGenerator()
        leaderboard_users: list[LeaderboardUser] = []
        for user, score, rank in zip(users, scores, range(len(users))):
            u = LeaderboardUser()
            u.user = user
            u.score = f"{score.score}({score.number})"
            u.rank = rank + 1
            leaderboard_users.append(u)

        generated = await generator.generate_leaderboard(leaderboard_users, 200)
        buffer = BytesIO()
        generated.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename="leaderboard.png")

        top_score = scores[0].score
        top_users = [
            users[i]
            for i, score in enumerate(scores)
            if score.score == top_score
        ]
        mentions = " ".join(u.mention for u in top_users)

        await channel.send(
            content=f"🏆 Daily RNGDLE leaderboard — Félicitations à {mentions} !",
            file=file,
        )

        LOGGER.info(
            f"Daily leaderboard sent to guild {config.guild_id} ({channel.name})"
        )


async def rngdle_daily_leaderboard_loop(bot: discord.Bot) -> None:
    while True:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        sleep_seconds = (next_midnight - now).total_seconds()

        LOGGER.info(
            f"Daily leaderboard task: sleeping {sleep_seconds:.0f}s until midnight UTC"
        )
        await asyncio.sleep(sleep_seconds)

        try:
            await send_daily_leaderboard(bot)
        except Exception:
            LOGGER.exception("Failed to send daily leaderboard")


def schedule_rngdle_daily_leaderboard(bot: discord.Bot) -> None:
    try:
        bot.loop.create_task(rngdle_daily_leaderboard_loop(bot))
        LOGGER.info("RNGdle daily leaderboard task scheduled")
    except Exception:
        LOGGER.exception("Failed to schedule RNGdle daily leaderboard")
