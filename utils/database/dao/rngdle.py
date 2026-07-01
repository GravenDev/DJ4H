from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy.sql.expression import select

from utils.database import RNGdle, RNGdleGuildConfig, RNGdleUser, get_db


def get_today_range():
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_next_day = start_of_day + timedelta(days=1)

    start_ts = int(start_of_day.timestamp()) * 1000
    end_ts = int(start_of_next_day.timestamp()) * 1000
    return start_ts, end_ts


def get_yesterday_range():
    now = datetime.now(timezone.utc)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_yesterday = start_of_today - timedelta(days=1)

    start_ts = int(start_of_yesterday.timestamp()) * 1000
    end_ts = int(start_of_today.timestamp()) * 1000
    return start_ts, end_ts


class RNGdleDao:
    @staticmethod
    async def register_user(user_id: int, guild_id: int, username: str) -> None:
        async for session in get_db():
            # Try to find an existing entry for this user in this guild
            existing = await session.execute(
                select(RNGdleUser).filter(
                    RNGdleUser.user_id == user_id,
                    RNGdleUser.guild_id == guild_id,
                )
            )
            existing_row = existing.scalars().first()

            if existing_row is not None:
                # Update the username if it changed
                if existing_row.rng_username != username:
                    existing_row.rng_username = username
                    session.add(existing_row)
                    await session.commit()
                # else: nothing to do
                return

            # No existing entry -> create one
            rngdle_user = RNGdleUser(
                user_id=user_id, guild_id=guild_id, rng_username=username
            )
            session.add(rngdle_user)
            await session.commit()
            return

    @staticmethod
    async def get_registered_users(
        guild_id: int,
    ) -> Sequence[RNGdleUser] | None:
        async for session in get_db():
            users = await session.execute(
                select(RNGdleUser).filter(RNGdleUser.guild_id == guild_id)
            )
            return users.scalars().all()
        return None

    @staticmethod
    async def get_all_registered_users() -> Sequence[RNGdleUser] | None:
        """Return all registered RNGdle users across guilds."""
        async for session in get_db():
            users = await session.execute(select(RNGdleUser))
            return users.scalars().all()
        return None

    @staticmethod
    async def upsert_rngdle(
        user_id: int,
        guild_id: int,
        date: int,
        score: int,
        number: int,
    ) -> bool:
        """
        INSERT a roll into RNGdle history if it does not already exist.
        Returns True if inserted, False if an identical roll already exists.
        We consider a roll identical if user_id + date + number match an existing row.
        """
        async for session in get_db():
            existing = await session.execute(
                select(RNGdle).filter(
                    RNGdle.user_id == user_id,
                    RNGdle.date == date,
                    RNGdle.number == number,
                )
            )
            existing_row = existing.scalars().first()
            if existing_row is not None:
                return False

            rng = RNGdle(
                user_id=user_id,
                guild_id=guild_id,
                date=date,
                score=score,
                number=number,
            )
            session.add(rng)
            await session.commit()
            return True

    @staticmethod
    async def get_today_scores(
        guild_id: int,
    ) -> Sequence[RNGdle] | None:
        # Match the stored int date format: YYYYMMDD
        start_ts, end_ts = get_today_range()

        async for session in get_db():
            query = (
                select(RNGdle)
                .filter(
                    RNGdle.guild_id == guild_id,
                    RNGdle.date >= start_ts,
                    RNGdle.date < end_ts,
                )
                .order_by(RNGdle.score.desc())
            )

            rows = await session.execute(query)
            return rows.scalars().all()

        return None

    @staticmethod
    async def get_scores_in_range(
        guild_id: int, start_ts: int, end_ts: int
    ) -> Sequence[RNGdle] | None:
        async for session in get_db():
            query = (
                select(RNGdle)
                .filter(
                    RNGdle.guild_id == guild_id,
                    RNGdle.date >= start_ts,
                    RNGdle.date < end_ts,
                )
                .order_by(RNGdle.score.desc())
            )

            rows = await session.execute(query)
            return rows.scalars().all()

        return None


class RNGdleGuildConfigDao:

    @staticmethod
    async def set_leaderboard_channel(guild_id: int, channel_id: int | None) -> None:
        async for session in get_db():
            existing = await session.execute(
                select(RNGdleGuildConfig).filter(RNGdleGuildConfig.guild_id == guild_id)
            )
            config = existing.scalars().first()

            if config is not None:
                config.leaderboard_channel_id = channel_id
                session.add(config)
            else:
                config = RNGdleGuildConfig(
                    guild_id=guild_id, leaderboard_channel_id=channel_id
                )
                session.add(config)

            await session.commit()

    @staticmethod
    async def get_leaderboard_channel(guild_id: int) -> int | None:
        async for session in get_db():
            existing = await session.execute(
                select(RNGdleGuildConfig).filter(RNGdleGuildConfig.guild_id == guild_id)
            )
            config = existing.scalars().first()
            if config is not None:
                return config.leaderboard_channel_id
            return None

    @staticmethod
    async def get_all_configured_guilds() -> Sequence[RNGdleGuildConfig]:
        async for session in get_db():
            result = await session.execute(select(RNGdleGuildConfig))
            return result.scalars().all()
        return []
