import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

README = Path("README.md")

CONTRIBUTORS_START = "<!-- CONTRIBUTORS:START -->"
CONTRIBUTORS_END = "<!-- CONTRIBUTORS:END -->"

VERSION_START = "<!-- VERSION:START -->"
VERSION_END = "<!-- VERSION:END -->"

GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]


def github_api(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "README-metadata-updater",
        },
    )

    with urllib.request.urlopen(request) as response:
        return json.load(response)


def get_contributors():
    """Fetch all repository collaborators, handling pagination."""
    contributors = []
    page = 1

    while True:
        url = (
            f"https://api.github.com/repos/"
            f"{GITHUB_REPOSITORY}/contributors"
            f"?per_page=100&page={page}"
        )

        users = github_api(url)

        if not users:
            break

        contributors.extend(users)

        if len(users) < 100:
            break

        page += 1

    return contributors


def generate_contributors(contributors):
    """Generate the Markdown for the contributors."""
    contributors.sort(key=lambda user: user["login"].lower())

    entries = []

    for user in contributors:
        login = user["login"].capitalize()
        avatar_url = user["avatar_url"]
        profile_url = user["html_url"]

        entries.append(
            f'<img src="{avatar_url}" '
            f'alt="{login}" '
            f'width="25"/> '
            f"[{login}]({profile_url})"
        )

    return ", ".join(entries)


def get_latest_tag():
    """
    Return the highest version tag according to Git's version sorting.

    Examples:
        v1.10.0 > v1.9.0
        v2.0.0 > v1.99.0
    """

    result = subprocess.run(
        [
            "git",
            "tag",
            "--sort=-v:refname",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    tags = [tag.strip() for tag in result.stdout.splitlines() if tag.strip()]

    if not tags:
        raise RuntimeError("No Git tags found.")

    return tags[0]


def replace_section(
    content: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
):
    """Replace the content between two README markers."""

    pattern = re.escape(start_marker) + r".*?" + re.escape(end_marker)

    replacement_text = f"{start_marker} {replacement} {end_marker}"

    updated, count = re.subn(
        pattern,
        replacement_text,
        content,
        count=1,
        flags=re.DOTALL,
    )

    if count != 1:
        raise RuntimeError(
            f"Could not find README markers:\n" f"{start_marker}\n" f"...\n" f"{end_marker}"
        )

    return updated


def main():
    if not README.exists():
        raise FileNotFoundError("README.md not found.")

    content = README.read_text(encoding="utf-8")

    # Fetch contributors once.
    contributors_data = get_contributors()
    contributors = generate_contributors(contributors_data)

    # Get the latest version tag.
    latest_tag = get_latest_tag()

    # Update contributors.
    content = replace_section(
        content,
        CONTRIBUTORS_START,
        CONTRIBUTORS_END,
        contributors,
    )

    # Update version.
    content = replace_section(
        content,
        VERSION_START,
        VERSION_END,
        latest_tag,
    )

    README.write_text(
        content,
        encoding="utf-8",
    )

    print(f"Found {len(contributors_data)} contributors.")
    print(f"Latest tag: {latest_tag}")


if __name__ == "__main__":
    main()
