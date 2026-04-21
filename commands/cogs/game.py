from io import BytesIO

import discord
from discord.commands import slash_command
from discord.ext import commands

from config import LOGGER
from utils.database import User
from utils.database.dao.users import UserDao
from utils.image_generator import LeaderboardGenerator, LeaderboardUser


def get_medal_emoji(position: int) -> str:
    """Get the medal emoji based on the user's position."""
    icons: dict[int, str] = {
        1: "🥇",
        2: "🥈",
        3: "🥉"
    }

    return icons.get(position, f"#{position}")


class Game(commands.Cog):
    """Game commands for the bot."""

    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leaderboard_generator = LeaderboardGenerator()

    async def get_user_data(self, users: list[type[User]]):
        users_response = []
        for user in users:
            user_data = await self.bot.get_or_fetch_user(user.user_id)
            if user_data:
                user_ = LeaderboardUser()
                user_.user = user_data
                user_.score = user.score
                user_.rank = await UserDao.get_rank(user.user_id, user.guild_id)
                users_response.append(user_)
        return users_response

    @slash_command()
    async def leaderboard(self, ctx) -> None:
        """Show game leaderboard."""
        await ctx.defer()  # Defer the response to allow for longer processing time
        if not ctx.guild:
            return

        leaderboard = await UserDao.get_leaderboard(ctx.guild.id, 10)

        if not leaderboard:
            await ctx.respond("No users found in the leaderboard.")
            return
        leaderboard_user = await self.get_user_data(leaderboard)
        generated_leaderboard = (
            await self.leaderboard_generator.generate_leaderboard(
                leaderboard_user
            )
        )
        buffer = BytesIO()
        generated_leaderboard.save(buffer, format="PNG")
        buffer.seek(0)  # Move to the beginning of the BytesIO buffer
        file = discord.File(fp=buffer, filename="leaderboard.png")

        await ctx.respond(file=file)

    @slash_command()
    async def score(self, ctx, member:discord.Member=None) -> None:
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
            colour=discord.Colour(5220337),
        )

        await ctx.respond(embed=embed)


def setup(bot: discord.Bot) -> None:
    """Load the Game cog."""
    bot.add_cog(Game(bot))
    LOGGER.info("Game cog loaded successfully.")
