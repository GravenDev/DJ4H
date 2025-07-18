from sqlalchemy import BigInteger, Column

from .connection import Base


class Guild(Base):
    __tablename__ = "guilds"

    guild_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    channel_id = Column(BigInteger, primary_key=True, nullable=False)
    delay_second = Column(BigInteger, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(
        BigInteger, primary_key=True, unique=True, nullable=False
    )
    guild_id = Column(BigInteger, nullable=False)
    author_id = Column(BigInteger, nullable=False)
    timestamp = Column(BigInteger, nullable=False)


class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, unique=True, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    score = Column(BigInteger, nullable=False)
