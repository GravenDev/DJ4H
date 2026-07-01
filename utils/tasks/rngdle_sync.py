import traceback

from discord.ext import tasks

from config import LOGGER, RNGDLE_SYNC_INTERVAL
from utils.database.dao.rngdle import RNGdleDao
from utils.rngdle import RNGdle as RNGdleClient


async def _process_user(rng_client: RNGdleClient, db_user, log_mode: str = "background") -> dict:
    """
    Fetch rolls for one user and store them into DB history.

    Args:
        rng_client: RNGdle API client
        db_user: Database user object
        log_mode: "background" for hourly task, "manual" for explicit refresh command

    Returns:
        dict with keys: processed (int), failed (int)
    """
    processed = 0
    failed = 0

    try:
        rolls = rng_client.get_user_rolls(db_user.rng_username)
        if not rolls:
            LOGGER.debug(f"No rolls found for {db_user.rng_username}")
            return {"processed": 0, "failed": 0}

        for roll in rolls:
            try:
                inserted = await RNGdleDao.upsert_rngdle(
                    user_id=db_user.user_id,
                    guild_id=db_user.guild_id,
                    date=roll.date,
                    score=roll.score,
                    number=roll.number,
                )
                if inserted:
                    processed += 1
                    if log_mode == "background":
                        LOGGER.info(
                            f"Stored/updated rngdle for {db_user.rng_username} (user {db_user.user_id}), score {roll.score} at {roll.date} number: {roll.number}"
                        )
            except Exception:
                failed += 1
                LOGGER.error(
                    f"Failed upserting roll for {db_user.rng_username}: {traceback.format_exc()}"
                )
    except Exception:
        failed += 1
        LOGGER.error(
            f"Failed fetching rolls for {db_user.rng_username}: {traceback.format_exc()}"
        )

    return {"processed": processed, "failed": failed}


@tasks.loop(seconds=RNGDLE_SYNC_INTERVAL)
async def rngdle_sync_task() -> None:
    """Every hour fetch all registered users and sync their rolls."""
    rng_client = RNGdleClient()
    LOGGER.info("RNGdle sync: starting pass to fetch registered users")
    users = await RNGdleDao.get_all_registered_users()
    if not users:
        LOGGER.info("RNGdle sync: no registered users found")
    else:
        for user in users:
            await _process_user(rng_client, user, log_mode="background")

    LOGGER.info(f"RNGdle sync: pass complete")


@rngdle_sync_task.error
async def on_rngdle_sync_error(exc: Exception) -> None:
    LOGGER.error(f"RNGdle sync task error: {exc}")


async def sync_guild_users(guild_id: int) -> dict:
    """
    Manually sync all RNGdle users for a specific guild.
    Returns a dict with counts of processed and failed users.
    """
    rng_client = RNGdleClient()
    users = await RNGdleDao.get_registered_users(guild_id)

    if not users:
        return {"processed": 0, "failed": 0, "users_count": 0}

    total_processed = 0
    total_failed = 0

    for user in users:
        stats = await _process_user(rng_client, user, log_mode="manual")
        total_processed += stats["processed"]
        total_failed += stats["failed"]

    return {"processed": total_processed, "failed": total_failed, "users_count": len(users)}
