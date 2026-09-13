import asyncio
import datetime
import traceback

import aiohttp
from discord.ext import tasks

from config import LOGGER, RNGDLE_SYNC_INTERVAL, RNGDLE_TABLE_SYNC_INTERVAL
from utils.database.dao.rngdle import RNGdleDao
from utils.database.schema import RNGdleUser
from utils.rngdle import (
    RNGdle as RNGdleClient,
    update_compressed_score_to_percent_table,
)

# Register when the last sync was done, used for fetching cooldown
_last_rngdle_sync = datetime.datetime.fromtimestamp(0)


async def _process_user(
    rng_client: RNGdleClient,
    db_user: RNGdleUser,
    log_mode: str = "background",
    *,
    force_full_fetch: bool = False,
) -> dict[str, int]:
    """
    Fetch rolls for one user and store them into DB history.

    Args:
        rng_client: RNGdle API client
        db_user: Database user object
        log_mode: "background" for hourly task, "manual" for explicit refresh command

    Returns:
        dict with keys: processed (int), failed (int)
    """
    global _last_rngdle_sync

    stats = {"fetched": 0, "processed": 0, "failed": 0}

    _last_rngdle_sync = datetime.datetime.now()

    most_recent_roll = await RNGdleDao.get_user_most_recent_roll(
        int(db_user.user_id), int(db_user.guild_id)
    )
    most_recent_timestamp = int(most_recent_roll.date) if most_recent_roll else 0
    if force_full_fetch:
        # Set the threshold timestamp to 0 to force a fetch of all passed rolls
        most_recent_timestamp = 0

    utc = datetime.UTC
    last_reset = datetime.datetime.now(utc).date()
    last_roll_date = datetime.datetime.fromtimestamp(most_recent_timestamp // 1000, utc).date()

    if last_roll_date >= last_reset:
        # No need to fetch any rolls
        return stats

    _last_rngdle_sync = datetime.datetime.now()

    try:
        async with aiohttp.ClientSession() as session:
            rolls = await rng_client.fetch_user_rolls(
                str(db_user.rng_username), session, threshold_timestamp=most_recent_timestamp
            )
        if not rolls:
            LOGGER.debug(f"No rolls found for {db_user.rng_username}")
            return stats

        stats["fetched"] += len(rolls)
        for roll in rolls:
            try:
                already_exists = await RNGdleDao.roll_exists(
                    user_id=int(db_user.user_id), date=roll.date, number=roll.number
                )
                if already_exists:
                    # Update with new score if necessary
                    await RNGdleDao.update_roll(
                        int(db_user.user_id), roll.date, roll.score, roll.number, roll.badges
                    )
                else:
                    # Insert the new roll
                    inserted = await RNGdleDao.upsert_rngdle(
                        user_id=int(db_user.user_id),
                        guild_id=int(db_user.guild_id),
                        date=roll.date,
                        score=roll.score,
                        number=roll.number,
                        badges=roll.badges,
                    )
                    if inserted:
                        stats["processed"] += 1
                        if log_mode == "background":
                            LOGGER.info(
                                f"Stored/updated rngdle for {db_user.rng_username} (user {db_user.user_id}), score {roll.score} at {roll.date} number: {roll.number} badges: {roll.badges}"
                            )

            except Exception:
                stats["failed"] += 1
                LOGGER.error(
                    f"Failed upserting roll for {db_user.rng_username}: {traceback.format_exc()}"
                )
    except Exception:
        stats["failed"] += 1
        LOGGER.error(f"Failed fetching rolls for {db_user.rng_username}: {traceback.format_exc()}")

    return stats


@tasks.loop(seconds=RNGDLE_SYNC_INTERVAL)
async def rngdle_autosync_task() -> None:
    """Every 12 hours, fetch all registered users and sync their rolls."""
    await rngdle_fetch_task()


@rngdle_autosync_task.error
async def on_rngdle_sync_error(exc: Exception) -> None:
    LOGGER.error(f"RNGdle sync task error: {exc}")


@tasks.loop(seconds=RNGDLE_TABLE_SYNC_INTERVAL)
async def rngdle_score_to_percent_autoupdate_task() -> None:
    """Every week, update the RNGdle score to percent table."""
    has_changed = await update_compressed_score_to_percent_table()
    if has_changed:
        # The table has changed, and so the scores have all changed. Update all stored rolls with their new score
        await rngdle_fetch_task(force_full_fetch=True)
        LOGGER.info("RNGdle table sync: Successfully updated all stored scores")


@rngdle_score_to_percent_autoupdate_task.error
async def on_rngdle_table_sync_error(exc: Exception) -> None:
    LOGGER.error(f"RNGdle table update task error: {exc}")


RNGdle_FETCH_LOCK = asyncio.Lock()


async def rngdle_fetch_task(*, force_full_fetch: bool = False) -> list[dict[str, int]]:
    """Fetch all registered users and sync their rolls."""
    LOGGER.info("RNGdle sync: starting pass to fetch registered users")
    if force_full_fetch:
        LOGGER.info("RNGdle sync: running with forced full fetch enabled")

    rng_client = RNGdleClient()
    users = await RNGdleDao.get_all_registered_users()

    async with RNGdle_FETCH_LOCK:
        if not users:
            LOGGER.info("RNGdle sync: no registered users found")
            stats = []
        else:
            async with asyncio.TaskGroup() as task_group:
                tasks = [
                    task_group.create_task(
                        _process_user(
                            rng_client,
                            user,
                            log_mode="background",
                            force_full_fetch=force_full_fetch,
                        )
                    )
                    for user in users
                ]
            stats = [task.result() for task in tasks]

    LOGGER.info("RNGdle sync: pass complete")
    return stats


RNGdle_COOLDOWN = datetime.timedelta(minutes=5)


async def rngdle_fetch_with_cooldown() -> None:
    now = datetime.datetime.now()
    since_last_sync = now - _last_rngdle_sync
    if since_last_sync < RNGdle_COOLDOWN:
        LOGGER.info(
            f"RNGdle: did not fetch users because of cooldown (elapsed: {round(since_last_sync.total_seconds())}s; cooldown: {round(RNGdle_COOLDOWN.total_seconds())}s)"
        )
        return
    await rngdle_fetch_task()


async def sync_guild_users(guild_id: int) -> dict[str, int]:
    """
    Manually sync all RNGdle users for a specific guild.
    Returns a dict with counts of processed and failed users.
    """
    users = await RNGdleDao.get_registered_users(guild_id)

    if not users:
        return {"fetched": 0, "processed": 0, "failed": 0, "users_count": 0}

    all_stats = await rngdle_fetch_task()

    stats_summary = {
        "users_count": len(users),
    }
    for stats in all_stats:
        for stat, amount in stats.items():
            stats_summary.setdefault(stat, 0)
            stats_summary[stat] += amount
    return stats_summary


if __name__ == "__main__":
    from config import setup_logging
    from utils.database import init_db

    setup_logging()

    async def local_main():
        LOGGER.info("Testing locally")
        LOGGER.info("------")
        await init_db()
        LOGGER.info("Database initialized successfully.")
        LOGGER.info("------")
        await rngdle_fetch_task(force_full_fetch=True)

        rolls = await RNGdleDao.get_user_rolls(295598614405971968, 703541400901255228)
        assert rolls is not None, "No rolls"

        total_score = sum(roll.score for roll in rolls)
        LOGGER.info(f"Total score {total_score}")

    # asyncio.run(local_main())

    asyncio.run(rngdle_score_to_percent_autoupdate_task())
