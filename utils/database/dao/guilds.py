from utils.database import Guild, get_db


class GuildsDao:
    def __init__(self):
        self.db = next(get_db())

    def add_guild(
        self, guild_id: int, channel_id: int, delay_second: int
    ) -> None:
        """Add a new guild to the database."""
        guild = Guild(
            guild_id=guild_id, channel_id=channel_id, delay_second=delay_second
        )

        self.db.add(guild)
        self.db.commit()

    def get_guild(self, guild_id: int) -> Guild | None:
        """Retrieve a guild by its ID."""
        return self.db.query(Guild).filter(Guild.guild_id == guild_id).first()

    def update_guild(
        self, guild_id: int, channel_id: int, delay_second: int
    ) -> None:
        """Update an existing guild's channel and delay."""
        guild = self.get_guild(guild_id)
        guild.channel_id = channel_id
        guild.delay_second = delay_second
        self.db.commit()
