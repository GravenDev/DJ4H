from io import BytesIO

import discord
from discord.ext import commands

from config import LOGGER
from utils import get_or_fetch_user
from utils.database.dao.users import UserDao
from utils.image_generator import LeaderboardGenerator, LeaderboardUser


class JD4HLeaderboard(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leaderboard_generator = LeaderboardGenerator()

    @commands.slash_command(
        name="jd4h-leaderboard",
        description="Show JD4H leaderboard",
    )
    async def jd4h_leaderboard(self, ctx: discord.ApplicationContext) -> None:
        """Show JD4H leaderboard."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        leaderboard = await UserDao.get_leaderboard(ctx.guild.id, 10)

        if not leaderboard:
            await ctx.respond("No users found in the leaderboard.")
            return

        users: list[LeaderboardUser] = []
        for user in leaderboard:
            user_data = await get_or_fetch_user(self.bot, user.user_id)
            if user_data is None:
                continue
            user_ = LeaderboardUser()
            user_.user = user_data
            user_.score = str(user.score)
            user_.rank = await UserDao.get_rank(user.user_id, user.guild_id)
            users.append(user_)

        generated_leaderboard = (
            await self.leaderboard_generator.generate_leaderboard(users)
        )
        buffer = BytesIO()
        generated_leaderboard.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename="leaderboard.png")

        await ctx.respond(file=file)


def setup(bot):
    bot.add_cog(JD4HLeaderboard(bot))
    LOGGER.info("JD4HLeaderboard cog loaded")
