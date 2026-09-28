<h3 align="center">
  <img alt="Image showing Graven development discord logo" src="https://avatars.githubusercontent.com/u/78621926?s=200&v=4" width="75"><br/>
  DJ4H <br/>
  This project is under the <a href="https://choosealicense.com/licenses/gpl-3.0/">GNU GPL v3</a> license<br/><br/>
</h3>

# <p align="center">`DJ4H`</p>

[![CI](https://github.com/GravenDev/DJ4H/actions/workflows/ci.yml/badge.svg)](https://github.com/GravenDev/DJ4H/actions/workflows/ci.yml)
[![Build & Deploy DJ4H](https://github.com/GravenDev/DJ4H/actions/workflows/deploy.yml/badge.svg)](https://github.com/GravenDev/DJ4H/actions/workflows/deploy.yml)

All the projects in the <code>GravenDev</code> organisation are used by the discord server <code>
discord.gg/graven</code> both by the moderators and the members.
Most of the contributors are part of the staff but the members are also allowed to contribute.

---

## Global information

| Global information |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
|--------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Description        | DJ4H is a Discord bot designed to enhance server engagement. It includes features for tracking activity engagement, providing a dynamic and interactive experience for communities.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Contributors       | <!-- CONTRIBUTORS:START --> <img src="https://avatars.githubusercontent.com/u/44125445?v=4" alt="Alessevan" width="25"/> [Alessevan](https://github.com/Alessevan), <img src="https://avatars.githubusercontent.com/u/185201144?v=4" alt="Alexandre-josepavel" width="25"/> [Alexandre-josepavel](https://github.com/alexandre-josepavel), <img src="https://avatars.githubusercontent.com/u/26577763?v=4" alt="Antoinejt" width="25"/> [Antoinejt](https://github.com/AntoineJT), <img src="https://avatars.githubusercontent.com/in/29110?v=4" alt="Dependabot[bot]" width="25"/> [Dependabot[bot]](https://github.com/apps/dependabot), <img src="https://avatars.githubusercontent.com/u/74816698?v=4" alt="Flenderrax" width="25"/> [Flenderrax](https://github.com/FlenderrAX), <img src="https://avatars.githubusercontent.com/u/73261020?v=4" alt="Gamingdy" width="25"/> [Gamingdy](https://github.com/gamingdy), <img src="https://avatars.githubusercontent.com/u/34105327?v=4" alt="Lindwen" width="25"/> [Lindwen](https://github.com/Lindwen), <img src="https://avatars.githubusercontent.com/u/1571189?v=4" alt="Lramelot" width="25"/> [Lramelot](https://github.com/Lramelot), <img src="https://avatars.githubusercontent.com/u/84503460?v=4" alt="Mityno" width="25"/> [Mityno](https://github.com/Mityno), <img src="https://avatars.githubusercontent.com/u/44524788?v=4" alt="Redstom" width="25"/> [Redstom](https://github.com/RedsTom), <img src="https://avatars.githubusercontent.com/in/2740?v=4" alt="Renovate[bot]" width="25"/> [Renovate[bot]](https://github.com/apps/renovate), <img src="https://avatars.githubusercontent.com/u/69684024?v=4" alt="Therealgabhas" width="25"/> [Therealgabhas](https://github.com/TheRealGabHas) <!-- CONTRIBUTORS:END --> |
| Version            | <!-- VERSION:START --> v1.5.4 <!-- VERSION:END -->                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

---

## State

![](https://img.shields.io/badge/State-In_production-green?style=for-the-badge)

![](https://img.shields.io/github/issues/GravenDev/DJ4H?style=for-the-badge)

![](https://img.shields.io/github/issues-pr/GravenDev/DJ4H?style=for-the-badge)

---

## About The Project

DJ4H is a Discord bot designed for the "4-hour Game" on the Async - Community server (formerly Graven - Développement).
Its primary purpose is to automate point counting.

Although designed for the Async - Community server, the bot can be used on other servers and can run on multiple servers
simultaneously.

DJ4H implements a competitive timing game called "The 4h Game". Players compete by sending messages in a designated
channel after a configurable delay period has passed since the last message.

## Features

- Automatic point counting
- Leaderboard image generation
- Player point management (set/view scores)

## Commands

Required command parameters are shown in brackets (`[required]`) while optional parameters are in parentheses (
`(optional)`).

### Configuration (Admin only)

| Command                     | Description                                                                                                                          |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `/config [channel] [delay]` | Sets the game channel and the required delay to score a point. Time prefixes: `s` (seconds), `m` (minutes), `h` (hours), `d` (days). |
| `/set [member] [score]`     | Sets a member's score to the specified value.                                                                                        |
| `/dump_log`                 | Retrieves the bot's log file.                                                                                                        |

### Player

| Command        | Description                                |
|----------------|--------------------------------------------|
| `/leaderboard` | Displays an image with the top 10 players. |
| `/score`       | Shows your own score.                      |

## Installation

### Prerequisites

- Python 3.13
- Poetry (for dependency management)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/GravenDev/DJ4H.git
   cd DJ4H
   ```
2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

## Configuration

```bash
cp .env.example .env
```

Then fill in `BOT_TOKEN`. Every variable is documented in `.env.example`; the commented-out ones are optional and show
their default value.

## Usage

### Development Mode

```bash
# Run the bot
poetry run python main.py
```

### Production Mode with Docker

```bash
# Build and run with Docker Compose
docker compose -f compose.prod.yaml up -d
```

Make a deployment

```bash
# clone repository
git checkout master
git pull
git tag vx.x.x
git push origin vx.x.x
```

### Development Mode with Docker

```bash
# Build and run with Docker Compose
docker compose up -d
```

## Development

### Code Formatting

```bash
# Format code with Black
poetry run black .
```

### Project Structure

```
DJ4H/
├── main.py                    # Entry point
├── config.py                  # Configuration and logging
├── commands/                  # Discord commands
│   ├── cogs/game.py          # /leaderboard and /score commands
│   └── handler/events.py     # Main game logic
├── utils/
│   ├── database/             # Database layer
│   │   ├── connection.py     # SQLite connection
│   │   ├── schema.py         # Data models
│   │   └── dao/              # Data Access Objects
│   └── image_generator.py    # Image generation for leaderboard
└── docker/                   # Docker configuration
```

## Database

The bot uses SQLite with three main tables:

- `guilds`: Server configuration (channel, delay).
- `users`: User scores per server.
- `messages`: Message tracking for game logic.

## Support

To report bugs or request features, please create an issue on the GitHub repository.
