from io import BytesIO
import datetime
import asyncio

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
    ServerStatGenerator,
    OverallLeaderboardGenerator,
)
from utils.rngdle import RNGdle as RNGdleAPI
from utils.rngdle import get_score_tier


class LeaderboardPaginator(discord.ui.View):
    def __init__(
        self,
        users_data,
        generator,
        caller_index=None,
        current_page=0,
        per_page=10,
        is_ephemeral=False,
    ):
        super().__init__(timeout=180)
        self.users_data = users_data
        self.generator = generator
        self.caller_index = caller_index
        self.per_page = per_page
        self.is_ephemeral = is_ephemeral

        self.max_pages = max(1, (len(self.users_data) + self.per_page - 1) // self.per_page)
        self.current_page = max(0, min(current_page, self.max_pages - 1))

        self.prev_btn = discord.ui.Button(label="◀ Précédent", style=discord.ButtonStyle.primary)
        self.prev_btn.callback = self.prev_callback
        self.add_item(self.prev_btn)

        self.page_btn = discord.ui.Button(style=discord.ButtonStyle.success, disabled=True)
        self.add_item(self.page_btn)

        self.next_btn = discord.ui.Button(label="Suivant ▶", style=discord.ButtonStyle.primary)
        self.next_btn.callback = self.next_callback
        self.add_item(self.next_btn)

        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = self.current_page == 0
        self.next_btn.disabled = self.current_page + 1 >= self.max_pages
        self.page_btn.label = f"Page {self.current_page + 1} / {self.max_pages}"

    async def get_page_content(self) -> discord.File:
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        slice_data = self.users_data[start_idx:end_idx]

        caller_info = None
        if self.caller_index is not None and not (start_idx <= self.caller_index < end_idx):
            caller_info = {
                "rank": self.caller_index + 1,
                "data": self.users_data[self.caller_index],
            }

        img = await self.generator.generate_leaderboard(
            slice_data, start_rank=start_idx + 1, caller_info=caller_info
        )

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return discord.File(fp=buffer, filename=f"leaderboard_all_p{self.current_page}.png")

    async def prev_callback(self, interaction: discord.Interaction):
        await self._handle_pagination(interaction, self.current_page - 1)

    async def next_callback(self, interaction: discord.Interaction):
        await self._handle_pagination(interaction, self.current_page + 1)

    async def _handle_pagination(self, interaction: discord.Interaction, target_page: int):
        self.current_page = target_page

        if self.is_ephemeral:
            self.update_buttons()
            file = await self.get_page_content()
            await interaction.response.edit_message(file=file, view=self)
        else:
            new_view = LeaderboardPaginator(
                self.users_data,
                self.generator,
                caller_index=self.caller_index,
                current_page=self.current_page,
                per_page=self.per_page,
                is_ephemeral=True,
            )
            file = await new_view.get_page_content()
            await interaction.response.send_message(file=file, view=new_view, ephemeral=True)


class RNGdle(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.leaderboard_generator = LeaderboardGenerator()
        self.profile_generator = ProfileGenerator()
        self.server_stat_generator = ServerStatGenerator()
        self.overall_leaderboard_generator = OverallLeaderboardGenerator()
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

    @rng_group.command(name="profile", description="Show a RNGdle user profile.")
    async def profile(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Option(
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

        if not user:
            db_user = next((u for u in registered_users if u.user_id == ctx.author.id), None)
            if db_user:
                rngdle_username = db_user.rng_username
                target_id = ctx.author.id
                member = ctx.author
        elif user.startswith("<@") and user.endswith(">"):
            target_id = int(user.strip("<@!>"))
            db_user = next((u for u in registered_users if u.user_id == target_id), None)
            if db_user:
                rngdle_username = db_user.rng_username
                member = ctx.guild.get_member(target_id) or await get_or_fetch_user(
                    self.bot, target_id
                )
        else:
            rngdle_username = user
            db_user = next(
                (u for u in registered_users if u.rng_username.lower() == user.lower()),
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
        highest_score = -1
        lowest_score = float("inf")
        total_score_sum = 0
        lucky_number = 0
        unlucky_number = 0
        max_badges = 0
        highest_date = None
        lowest_date = None

        rarity_counts = {
            "MYTHIC": 0,
            "ANOMALY": 0,
            "EPIC": 0,
            "RARE": 0,
            "UNCOMMON": 0,
            "COMMON": 0,
            "TRASH": 0,
        }

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

            if score < lowest_score:
                lowest_score = score
                lowest_date = rolled_date
                unlucky_number = num

            if badges > max_badges:
                max_badges = badges

            tier = get_score_tier(score).name
            if tier in rarity_counts:
                rarity_counts[tier] += 1

        avg_score = int(total_score_sum / total_rolls) if total_rolls > 0 else 0

        rank = await RNGdleDao.get_server_rank_by_total(target_id, ctx.guild.id)
        total_players = len(registered_users) if registered_users else 0

        stats_dict = {
            "total_rolls": total_rolls,
            "total_score_sum": total_score_sum,
            "avg_score": avg_score,
            "highest_score": highest_score,
            "highest_date": (highest_date.strftime("%d %b %Y") if highest_date else "N/A"),
            "lucky_seed": lucky_number,
            "lowest_score": lowest_score if lowest_score != float("inf") else 0,
            "lowest_date": (lowest_date.strftime("%d %b %Y") if lowest_date else "N/A"),
            "unlucky_seed": unlucky_number,
            "max_badges": max_badges,
            "server_rank": rank,
            "total_players": total_players,
            "rarities": rarity_counts,
        }

        img = await self.profile_generator.generate_profile(member, rngdle_username, stats_dict)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename=f"profile_{rngdle_username}.png")

        await ctx.respond(file=file)

    @rng_group.command(name="server-stats", description="Show RNGdle server stats.")
    async def server_stats(self, ctx: discord.ApplicationContext) -> None:
        """Show RNGDLE server stats."""
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        registered_users = await RNGdleDao.get_registered_users(ctx.guild.id)
        if not registered_users:
            await ctx.respond("Personne n'est enregistré sur ce serveur.")
            return

        user_map = {u.user_id: u.rng_username for u in registered_users}

        await rngdle_fetch_with_cooldown()
        rolls = await RNGdleDao.get_guild_rolls(ctx.guild.id)

        if not rolls:
            await ctx.respond("Aucun tirage trouvé pour ce serveur.")
            return

        total_rolls = len(rolls)
        overall_score = 0
        best_roll = {"score": -1, "user": "", "number": 0, "user_id": None}
        worst_roll = {"score": float("inf"), "user": "", "number": 0, "user_id": None}

        rarity_counts = {
            "TRASH": 0,
            "COMMON": 0,
            "UNCOMMON": 0,
            "RARE": 0,
            "EPIC": 0,
            "ANOMALY": 0,
            "MYTHIC": 0,
        }

        user_rarity_counts = {}

        for roll in rolls:
            score = roll.score
            number = roll.number
            user_id = roll.user_id
            username = user_map.get(user_id, "Unknown")

            overall_score += score

            if score > best_roll["score"]:
                best_roll = {"score": score, "user": username, "number": number, "user_id": user_id}

            if score < worst_roll["score"]:
                worst_roll = {
                    "score": score,
                    "user": username,
                    "number": number,
                    "user_id": user_id,
                }

            tier = get_score_tier(score).name
            if tier in rarity_counts:
                rarity_counts[tier] += 1

            if user_id:
                if user_id not in user_rarity_counts:
                    user_rarity_counts[user_id] = {
                        "TRASH": 0,
                        "COMMON": 0,
                        "UNCOMMON": 0,
                        "RARE": 0,
                        "EPIC": 0,
                        "ANOMALY": 0,
                        "MYTHIC": 0,
                    }
                if tier in user_rarity_counts[user_id]:
                    user_rarity_counts[user_id][tier] += 1

        tiers_list = ["TRASH", "COMMON", "UNCOMMON", "RARE", "EPIC", "ANOMALY", "MYTHIC"]
        tier_kings = {t: [] for t in tiers_list}

        for tier in tiers_list:
            tier_users = [
                (uid, counts[tier])
                for uid, counts in user_rarity_counts.items()
                if counts[tier] > 0
            ]
            tier_users.sort(key=lambda x: x[1], reverse=True)
            tier_kings[tier] = tier_users[:3]

        avg_score = int(overall_score / total_rolls) if total_rolls > 0 else 0

        best_member = None
        if best_roll.get("user_id"):
            best_member = await get_or_fetch_user(self.bot, int(best_roll["user_id"]))
        best_roll["member"] = best_member

        worst_member = None
        if worst_roll.get("user_id"):
            worst_member = await get_or_fetch_user(self.bot, int(worst_roll["user_id"]))
        worst_roll["member"] = worst_member

        tier_members = {t: [] for t in tiers_list}
        for t, kings in tier_kings.items():
            for uid, count in kings:
                member = await get_or_fetch_user(self.bot, int(uid))
                if member:
                    tier_members[t].append(member)

        stats_dict = {
            "total_rolls": total_rolls,
            "overall_score": overall_score,
            "avg_score": avg_score,
            "best_roll": best_roll,
            "worst_roll": worst_roll,
            "rarities": rarity_counts,
            "tier_members": tier_members,
        }

        img = await self.server_stat_generator.generate_server_stat(ctx.guild, stats_dict)

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        file = discord.File(fp=buffer, filename="server_stats.png")

        await ctx.respond(file=file)

    @rng_group.command(
        name="leaderboard-all", description="Show the overall RNGdle leaderboard for the server."
    )
    async def leaderboard_all(
        self,
        ctx: discord.ApplicationContext,
        page: discord.Option(int, "Page number", min_value=1, default=1),
    ):
        await ctx.defer()
        if ctx.guild is None:
            await ctx.respond("This command can only be used in a server!")
            return

        leaderboard_rows = await RNGdleDao.get_overall_leaderboard(ctx.guild.id)

        if not leaderboard_rows:
            await ctx.respond("Aucun score enregistré sur ce serveur.", ephemeral=True)
            return

        registered_users = await RNGdleDao.get_registered_users(ctx.guild.id)
        reg_map = {u.user_id: u.rng_username for u in registered_users}

        users_data = []
        caller_index = None
        caller_id = ctx.author.id

        for i, row in enumerate(leaderboard_rows):
            user_id = row.user_id
            total_score = row.total_score

            if user_id == caller_id:
                caller_index = i

            member = ctx.guild.get_member(user_id) or await get_or_fetch_user(self.bot, user_id)
            rngdle_username = reg_map.get(user_id, "Unknown")

            users_data.append(
                {
                    "discord_user": member,
                    "rngdle_username": rngdle_username,
                    "total_score": total_score,
                }
            )

        view = LeaderboardPaginator(
            users_data=users_data,
            generator=self.overall_leaderboard_generator,
            caller_index=caller_index,
            current_page=page - 1,
            per_page=10,
            is_ephemeral=False,
        )

        file = await view.get_page_content()
        await ctx.respond(file=file, view=view)


def setup(bot):
    bot.add_cog(RNGdle(bot))
