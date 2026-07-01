import discord
from discord import SlashCommandGroup
from discord.ext import commands

from config import MAGIC_COLOR
from utils.database.dao.rngdle import RNGdleDao, RNGdleGuildConfigDao
from utils.tasks.rngdle_sync import sync_guild_users


class RNGdle(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    rng_group = SlashCommandGroup(name="rngdle", description="RNGDLE commands")

    @rng_group.command(description="Register/Update an RNGDLE user")
    @discord.default_permissions()
    async def register(
        self,
        ctx: discord.ApplicationContext,
        discord_user: discord.Member,
        username: str,
    ) -> None:
        """Register an RNGDLE user."""
        await ctx.defer()
        await RNGdleDao.register_user(discord_user.id, ctx.guild.id, username)
        message = discord.Embed(
            title="RNGDLE user",
            color=discord.Colour(MAGIC_COLOR),
            description=f"RNGDLE user `{username}` link to <@{discord_user.id}> successfully!",
        )
        await ctx.respond(embed=message)

    @rng_group.command(description="Show registered RNGDLE users")
    @discord.default_permissions()
    async def show(self, ctx: discord.ApplicationContext) -> None:
        """Show registered RNGDLE users."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        users = await RNGdleDao.get_registered_users(ctx.guild.id)
        if not users:
            await ctx.respond("No registered RNGDLE users found.")
            return

        all_users = "\n".join(
            f"<@{user.user_id}> -> {user.rng_username}" for user in users
        )
        message = discord.Embed(
            title="RNGDLE users",
            color=discord.Colour(MAGIC_COLOR),
            description=all_users,
        )
        await ctx.respond(embed=message)

    @rng_group.command(
        description="Set the channel for daily RNGDLE leaderboard"
    )
    @discord.default_permissions()
    async def setleaderboard(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
    ) -> None:
        """Set the channel where the daily leaderboard will be posted at midnight."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        await RNGdleGuildConfigDao.set_leaderboard_channel(
            ctx.guild.id, channel.id
        )
        message = discord.Embed(
            title="RNGdle Leaderboard Channel",
            color=discord.Colour(MAGIC_COLOR),
            description=f"Daily leaderboard will be posted in {channel.mention}.",
        )
        await ctx.respond(embed=message)

    @rng_group.command(description="Manually refresh RNGdle scores for all registered users")
    @discord.default_permissions()
    async def refresh(self, ctx: discord.ApplicationContext) -> None:
        """Manually refresh RNGdle scores without waiting for the hourly task."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        result = await sync_guild_users(ctx.guild.id)

        if result["users_count"] == 0:
            message = discord.Embed(
                title="RNGdle Refresh",
                color=discord.Colour(MAGIC_COLOR),
                description="No registered RNGDLE users found in this server.",
            )
        else:
            description = (
                f"Refreshed **{result['users_count']}** registered users:\n"
                f"✅ Stored: **{result['processed']}** rolls\n"
                f"❌ Failed: **{result['failed']}** rolls"
            )
            message = discord.Embed(
                title="RNGdle Refresh Complete",
                color=discord.Colour(MAGIC_COLOR),
                description=description,
            )

        await ctx.respond(embed=message)


def setup(bot):
    bot.add_cog(RNGdle(bot))
