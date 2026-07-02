import pathlib

import discord
from discord import SlashCommandGroup
from discord.ext import commands

from config import LOGGER


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin = SlashCommandGroup(
        name="admin", description="General bot admin commands"
    )

    @admin.command(description="Dump the bot's log")
    @discord.default_permissions()
    async def dump_log(self, ctx):
        """Dump the bot's log."""
        if not ctx.guild:
            await ctx.respond("This command can only be used in a server.")
            return

        current_path = pathlib.Path(__file__).parent.resolve()
        log_file = pathlib.Path(f"{current_path}/../../logs/bot.log")
        if not log_file.exists():
            await ctx.respond("Log file does not exist.")
            return
        with open(log_file, "rb") as f:
            await ctx.respond(
                "Here is the log file:",
                file=discord.File(f, "bot.log"),
                ephemeral=True,
            )


def setup(bot):
    bot.add_cog(Admin(bot))
    LOGGER.info("Admin cog loaded.")
