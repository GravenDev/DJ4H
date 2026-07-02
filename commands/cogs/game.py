from io import BytesIO

import discord
from discord import SlashCommandGroup
from discord.ext import commands

from config import LOGGER, MAGIC_COLOR
from utils import get_or_fetch_user
from utils.database.dao.users import UserDao
from utils.image_generator import JD4HLeaderboardUser, LeaderboardGenerator


class Game(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leaderboard_generator = LeaderboardGenerator()

    jd4h = SlashCommandGroup(
        name="jd4h", description="Commands for the 4h game"
    )

    @jd4h.command()
    async def score(self, ctx, member: discord.Member | None = None) -> None:
        """Check your score."""
        if not ctx.guild:
            return
        user_id = member.id if member else ctx.author.id
        user = await UserDao.get_user(user_id, ctx.guild.id)

        if user is None:
            await ctx.respond(f"<@{user_id}>'s have no score in this guild.")
            return

        embed = discord.Embed(
            title="🎪 Le jeu des 4h",
            description=f"Le score de <@{user_id}> est **{user.score}**",
            colour=discord.Colour(MAGIC_COLOR),
        )

        await ctx.respond(embed=embed)

    @jd4h.command(description="Show JD4H leaderboard")
    async def leaderboard(self, ctx: discord.ApplicationContext) -> None:
        """Show JD4H leaderboard."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        leaderboard = await UserDao.get_leaderboard(ctx.guild.id, 10)

        if not leaderboard:
            await ctx.respond("No users found in the leaderboard.")
            return

        users: list[JD4HLeaderboardUser] = []
        for user in leaderboard:
            user_data = await get_or_fetch_user(self.bot, user.user_id)
            if user_data is None:
                continue
            u = JD4HLeaderboardUser()
            u.user = user_data
            u.score = str(user.score)
            u.rank = await UserDao.get_rank(user.user_id, user.guild_id)
            users.append(u)

        generated = await self.leaderboard_generator.generate_leaderboard(users)
        buffer = BytesIO()
        generated.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename="leaderboard.png")

        await ctx.respond(file=file)


def setup(bot: discord.Bot) -> None:
    """Load the Game cog."""
    bot.add_cog(Game(bot))
    LOGGER.info("Game cog loaded successfully.")
