from ast import literal_eval
import bisect
from datetime import datetime
from enum import Enum
import json
from pathlib import Path
import typing

import requests

from config import LOGGER


class UserRolls:
    def __init__(self, number, date, score, badges=0):
        self.number = number
        self.date = date
        self.score = score
        self.badges = badges


def to_user_rolls(rolls: list):
    user_rolls = []
    for roll in rolls:
        number = roll["number"]
        score = roll["totalScore"]
        badges = roll.get("badgeCount", 0)
        time = to_timestamp(roll["rolledAt"])
        user_roll = UserRolls(number, time, score, badges)
        user_rolls.append(user_roll)
    return user_rolls


def to_timestamp(date):
    dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
    timestamp = int(dt.timestamp() * 1000)
    return timestamp


def load_score_to_percent_table():

    root_path = Path(__file__).parent.parent
    rngdle_resources = root_path / "ressources" / "rngdle"
    with open(rngdle_resources / "score_to_percent.json", mode="r") as file:
        data = json.load(file)

    evaluated_data: dict[int, float] = {}
    for score, percent in data.items():
        actual_score = typing.cast(int, literal_eval(score))
        if not isinstance(actual_score, (int, float)):
            LOGGER.warning(
                f"RNGdle: found key of type {type(actual_score)} with value {actual_score} while parsing score_to_percent.json"
            )
        elif isinstance(actual_score, float) and int(actual_score) != actual_score:
            LOGGER.warning(
                f"RNGdle: found key with value {actual_score} (invalid score) while parsing score_to_percent.json"
            )

        evaluated_data[actual_score] = percent
    return evaluated_data


def load_compressed_score_to_percent_table():

    root_path = Path(__file__).parent.parent
    rngdle_resources = root_path / "ressources" / "rngdle"
    with open(rngdle_resources / "compressed_score_to_percent.json", mode="r") as file:
        data = json.load(file)

    evaluated_data: dict[int, float] = {}
    for score, percent in data.items():
        actual_score = typing.cast(int, literal_eval(score))
        if not isinstance(actual_score, (int, float)):
            LOGGER.warning(
                f"RNGdle: found key of type {type(actual_score)} with value {actual_score} while parsing score_to_percent.json"
            )
        elif isinstance(actual_score, float) and int(actual_score) != actual_score:
            LOGGER.warning(
                f"RNGdle: found key with value {actual_score} (invalid score) while parsing score_to_percent.json"
            )

        evaluated_data[actual_score] = percent
    return evaluated_data


SCORE_TO_PERCENT: dict[int, float] = {}
# Uncomment to fetch the JSON table
# SCORE_TO_PERCENT = load_score_to_percent_table()
KNOWN_SCORES = sorted(SCORE_TO_PERCENT.keys())

COMPRESSED_SCORE_TO_PERCENT = load_compressed_score_to_percent_table()
KNOWN_COMPRESSED_SCORES = sorted(COMPRESSED_SCORE_TO_PERCENT.keys())


class Tier(Enum):
    TRASH = 1
    COMMON = 2
    UNCOMMON = 3
    RARE = 4
    EPIC = 5
    ANOMALY = 6
    MYTHIC = 7
    ERROR = 8

# From dark theme
# TIER_TO_COLOR = {
#     Tier.TRASH: (255, 210, 48), # dark
#     Tier.COMMON: (229, 231, 235), # dark
#     Tier.UNCOMMON: (0, 212, 146), # dark
#     Tier.RARE: (81, 162, 255), # dark
#     Tier.EPIC: (194, 122, 255), # dark
#     Tier.ANOMALY: (255, 137, 4), # dark
#     Tier.MYTHIC: (193, 0, 7), # dark
# }

# From light theme
# TIER_TO_COLOR = {
#     Tier.TRASH: (255, 210, 48), # light
#     Tier.COMMON: (153, 161, 175), # light
#     Tier.UNCOMMON: (94, 233, 181), # light
#     Tier.RARE: (142, 197, 255), # light
#     Tier.EPIC: (218, 178, 255), # light
#     Tier.ANOMALY: (255, 184, 106), # light
#     Tier.MYTHIC: (253, 165, 213), # light
# }

# In use
TIER_TO_COLOR = {
    Tier.TRASH: (229, 126, 98),  # custom
    Tier.COMMON: (229, 231, 235),  # dark
    Tier.UNCOMMON: (94, 233, 181),  # light
    Tier.RARE: (142, 197, 255),  # light
    Tier.EPIC: (218, 178, 255),  # light
    Tier.ANOMALY: (255, 137, 4),  # dark
    Tier.MYTHIC: (253, 165, 213),  # light
    Tier.ERROR: (255, 41, 41),
}


def get_score_tier_from_table(score: int):
    if score not in SCORE_TO_PERCENT:
        LOGGER.warning(f"RNGdle: unexpected score {score} (not in table).")
        # Enable if you prefer to not consider unknown scores
        # return Tier.ERROR

        # Find the highest known score that is below the given score and consider it for selecting the tier
        fixed_score_idx = bisect.bisect_left(KNOWN_SCORES, score) - 1
        fixed_score_idx = max(fixed_score_idx, 0)
        score = KNOWN_SCORES[fixed_score_idx]

    percent = SCORE_TO_PERCENT[score]

    if 0 <= percent < 1.5:
        tier = Tier.TRASH
    elif percent < 50:
        tier = Tier.COMMON
    elif percent < 75:
        tier = Tier.UNCOMMON
    elif percent < 90:
        tier = Tier.RARE
    elif percent < 95:
        tier = Tier.EPIC
    elif percent < 99:
        tier = Tier.ANOMALY
    elif percent < 100:
        tier = Tier.MYTHIC
    else:
        LOGGER.warning(
            f"RNGdle: unexpected score ({score}) and percent value ({percent})."
        )
        return Tier.ERROR

    return tier


def get_score_tier(score: int):
    if score < 0:
        LOGGER.warning(f"RNGdle: unexpected negative score ({score}).")
        return Tier.ERROR

    if 0 <= score < 2098:  # percent < 1.5
        return Tier.TRASH
    elif score < 5_349:  # percent < 50
        return Tier.COMMON
    elif score < 8_642:  # percent < 75
        return Tier.UNCOMMON
    elif score < 20_245:  # percent < 90
        return Tier.RARE
    elif score < 33_971:  # percent < 95
        return Tier.EPIC
    elif score < 150_679:  # percent < 99
        return Tier.ANOMALY
    elif score <= 181_186_584:  # percent < 100 (highest known score)
        return Tier.MYTHIC

    # Score is too high
    LOGGER.warning(
        f"RNGdle: unexpected score ({score}), higher than highest known score."
    )
    return Tier.ERROR


def get_tier_color(tier: Tier):
    return TIER_TO_COLOR[tier]


def get_score_percent(score: int):
    # Find the index to the highest know score that is lower than given score
    score_idx = bisect.bisect_left(KNOWN_COMPRESSED_SCORES, score) - 1
    score_idx = max(score_idx, 0)
    percent_score = KNOWN_COMPRESSED_SCORES[score_idx]
    # Return it's percent
    return COMPRESSED_SCORE_TO_PERCENT[percent_score]


def format_tier(tier: Tier):
    return f"{tier.name.title()}"


def format_percent(percent: int):
    if percent > 50:
        beat_percent = 99 - percent
        percent_text = f"{beat_percent}%"
        # percent_text = f"Top {beat_percent}%"
    else:
        percent_text = f"{percent}%"
        # percent_text = f"Bottom {percent}%"
    return percent_text


class RNGdle:
    def __init__(self):
        self.api_url = "https://www.rngdle.com/api/users/{}/rolls?limit=100&offset={}"

    def get_user_rolls(
        self, username, previous_roll: list[UserRolls] | None = None, offset=0
    ) -> list[UserRolls] | None:
        if previous_roll is None:
            previous_roll = []

        url = self.api_url.format(username, offset)
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            user_roll = to_user_rolls(result["rolls"])
            previous_roll += user_roll
            if result["hasMore"]:
                return self.get_user_rolls(username, previous_roll, offset + 100)
            return previous_roll
        else:
            return None
