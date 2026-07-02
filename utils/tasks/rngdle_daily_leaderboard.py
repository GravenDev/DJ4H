from datetime import time, timezone
from io import BytesIO

import discord
from discord.ext import tasks

from config import LOGGER
from utils import get_or_fetch_user
from utils.database.dao.rngdle import RNGdleDao, RNGdleGuildConfigDao, get_yesterday_range
from utils.image_generator import LeaderboardGenerator, RNGdleLeaderboardUser
from utils.number_utils import format_number


@tasks.loop(time=time(hour=0, minute=0, tzinfo=timezone.utc))
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
        leaderboard_users: list[RNGdleLeaderboardUser] = []
        for user, score, rank in zip(users, scores, range(len(users))):
            u = RNGdleLeaderboardUser()
            u.user = user
            u.score = format_number(score.score)
            u.tirage = str(score.number)
            u.rank = rank + 1
            leaderboard_users.append(u)

        generated = await generator.generate_leaderboard(leaderboard_users)
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


@rngdle_daily_leaderboard_task.error
async def on_daily_leaderboard_error(exc: Exception) -> None:
    LOGGER.error(f"Daily leaderboard task error: {exc}")
