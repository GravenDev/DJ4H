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

        guild_dao = GuildsDao()
        guild = guild_dao.get_guild(ctx.guild.id)
        if guild is None:
            return

        if guild.channel_id != ctx.channel.id:
            return

        message_dao = MessagesDao()
        user_dao = UserDao()

        current_time = int(time.time())
        last_message = message_dao.get_last_messages_by_guild(guild.guild_id)

        if last_message is None:
            message_dao.add_message(
                ctx.id, guild.guild_id, current_time, ctx.author.id
            )
            LOGGER.info(
                f"Added message {ctx.id} to {ctx.guild.name} at {current_time}"
            )
            return
        if last_message.author_id == ctx.author.id:
            # Last message was sent by the same user
            LOGGER.debug(
                f"Last message {last_message.message_id} was sent by the same user in {ctx.guild.name}"
            )
            return

        # User has won a point
        if last_message.timestamp + guild.delay_second <= current_time:
            last_message_author = user_dao.get_user(
                last_message.author_id, guild.guild_id
            )

            if last_message_author is None:
                # First point for the user
                user_dao.add_user(last_message.author_id, guild.guild_id, 1)
                LOGGER.info(
                    f"Added user {last_message.author_id} to {ctx.guild.name} with score 1"
                )
            else:
                # Update the user's score
                new_score = last_message_author.score + 1
                user_dao.update_user(
                    last_message.author_id,
                    guild.guild_id,
                    new_score,
                )
                LOGGER.info(
                    f"Updated user {last_message.author_id} in {ctx.guild.name} to score {new_score}"
                )

        message_dao.add_message(
            ctx.id, guild.guild_id, current_time, ctx.author.id
        )
        LOGGER.debug(
            f"Added message {ctx.id} to {ctx.guild.name} at {current_time}"
        )
        message_dao.delete_message(last_message.message_id)
        LOGGER.debug(
            f"Deleted last_message {last_message.message_id} to {ctx.guild.name}"
        )


def setup(bot):
    """Setup the event handler."""
    bot.add_cog(EventHandler(bot))
    LOGGER.info("Event handler loaded")
