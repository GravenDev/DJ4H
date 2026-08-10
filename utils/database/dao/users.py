from sqlalchemy.sql.expression import select

from utils.database import User, get_db


class UserDao:
    @staticmethod
    async def get_user(user_id: int, guild_id: int) -> User | None:
        """Asynchronously add a new user to the database."""
        async for session in get_db():
            user = await session.execute(
                select(User).filter(User.user_id == user_id, User.guild_id == guild_id)
            )
            return user.scalars().first()
        return None

    @staticmethod
    async def update_user(user_id: int, guild_id: int, score: int) -> None:
        """Asynchronously update a user's information."""
        async for session in get_db():
            user_query = await session.execute(
                select(User).filter(User.user_id == user_id, User.guild_id == guild_id)
            )
            user = user_query.scalars().first()
            if user:
                user.score = score
                await session.commit()

    @staticmethod
    async def add_user(user_id: int, guild_id: int, score: int) -> None:
        """Asynchronously add a new user to the database."""
        async for session in get_db():
            user = User(user_id=user_id, guild_id=guild_id, score=score)
            session.add(user)
            await session.commit()

    @staticmethod
    async def get_leaderboard(guild_id: int, limit: int | None) -> list[type[User]] | None:
        """Asynchronously get the leaderboard for a specific guild."""
        async for session in get_db():
            query = await session.execute(
                select(User)
                .filter(User.guild_id == guild_id)
                .order_by(User.score.desc())
                .limit(limit)
            )
            return query.scalars().all()
        return None

    # TODO: Implement a method to get with sqlalchemy the rank of a user in a specific guild
    @staticmethod
    async def get_rank(user_id: int, guild_id: int) -> int:
        """Asynchronously get the rank of a user in a specific guild."""
        leaderboard = await UserDao.get_leaderboard(guild_id, limit=None)
        if leaderboard is None:
            return -1
        sorted_users = sorted(leaderboard, key=lambda x: x.score, reverse=True)
        for index, user in enumerate(sorted_users):
            if user.user_id == user_id:
                return index + 1
        return -1

    @staticmethod
    async def delete_user(user_id: int, guild_id: int):
        async for session in get_db():
            user_query = await session.execute(
                select(User).filter(User.user_id == user_id, User.guild_id == guild_id)
            )
            user = user_query.scalars().first()
            if user is None:
                return
            await session.delete(user)
            await session.commit()
