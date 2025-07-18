import pathlib
from io import BytesIO

import discord
from PIL import Image, ImageDraw, ImageFont

from config import LOGGER


class LeaderboardUser:
    user: discord.User
    score: int
    rank: int


class LeaderboardGenerator:
    PODIUM_BRONZE: Image.Image
    PODIUM_SILVER: Image.Image
    PODIUM_GOLD: Image.Image

    WIDTH: int = 800
    ROW_HEIGHT: int = 90
    HEADER_HEIGHT: int = 100

    BG_COLOR = (25, 25, 25)  # Dark background
    TEXT_COLOR = (255, 255, 255)  # White text
    HEADER_BG_COLOR = (50, 50, 50)  # Slightly lighter header background
    ROW_EVEN_COLOR = (35, 35, 35)  # Even row background
    ROW_ODD_COLOR = (45, 45, 45)  # Odd row background
    HIGHLIGHT_COLOR = (0, 100, 200)  # For "async" button

    def __init__(
        self,
    ):
        """
        Initializes the Leaderboard Generator.
        """
        self.base_path = (
            f"{pathlib.Path(__file__).parent.resolve()}/../ressources"
        )
        self._load_static_resources()

    def _load_static_resources(self):
        self.PODIUM_BRONZE = (
            Image.open(f"{self.base_path}/images/medal_bronze.png")
            .convert("RGBA")
            .resize((50, 50))
        )
        self.PODIUM_SILVER = (
            Image.open(f"{self.base_path}/images/medal_silver.png")
            .convert("RGBA")
            .resize((50, 50))
        )
        self.PODIUM_GOLD = (
            Image.open(f"{self.base_path}/images/medal_gold.png")
            .convert("RGBA")
            .resize((50, 50))
        )

        try:
            # Attempt to load a specific font, fallback to default if not found or no path provided
            self.font_header = ImageFont.truetype(
                f"{self.base_path}/font/outfit.ttf", 40
            )
            self.font_regular = ImageFont.truetype(
                f"{self.base_path}/font/outfit.ttf", 30
            )
            self.font_small = ImageFont.truetype(
                f"{self.base_path}/font/outfit.ttf", 24
            )
        except IOError:
            LOGGER.warning(
                "Warning: Could not load specified font. Using Pillow's default font."
            )
            self.font_header = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    async def generate_leaderboard(self, users: list[LeaderboardUser]):
        """
        Generates the leaderboard image.

        Args:
            users (list): A list of dictionaries, each representing a user.
                          Expected keys: "username", "score", "avatar_path"..
        """
        total_height = self.HEADER_HEIGHT + (len(users) * self.ROW_HEIGHT)
        img = Image.new("RGB", (self.WIDTH, total_height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # Draw Header
        draw.rectangle(
            [0, 0, self.WIDTH, self.HEADER_HEIGHT], fill=self.HEADER_BG_COLOR
        )

        # Header Text (Adjust positions and fonts)
        headers = ["Rang", "Pseudo", "Score"]
        # Column widths are still conceptual for text placement
        # col_widths = [100, 450, 100]
        x_offsets = [15, 190, 680]  # Starting X positions for text

        draw.text(
            (x_offsets[0], self.HEADER_HEIGHT / 2 - 15),
            headers[0],
            fill=self.TEXT_COLOR,
            font=self.font_regular,
        )
        draw.text(
            (x_offsets[1], self.HEADER_HEIGHT / 2 - 15),
            headers[1],
            fill=self.TEXT_COLOR,
            font=self.font_regular,
        )
        draw.text(
            (x_offsets[2], self.HEADER_HEIGHT / 2 - 15),
            headers[2],
            fill=self.TEXT_COLOR,
            font=self.font_regular,
        )

        # Draw User Rows
        for user in users:
            y_pos = self.HEADER_HEIGHT + ((user.rank - 1) * self.ROW_HEIGHT)
            row_color = (
                self.ROW_EVEN_COLOR
                if (user.rank - 1) % 2 == 0
                else self.ROW_ODD_COLOR
            )
            draw.rectangle(
                [0, y_pos, self.WIDTH, y_pos + self.ROW_HEIGHT], fill=row_color
            )

            # Rank (handle top 3 differently)
            rank_text_x = 30  # X position for rank number or icon
            rank_text_y = y_pos + (self.ROW_HEIGHT / 2) - 15
            if user.rank == 1:
                # Placeholder for gold medal icon
                try:
                    img.paste(
                        self.PODIUM_GOLD,
                        (rank_text_x - 15, int(rank_text_y - 10)),
                        self.PODIUM_GOLD,
                    )
                except FileNotFoundError:
                    draw.text(
                        (rank_text_x, rank_text_y),
                        str(user.rank),
                        fill=(255, 215, 0),
                        font=self.font_regular,
                    )  # Gold color
            elif user.rank == 2:
                # Placeholder for silver medal icon
                try:
                    img.paste(
                        self.PODIUM_SILVER,
                        (rank_text_x - 15, int(rank_text_y - 10)),
                        self.PODIUM_SILVER,
                    )
                except FileNotFoundError:
                    draw.text(
                        (rank_text_x, rank_text_y),
                        str(user.rank),
                        fill=(192, 192, 192),
                        font=self.font_regular,
                    )  # Silver color
            elif user.rank == 3:
                # Placeholder for bronze medal icon
                try:
                    img.paste(
                        self.PODIUM_BRONZE,
                        (rank_text_x - 15, int(rank_text_y - 10)),
                        self.PODIUM_BRONZE,
                    )
                except FileNotFoundError:
                    draw.text(
                        (rank_text_x, rank_text_y),
                        str(user.rank),
                        fill=(205, 127, 50),
                        font=self.font_regular,
                    )  # Bronze color
            else:
                draw.text(
                    (rank_text_x, rank_text_y),
                    str(user.rank),
                    fill=self.TEXT_COLOR,
                    font=self.font_regular,
                )

            # Avatar (User Image) - This is where the user's actual avatar would go
            avatar_x = 100
            avatar_y = y_pos + 15
            avatar_size = 60
            try:
                avatar_data = await user.user.avatar.read()
                avatar_img = (
                    Image.open(BytesIO(avatar_data))
                    .resize((avatar_size, avatar_size))
                    .convert("RGBA")
                )
                # Create a circular mask for the avatar with antialiasing
                self.create_avatar_mask(
                    avatar_img, avatar_size, avatar_x, avatar_y, img
                )
            except Exception:
                # Si l'avatar n'est pas disponible, afficher un cercle gris par défaut
                default_avatar = Image.new(
                    "RGBA", (avatar_size, avatar_size), (120, 120, 120, 255)
                )
                self.create_avatar_mask(
                    default_avatar, avatar_size, avatar_x, avatar_y, img
                )

            # Username
            username_x = 190  # X position for username
            username_y = y_pos + (self.ROW_HEIGHT / 2) - 15
            draw.text(
                (username_x, username_y),
                user.user.name,
                fill=self.TEXT_COLOR,
                font=self.font_regular,
            )

            # Score (Niv.)
            score_x = 680  # X position for score
            score_y = y_pos + (self.ROW_HEIGHT / 2) - 15
            draw.text(
                (score_x, score_y),
                str(user.score),
                fill=self.TEXT_COLOR,
                font=self.font_regular,
            )

        return img

    @staticmethod
    def create_avatar_mask(avatar_img, avatar_size, avatar_x, avatar_y, img):
        mask = Image.new("L", (avatar_size * 4, avatar_size * 4), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar_size * 4, avatar_size * 4), fill=255)
        mask = mask.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        avatar_img.putalpha(mask)
        img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)
