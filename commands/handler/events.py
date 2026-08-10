import time

import discord
from discord.ext import commands

from config import LOGGER
from utils.database.dao.guilds import GuildsDao
from utils.database.dao.messages import MessagesDao
from utils.database.dao.users import UserDao


class EventHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Message):
        """Handle incoming messages."""
        if ctx.author.bot:
            return

        guild = await GuildsDao.get_guild(ctx.guild.id)

        if guild is None:
            return

        if guild.channel_id != ctx.channel.id:
            return

        current_time = int(time.time())
        last_message = await MessagesDao.get_last_messages_by_guild(guild.guild_id)

        if last_message is None:
            LOGGER.info(f"{ctx.id} {guild.guild_id} {current_time} {ctx.author.id}")
            await MessagesDao.add_message(ctx.id, guild.guild_id, current_time, ctx.author.id)
            LOGGER.info(f"Added message {ctx.id} to {ctx.guild.name} at {current_time}")
            return
        if last_message.author_id == ctx.author.id:
            # Last message was sent by the same user
            LOGGER.debug(
                f"Last message {last_message.message_id} was sent by the same user in {ctx.guild.name}"
            )
            return

        # User has won a point
        if last_message.timestamp + guild.delay_second <= current_time:
            last_message_author = await UserDao.get_user(last_message.author_id, guild.guild_id)

            if last_message_author is None:
                # First point for the user
                await UserDao.add_user(last_message.author_id, guild.guild_id, 1)
                LOGGER.info(f"Added user {last_message.author_id} to {ctx.guild.name} with score 1")
            else:
                # Update the user's score
                new_score = last_message_author.score + 1
                await UserDao.update_user(
                    last_message.author_id,
                    guild.guild_id,
                    new_score,
                )
                LOGGER.info(
                    f"Updated user {last_message.author_id} in {ctx.guild.name} to score {new_score}"
                )
            member = await ctx.guild.fetch_member(last_message.author_id)
            embed = discord.Embed(
                title="Point Awarded!",
                description=(
                    f"{member.mention} "
                    f"has been awarded a point! They now have {last_message_author.score + 1 if last_message_author else 1} points."
                ),
                color=0x00FF00,
            )
            await ctx.channel.send(embed=embed)

        await MessagesDao.add_message(ctx.id, guild.guild_id, current_time, ctx.author.id)
        LOGGER.debug(f"Added message {ctx.id} to {ctx.guild.name} at {current_time}")
        await MessagesDao.delete_message(last_message.message_id)
        LOGGER.debug(f"Deleted last_message {last_message.message_id} to {ctx.guild.name}")


def setup(bot):
    """Set up the event handler."""
    bot.add_cog(EventHandler(bot))
    LOGGER.info("Event handler loaded")
