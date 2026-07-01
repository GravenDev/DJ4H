import discord

from config import BOT_TOKEN, DEBUG_GUILD_ID, LOGGER, setup_logging
from utils.database import init_db
from utils.tasks.rngdle_daily_leaderboard import rngdle_daily_leaderboard_task
from utils.tasks.rngdle_sync import rngdle_sync_task


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
    await init_db()
    LOGGER.info("Database initialized successfully.")
    LOGGER.info("------")

    if not rngdle_sync_task.is_running():
        rngdle_sync_task.start()
        LOGGER.info("RNGdle sync task started")
    else:
        LOGGER.info("RNGdle sync task already running")

    if not rngdle_daily_leaderboard_task.is_running():
        rngdle_daily_leaderboard_task.start(bot)
        LOGGER.info("RNGdle daily leaderboard task started")
    else:
        LOGGER.info("RNGdle daily leaderboard task already running")


bot.load_extensions("commands", recursive=True)
bot.run(BOT_TOKEN)
