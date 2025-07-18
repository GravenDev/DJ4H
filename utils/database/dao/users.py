from utils.database import User, get_db


class UserDao:
    def __init__(self):
        self.db = next(get_db())

    def get_user(self, user_id: int, guild_id: int) -> User | None:
        """Retrieve a user by their ID."""
        return (
            self.db.query(User)
            .filter(User.user_id == user_id, User.guild_id == guild_id)
            .first()
        )

    def update_user(self, user_id: int, guild_id: int, score: int) -> None:
        """Update a user's information."""
        user = self.get_user(user_id, guild_id)
        if user:
            user.score = score
            self.db.commit()

    def add_user(self, user_id: int, guild_id: int, score: int) -> None:
        """Add a new user to the database."""
        user = User(user_id=user_id, guild_id=guild_id, score=score)
        self.db.add(user)
        self.db.commit()

    def get_leaderboard(self, guild_id: int, limit: int) -> list[type[User]]:
        """Get the leaderboard for a specific guild."""
        return (
            self.db.query(User)
            .filter(User.guild_id == guild_id)
            .order_by(User.score.desc())
            .limit(limit)
            .all()
        )

    # TODO: Implement a method to get with sqlalchemy the rank of a user in a specific guild
    def get_rank(self, user_id: int, guild_id: int) -> int:
        """Get the rank of a user in a specific guild."""
        users = self.get_leaderboard(guild_id, limit=None)
        sorted_users = sorted(users, key=lambda x: x.score, reverse=True)
        for index, user in enumerate(sorted_users):
            if user.user_id == user_id:
                return index + 1
        return -1
