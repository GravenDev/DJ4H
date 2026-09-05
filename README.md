<h3 align="center">
  <img src="https://avatars.githubusercontent.com/u/78621926?s=200&v=4" width="75"><br/>
  DJ4H <br/>
  This project is under the <a href="https://choosealicense.com/licenses/gpl-3.0/">GNU GPL v3</a> license<br/><br/>
</h3>

# <p align="center">`DJ4H`</p>

[![CI](https://github.com/GravenDev/DJ4H/actions/workflows/ci.yml/badge.svg)](https://github.com/GravenDev/DJ4H/actions/workflows/ci.yml)
[![Build & Deploy DJ4H](https://github.com/GravenDev/DJ4H/actions/workflows/deploy.yml/badge.svg)](https://github.com/GravenDev/DJ4H/actions/workflows/deploy.yml)

All the projects in the <code>AsyncCommunityDiscord</code> organisation are used by the discord server <code>
discord.gg/graven</code> both by the moderators and the members.
Most of the contributors are part of the staff but the members are also allowed to contribute.

---

## Global information

| Global information |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
|--------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Description        | DJ4H is a Discord bot designed to enhance server engagement. It includes features for tracking activity engagement, providing a dynamic and interactive experience for communities.                                                                                                                                                                                                                                                                                                                                          |
| Collaborators      | <img src="https://avatars.githubusercontent.com/u/73261020?v=4" alt="drawing" width="25"/> [Gamingdy](https://github.com/Gamingdy),  <img src="https://avatars.githubusercontent.com/u/34105327?s=64&v=4" alt="drawing" width="25"/> [Lindwen](https://github.com/Lindwen), <img src="https://avatars.githubusercontent.com/u/1571189?s=64&v=4" alt="drawing" width="25"/> [Loïc R](https://github.com/Lramelot),  <img src="https://avatars.githubusercontent.com/u/69684024?s=64&v=4" alt="drawing" width="25"/> [GabHas](https://github.com/TheRealGabHas) |
| Version            | 1.0.0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

---

## State

![](https://img.shields.io/badge/State-In_production-green?style=for-the-badge)

<!-- Replace with your repository URL -->
![](https://img.shields.io/github/issues/AsyncCommunityDiscord/DJ4H?style=for-the-badge)

<!-- Replace with your repository URL -->
![](https://img.shields.io/github/issues-pr/AsyncCommunityDiscord/DJ4H?style=for-the-badge)

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

| Command | Description |
| --- | --- |
| `/config [channel] [delay]` | Sets the game channel and the required delay to score a point. Time prefixes: `s` (seconds), `m` (minutes), `h` (hours), `d` (days). |
| `/set [member] [score]` | Sets a member's score to the specified value. |
| `/dump_log` | Retrieves the bot's log file. |

### Player

| Command | Description |
| --- | --- |
| `/leaderboard` | Displays an image with the top 10 players. |
| `/score` | Shows your own score. |

## Installation

### Prerequisites

- Python 3.9+
- Poetry (for dependency management)

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/AsyncCommunityDiscord/DJ4H.git
   cd DJ4H
   ```
2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

## Configuration

Create a `.env` file in the project root with the following variables:

```env
BOT_TOKEN=your_discord_bot_token
DEBUG_GUILD_ID=your_dev_server_id  # Optional
DATABASE_PATH=dj4h.db              # Optional, defaults to dj4h.db
```

- `BOT_TOKEN`: Your Discord bot token (required).
- `DEBUG_GUILD_ID`: Discord server ID for development (optional).
- `DATABASE_PATH`: Path to the SQLite database file (optional).

## Usage

### Development Mode

```bash
# Run the bot
poetry run python main.py
```

### Production Mode with Docker

```bash
# Build and run with Docker Compose
docker-compose -f compose-prod.yml up -d
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
docker-compose up -d
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
��   └── handler/events.py     # Main game logic
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
