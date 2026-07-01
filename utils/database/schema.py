from sqlalchemy import BigInteger, Column, Integer, String, Text

from .connection import Base


class Guild(Base):
    __tablename__ = "guilds"

    guild_id = Column(BigInteger, primary_key=True, nullable=False)
    channel_id = Column(BigInteger, primary_key=True, nullable=False)
    delay_second = Column(BigInteger, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String(20), primary_key=True, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    author_id = Column(BigInteger, nullable=False)
    timestamp = Column(BigInteger, nullable=False)


class User(Base):
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    score = Column(BigInteger, nullable=False)


class RNGdle(Base):
    __tablename__ = "rngdle"

    # SQLite autoincrement works reliably with INTEGER PRIMARY KEY
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    date = Column(BigInteger, nullable=False)
    score = Column(BigInteger, nullable=False)
    number = Column(BigInteger, nullable=False)


class RNGdleUser(Base):
    __tablename__ = "rngdleuser"

    user_id = Column(BigInteger, primary_key=True, nullable=False)
    guild_id = Column(BigInteger, nullable=False)
    rng_username = Column(Text, nullable=False)


class RNGdleGuildConfig(Base):
    __tablename__ = "rngdleguildconfig"

    guild_id = Column(BigInteger, primary_key=True, nullable=False)
    leaderboard_channel_id = Column(BigInteger, nullable=True)
