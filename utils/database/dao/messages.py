from sqlalchemy.orm import Session

from utils.database import Message, get_db


class MessagesDao:
    def __init__(self):
        self.db = next(get_db())

    def get_message(self, message_id: int):
        """Get a message by its ID."""
        return (
            self.db.query(Message)
            .filter(Message.message_id == message_id)
            .first()
        )

    def get_last_messages_by_guild(self, guild_id: int) -> Message | None:
        """Get all messages for a specific guild."""
        #
        return (
            self.db.query(Message)
            .filter(Message.guild_id == guild_id)
            .order_by(Message.timestamp.desc())
            .first()
        )

    def add_message(
        self, message_id: int, guild_id: int, timestamp: int, author_id: int
    ) -> None:
        """Add a new message to the database."""
        message = Message(
            message_id=message_id,
            guild_id=guild_id,
            timestamp=timestamp,
            author_id=author_id,
        )
        self.db.add(message)
        self.db.commit()

    def delete_message(self, message_id: int):
        """Delete a message by its ID."""
        message = self.get_message(message_id)
        if message:
            self.db.delete(message)
            self.db.commit()
