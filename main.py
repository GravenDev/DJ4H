import discord

from config import BOT_TOKEN, DEBUG_GUILD_ID, LOGGER, setup_logging
from utils.database import init_db
from utils.tasks.rngdle_daily_leaderboard import schedule_rngdle_daily_leaderboard
from utils.tasks.rngdle_sync import schedule_rngdle_sync


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
    # Schedule the hourly RNGdle sync task
    schedule_rngdle_sync(bot)
    # Schedule the daily RNGdle leaderboard task (midnight UTC)
    schedule_rngdle_daily_leaderboard(bot)


bot.load_extensions("commands", recursive=True)
bot.run(BOT_TOKEN)
