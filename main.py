import discord

from config import BOT_TOKEN, DEBUG_GUILD_ID, LOGGER, setup_logging
from utils.database.connection import Base, engine

setup_logging()

bot = discord.AutoShardedBot(
    intents=discord.Intents.default(),
    help_command=None,  # Disable the default help command
    debug_guilds=[DEBUG_GUILD_ID] if DEBUG_GUILD_ID else None,
)


@bot.event
async def on_ready():
    LOGGER.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    LOGGER.info("------")


Base.metadata.create_all(engine)
bot.load_extensions("commands", recursive=True)
bot.run(BOT_TOKEN)
