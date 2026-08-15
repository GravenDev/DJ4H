from sqlalchemy.sql.expression import select

from utils.database import Message, get_db


class MessagesDao:
    @staticmethod
    async def get_last_messages_by_guild(guild_id: int) -> Message | None:
        """Asynchronously get the last message for a specific guild."""
        async for session in get_db():
            message = await session.execute(
                select(Message)
                .filter(Message.guild_id == guild_id)
                .order_by(Message.timestamp.desc())
            )
            return message.scalars().first()
        return None

    @staticmethod
    async def add_message(message_id: int, guild_id: int, timestamp: int, author_id: int) -> None:
        """Asynchronously add a new message to the database."""
        async for session in get_db():
            message = Message(
                message_id=message_id,
                guild_id=guild_id,
                timestamp=timestamp,
                author_id=author_id,
            )
            session.add(message)
            await session.commit()

    @staticmethod
    async def delete_message(message_id: int):
        """Asynchronously delete a message by its ID."""
        async for session in get_db():
            message_query = await session.execute(
                select(Message).filter(Message.message_id == message_id)
            )
            message = message_query.scalars().first()
            if message:
                await session.delete(message)
                await session.commit()
