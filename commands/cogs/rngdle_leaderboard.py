from io import BytesIO

import discord
from discord.ext import commands

from config import MAGIC_COLOR
from utils import get_or_fetch_user
from utils.database.dao.rngdle import RNGdleDao
from utils.image_generator import LeaderboardGenerator, LeaderboardUser


class RNGdleLeaderboard(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leaderboard_generator = LeaderboardGenerator()

    @commands.slash_command(
        name="rngdle-leaderboard",
        description="Show RNGDLE leaderboard",
    )
    async def rngdle_leaderboard(
        self, ctx: discord.ApplicationContext
    ) -> None:
        """Show RNGDLE leaderboard."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        scores = await RNGdleDao.get_today_scores(ctx.guild.id)
        if not scores:
            await ctx.respond("No today scores found.")
            return

        users: list[discord.User] = []
        for score in scores:
            user = await get_or_fetch_user(self.bot, score.user_id)
            if user is not None:
                users.append(user)

        leaderboard_user: list[LeaderboardUser] = []
        for user, score, rank in zip(users, scores, range(len(users))):
            user_ = LeaderboardUser()
            user_.user = user
            user_.score = str(score.score)
            user_.tirage = str(score.number)
            user_.rank = rank + 1
            leaderboard_user.append(user_)

        generated_leaderboard = (
            await self.leaderboard_generator.generate_leaderboard(
                leaderboard_user
            )
        )
        buffer = BytesIO()
        generated_leaderboard.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename="leaderboard.png")

        await ctx.respond(file=file)


def setup(bot):
    bot.add_cog(RNGdleLeaderboard(bot))
