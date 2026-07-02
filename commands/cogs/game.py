import discord
from discord import SlashCommandGroup
from discord.ext import commands

from config import LOGGER, MAGIC_COLOR


class Game(commands.Cog):
    """Game commands for the bot."""

    def __init__(self, bot: discord.Bot):
        self.bot = bot

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


def setup(bot: discord.Bot) -> None:
    """Load the Game cog."""
    bot.add_cog(Game(bot))
    LOGGER.info("Game cog loaded successfully.")
