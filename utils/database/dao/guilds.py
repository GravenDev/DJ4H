from sqlalchemy.sql.expression import select

from utils.database import Guild, get_db


class GuildsDao:
    @staticmethod
    async def add_guild(guild_id: int, channel_id: int, delay_second: int) -> None:
        """Asynchronously add a new guild to the database."""
        async for session in get_db():
            guild = Guild(
                guild_id=guild_id,
                channel_id=channel_id,
                delay_second=delay_second,
            )
            session.add(guild)
            await session.commit()

    @staticmethod
    async def get_guild(guild_id: int) -> Guild | None:
        """Asynchronously retrieve a guild by its ID."""
        async for session in get_db():
            guild = await session.execute(select(Guild).filter(Guild.guild_id == guild_id))
            return guild.scalars().first()
        return None

    @staticmethod
    async def update_guild(guild_id: int, channel_id: int, delay_second: int) -> None:
        """Asynchronously update an existing guild's channel and delay."""
        async for session in get_db():
            guild_query = await session.execute(select(Guild).filter(Guild.guild_id == guild_id))
            guild = guild_query.scalars().first()
            if guild:
                guild.channel_id = channel_id
                guild.delay_second = delay_second
                await session.commit()
