from io import BytesIO

import discord
from discord import SlashCommandGroup
from discord.ext import commands

from config import LOGGER, MAGIC_COLOR
from utils import get_or_fetch_user
from utils.database.dao.guilds import GuildsDao
from utils.database.dao.users import UserDao
from utils.image_generator import JD4HLeaderboardUser, LeaderboardGenerator


def convert_time_to_seconds(time_str: str) -> int:
    match time_str.lower()[-1]:
        case "s":
            return int(time_str[:-1])
        case "m":
            return int(time_str[:-1]) * 60
        case "h":
            return int(time_str[:-1]) * 60 * 60
        case "d":
            return int(time_str[:-1]) * 24 * 60 * 60
        case _:
            raise ValueError("Invalid time format: Use 'm', 'h', or 'd'.")


class Game(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leaderboard_generator = LeaderboardGenerator()

    jd4h = SlashCommandGroup(
        name="jd4h", description="Commands for the 4h game"
    )

    jd4h_admin = SlashCommandGroup(
        name="jd4h-admin", description="JD4H admin commands"
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

    @jd4h_admin.command(description="Set game channel and delay")
    @discord.default_permissions()
    async def config(
        self,
        ctx,
        channel: discord.TextChannel,
        delay: discord.Option(
            str, description="Delay between messages. Ex: 30s, 5m, 4h, 3d"
        ),
    ) -> None:
        """Config game channel."""
        if not ctx.guild:
            await ctx.respond("This command can only be used in a server.")
            return

        try:
            converted_time = convert_time_to_seconds(delay)
        except ValueError as e:
            await ctx.respond(e)
            return

        if await GuildsDao.get_guild(ctx.guild.id) is None:
            await GuildsDao.add_guild(ctx.guild.id, channel.id, converted_time)
            await ctx.respond(
                f"Configuration setup: Channel: {channel.mention}, Delay: {delay}."
            )
            LOGGER.info(
                f"Guild {ctx.guild.id} configured with channel {channel.id} and delay {converted_time} seconds."
            )
            return

        await GuildsDao.update_guild(ctx.guild.id, channel.id, converted_time)
        await ctx.respond(
            f"Configuration updated: Channel: {channel.mention}, Delay: {delay}."
        )
        LOGGER.info(
            f"Guild {ctx.guild.id} updated with channel {channel.id} and delay {converted_time} seconds."
        )

    @jd4h_admin.command(description="Set a user's score")
    @discord.default_permissions()
    async def set(self, ctx, member: discord.Member, score: int):
        """Set a user's score."""
        if not ctx.guild:
            await ctx.respond("This command can only be used in a server.")
            return

        user = await UserDao.get_user(member.id, ctx.guild.id)

        if user is None:
            await UserDao.add_user(member.id, ctx.guild.id, score)
            await ctx.respond(f"Set user {member.mention}'s score to {score}.")
            LOGGER.info(
                f"User {member.id} added to guild {ctx.guild.id} with score {score}."
            )
        else:
            await UserDao.update_user(member.id, ctx.guild.id, score)
            await ctx.respond(
                f"User {member.mention}'s score updated to {score}."
            )
            LOGGER.info(
                f"User {member.id} updated in guild {ctx.guild.id} with score {score}."
            )

    @jd4h_admin.command(description="Unset a user's score")
    @discord.default_permissions()
    async def unset(self, ctx, member: discord.Member):
        """Unset a user's score."""
        if not ctx.guild:
            await ctx.respond("This command can only be used in a server.")
            return

        user = await UserDao.get_user(member.id, ctx.guild.id)

        if user is None:
            await ctx.respond(
                f"User {member.mention} does not have a score set."
            )
            return

        await UserDao.delete_user(member.id, ctx.guild.id)
        await ctx.respond(f"Unset user {member.mention}'s score.")
        LOGGER.info(f"User {member.id} removed from guild {ctx.guild.id}.")


def setup(bot: discord.Bot) -> None:
    """Load the Game cog."""
    bot.add_cog(Game(bot))
    LOGGER.info("Game cog loaded successfully.")
