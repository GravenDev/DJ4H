import argparse
from ast import literal_eval
import bisect
from datetime import datetime
from enum import Enum
import json
from math import ceil, floor
from pathlib import Path
import re
import typing

import requests

from config import LOGGER

ROOT_PATH = Path(__file__).parent.parent
SCORE_TO_PERCENT_PATH = ROOT_PATH / "ressources" / "rngdle" / "score_to_percent.json"
COMPRESSED_SCORE_TO_PERCENT_PATH = SCORE_TO_PERCENT_PATH.with_stem("compressed_score_to_percent")


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


def parse_score_to_percent_table(data: str) -> dict[str, str]:
    ENTRY_RE = re.compile(r"(\w+)\s*:\s*(\d*(?:\.\d+)?)")
    table: dict[str, str] = {score: percent for score, percent in ENTRY_RE.findall(data)}
    return table


def evaluate_score_to_percent_table(table: dict[str, str]) -> dict[int, float]:
    evaluated_data: dict[int, float] = {}
    for score, percent in table.items():
        actual_score = typing.cast(int, literal_eval(score))
        actual_percent = typing.cast(float, literal_eval(percent))

        if not isinstance(actual_score, (int, float)):
            LOGGER.warning(
                f"RNGdle: found key of type {type(actual_score)} with value {actual_score} while parsing score_to_percent.json"
            )
        elif isinstance(actual_score, float) and int(actual_score) != actual_score:
            LOGGER.warning(
                f"RNGdle: found key with value {actual_score} (invalid score) while parsing score_to_percent.json"
            )

        evaluated_data[actual_score] = actual_percent
    return evaluated_data


def fetch_score_to_percent_string():
    TABLE_FILE_URL = "https://www.rngdle.com/_next/static/chunks/13342e749f60f9c2.js"

    js_file = requests.get(TABLE_FILE_URL).content

    if len(js_file) < 100_000:
        LOGGER.warning(
            f"RNGdle: The file *seems* too small to contain the score to percent table ({len(js_file)} < 100 KB)"
        )
        return ""

    # Detect the score percentiles dict-like structure
    dict_pattern = re.compile(
        r"{(?:(?:0x[a-fA-F0-9]+|\d+|\d+e\d+)\s*:\s*(?:\d+(?:\.\d+)?|\.\d+),?)+}"
    )
    result = dict_pattern.search(str(js_file))
    if result is None:
        return ""

    return result.group()


def load_score_to_percent_table():
    with open(SCORE_TO_PERCENT_PATH) as file:
        data_raw = file.read()

    parsed_table = parse_score_to_percent_table(data_raw)
    return evaluate_score_to_percent_table(parsed_table)


def load_compressed_score_to_percent_table():
    with open(COMPRESSED_SCORE_TO_PERCENT_PATH, mode="r") as file:
        data = json.load(file)
    score_to_percent_table: dict[int, float] = {
        int(score): percent for score, percent in data.items()
    }
    return score_to_percent_table


def store_compressed_score_to_percent_table(new_table: dict[int, float]):
    global COMPRESSED_SCORE_TO_PERCENT, KNOWN_COMPRESSED_SCORES
    # Update the globals with the new table
    COMPRESSED_SCORE_TO_PERCENT = new_table
    KNOWN_COMPRESSED_SCORES = sorted(COMPRESSED_SCORE_TO_PERCENT.keys())

    with open(COMPRESSED_SCORE_TO_PERCENT_PATH, "w") as file:
        json.dump(new_table, file)


def update_compressed_score_to_percent_table():
    LOGGER.info("RNGdle table sync: Start update of the score to percent table")
    score_to_percent_raw = fetch_score_to_percent_string()
    if not score_to_percent_raw:
        LOGGER.warning(
            "RNGdle: Could not fetch the score to percent table from the website, aborting the update"
        )
        return
    score_to_percent_parsed = parse_score_to_percent_table(score_to_percent_raw)
    score_to_percent_table = evaluate_score_to_percent_table(score_to_percent_parsed)
    compressed_score_to_percent = compress_score_to_percent(score_to_percent_table)
    store_compressed_score_to_percent_table(compressed_score_to_percent)
    LOGGER.info("RNGdle table sync: Successfully updated the score to percent table")


def compress_score_to_percent(dico: dict[int, float]) -> dict[int, float]:
    # Compute a dict that stores for each percent which is the lowest score to reach that percent
    percent_to_score_min: dict[float, int] = {}
    for score, percent in dico.items():
        percent_rounded = int(percent * 2) / 2  # truncate to the previous .5
        if score < percent_to_score_min.get(percent_rounded, float("inf")):
            percent_to_score_min[percent_rounded] = score

    # Invert the dict to get a score that serves as a lower bound to determine the percent
    compressed_dico = {score: percent for percent, score in percent_to_score_min.items()}
    return compressed_dico


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


def get_score_tier_from_compressed_table(score: int):
    if score < 0:
        LOGGER.warning(f"RNGdle: unexpected negative score ({score}).")
        return Tier.ERROR

    percent = get_score_percent(score)

    if 0 <= percent < 1:
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
        LOGGER.warning(f"RNGdle: unexpected score ({score}) and percent value ({percent}).")
        return Tier.ERROR

    return tier


def get_score_tier(score: int):
    return get_score_tier_from_compressed_table(score)


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


def format_percent(percent: float):
    if percent > 50:
        top_percent = 100 - percent
        percent_text = f"{floor(top_percent)}%"
    else:
        bottom_percent = percent
        percent_text = f"{ceil(bottom_percent)}%"
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


if __name__ == "__main__":
    # Perform some operations on rngdle resources to test updates mechanisms
    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument(
        "-c",
        "--compress-score-table",
        help="Read, compress and store the score to percent table. This should only be used locally as it requires having the full table stored. Instead, consider using --update-score-table that fetches the table from the website",
        action="store_true",
    )

    arg_parser.add_argument(
        "-u",
        "--update-score-table",
        help="Fetch, compress and store the score to percent table",
        action="store_true",
    )

    args = arg_parser.parse_args()

    if args.compress_score_table:
        base_score_to_percent = load_score_to_percent_table()
        compressed_score_to_percent = compress_score_to_percent(base_score_to_percent)
        store_compressed_score_to_percent_table(compressed_score_to_percent)

    if args.update_score_table:
        update_compressed_score_to_percent_table()
