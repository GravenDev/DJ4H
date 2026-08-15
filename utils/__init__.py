import discord


async def get_or_fetch_user(bot: discord.Bot, user_id: int) -> discord.User | None:
    """Get a user from the bot's cache or fetch from Discord API."""
    user = bot.get_user(user_id)
    if user is None:
        try:
            user = await bot.fetch_user(user_id)
        except discord.NotFound:
            return None
    return user
