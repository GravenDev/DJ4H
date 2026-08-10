from io import BytesIO
import datetime

import discord
from discord import SlashCommandGroup
from discord.ext import commands

from config import MAGIC_COLOR
from utils import get_or_fetch_user
from utils.database.dao.rngdle import RNGdleDao, RNGdleGuildConfigDao
from utils.tasks.rngdle_sync import rngdle_fetch_with_cooldown, sync_guild_users
from utils.image_generator import (
    LeaderboardGenerator,
    RNGdleLeaderboardUser,
    ProfileGenerator,
)
from utils.rngdle import RNGdle as RNGdleAPI


class RNGdle(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leaderboard_generator = LeaderboardGenerator()
        self.profile_generator = ProfileGenerator()
        self.rngdle_api = RNGdleAPI()

    rng_group = SlashCommandGroup(name="rngdle", description="RNGDLE commands")

    rngdle_admin = SlashCommandGroup(name="rngdle-admin", description="RNGDLE admin commands")

    @rngdle_admin.command(description="Register/Update an RNGDLE user")
    @discord.default_permissions(administrator=True)
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

    @rngdle_admin.command(description="Show registered RNGDLE users")
    @discord.default_permissions(administrator=True)
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

        all_users = "\n".join(f"<@{user.user_id}> -> {user.rng_username}" for user in users)
        message = discord.Embed(
            title="RNGDLE users",
            color=discord.Colour(MAGIC_COLOR),
            description=all_users,
        )
        await ctx.respond(embed=message)

    @rngdle_admin.command(description="Set the channel for daily RNGDLE leaderboard")
    @discord.default_permissions(administrator=True)
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

        await RNGdleGuildConfigDao.set_leaderboard_channel(ctx.guild.id, channel.id)
        message = discord.Embed(
            title="RNGdle Leaderboard Channel",
            color=discord.Colour(MAGIC_COLOR),
            description=f"Daily leaderboard will be posted in {channel.mention}.",
        )
        await ctx.respond(embed=message)

    @rngdle_admin.command(description="Manually refresh RNGdle scores for all registered users")
    @discord.default_permissions(administrator=True)
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

    @rng_group.command(description="Show RNGDLE leaderboard")
    async def leaderboard(self, ctx: discord.ApplicationContext) -> None:
        """Show RNGDLE leaderboard."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        # Fetch rolls before accessing them
        await rngdle_fetch_with_cooldown()

        scores = await RNGdleDao.get_today_scores(ctx.guild.id)
        if not scores:
            await ctx.respond("No today scores found.")
            return

        users: list[RNGdleLeaderboardUser] = []
        for score_col in scores:
            user = await get_or_fetch_user(self.bot, score_col.user_id)
            if user is None:
                continue

            score = int(score_col.score)
            number = int(score_col.number)
            u = RNGdleLeaderboardUser.create_user_instance(user, score, number, len(users) + 1)
            users.append(u)

        generated = await self.leaderboard_generator.generate_leaderboard(users)
        buffer = BytesIO()
        generated.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename="leaderboard.png")

        await ctx.respond(file=file)

    @rng_group.command(name="profil", description="Show a RNGdle user profile.")
    async def profil(
        self,
        ctx: discord.ApplicationContext,
        target: discord.Option(
            str, "RNGdle username or @mention a Discord user", required=False
        ) = None,
    ) -> None:
        """Show RNGDLE profile stats."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        rngdle_username = None
        target_id = None
        member = None

        registered_users = await RNGdleDao.get_registered_users(ctx.guild.id)
        if not registered_users:
            await ctx.respond("Personne n'est enregistré sur ce serveur.", ephemeral=True)
            return

        if not target:
            db_user = next((u for u in registered_users if u.user_id == ctx.author.id), None)
            if db_user:
                rngdle_username = db_user.rng_username
                target_id = ctx.author.id
                member = ctx.author
        elif target.startswith("<@") and target.endswith(">"):
            target_id = int(target.strip("<@!>"))
            db_user = next((u for u in registered_users if u.user_id == target_id), None)
            if db_user:
                rngdle_username = db_user.rng_username
                member = ctx.guild.get_member(target_id) or await get_or_fetch_user(
                    self.bot, target_id
                )
        else:
            rngdle_username = target
            db_user = next(
                (u for u in registered_users if u.rng_username.lower() == target.lower()),
                None,
            )
            if db_user:
                target_id = db_user.user_id
                member = ctx.guild.get_member(target_id) or await get_or_fetch_user(
                    self.bot, target_id
                )

        if not rngdle_username or not target_id:
            await ctx.respond(
                "Utilisateur non trouvé ou compte non lié. Utilisez `/rngdle-admin register`.",
                ephemeral=True,
            )
            return

        rolls = await RNGdleDao.get_user_rolls(target_id, ctx.guild.id)

        if not rolls:
            await rngdle_fetch_with_cooldown()
            rolls = await RNGdleDao.get_user_rolls(target_id, ctx.guild.id)
            if not rolls:
                await ctx.respond(f"Aucun tirage trouvé pour `{rngdle_username}`!", ephemeral=True)
                return

        total_rolls = len(rolls)
        highest_score = 0
        total_score_sum = 0
        lucky_number = 0
        max_badges = 0
        highest_date = None

        for roll in rolls:
            score = roll.score
            num = roll.number
            badges = roll.badge_count

            rolled_date = datetime.datetime.fromtimestamp(roll.date / 1000.0)

            total_score_sum += score

            if score > highest_score:
                highest_score = score
                highest_date = rolled_date
                lucky_number = num

            if badges > max_badges:
                max_badges = badges

        avg_score = int(total_score_sum / total_rolls) if total_rolls > 0 else 0

        rank = await RNGdleDao.get_server_rank_by_total(target_id, ctx.guild.id)

        stats_dict = {
            "total_rolls": total_rolls,
            "total_score_sum": total_score_sum,
            "avg_score": avg_score,
            "highest_score": highest_score,
            "highest_date": (highest_date.strftime("%d %b %Y") if highest_date else "N/A"),
            "lucky_seed": lucky_number,
            "max_badges": max_badges,
            "server_rank": rank,
        }

        img = await self.profile_generator.generate_profile(member, rngdle_username, stats_dict)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename=f"profile_{rngdle_username}.png")

        await ctx.respond(file=file)


def setup(bot):
    bot.add_cog(RNGdle(bot))
