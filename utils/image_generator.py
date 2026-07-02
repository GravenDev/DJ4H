import pathlib
from io import BytesIO

import discord
from PIL import Image, ImageDraw, ImageFont

from config import LOGGER


class LeaderboardUser:
    user: discord.User
    score: str
    tirage: str
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

    def __init__(self):
        self.font_path = None
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
            self.font_path = f"{self.base_path}/font/outfit.ttf"
            self.font_header = ImageFont.truetype(self.font_path, 40)
            self.font_regular = ImageFont.truetype(self.font_path, 30)
            self.font_small = ImageFont.truetype(self.font_path, 24)
        except IOError:
            LOGGER.warning(
                "Warning: Could not load specified font. Using Pillow's default font."
            )
            self.font_path = None
            self.font_header = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def _draw_fitted(self, draw, text, x, y, max_width, base_font, fill):
        if self.font_path is None:
            draw.text((x, y), text, fill=fill, font=base_font)
            return
        font = base_font
        while draw.textlength(text, font=font) > max_width and font.size > 1:
            font = ImageFont.truetype(self.font_path, font.size - 1)
        draw.text((x, y), text, fill=fill, font=font)

    async def generate_leaderboard(self, users: list[LeaderboardUser]):
        total_height = self.HEADER_HEIGHT + (len(users) * self.ROW_HEIGHT)
        img = Image.new("RGB", (self.WIDTH, total_height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.rectangle(
            [0, 0, self.WIDTH, self.HEADER_HEIGHT], fill=self.HEADER_BG_COLOR
        )

        headers = ["Rang", "Pseudo", "Tirage", "Score"]
        x_offsets = [15, 190, 520, 650]

        for i, header in enumerate(headers):
            draw.text(
                (x_offsets[i], self.HEADER_HEIGHT / 2 - 15),
                header,
                fill=self.TEXT_COLOR,
                font=self.font_regular,
            )

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

            rank_text_x = 30
            rank_text_y = y_pos + (self.ROW_HEIGHT / 2) - 15
            if user.rank == 1:
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
                    )
            elif user.rank == 2:
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
                    )
            elif user.rank == 3:
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
                    )
            else:
                draw.text(
                    (rank_text_x, rank_text_y),
                    str(user.rank),
                    fill=self.TEXT_COLOR,
                    font=self.font_regular,
                )

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
                self.create_avatar_mask(
                    avatar_img, avatar_size, avatar_x, avatar_y, img
                )
            except Exception:
                default_avatar = Image.new(
                    "RGBA", (avatar_size, avatar_size), (120, 120, 120, 255)
                )
                self.create_avatar_mask(
                    default_avatar, avatar_size, avatar_x, avatar_y, img
                )

            username_x = 190
            username_y = y_pos + (self.ROW_HEIGHT / 2) - 15
            self._draw_fitted(
                draw,
                user.user.name,
                username_x,
                username_y,
                320,
                self.font_regular,
                self.TEXT_COLOR,
            )

            tirage_x = x_offsets[2]
            tirage_y = y_pos + (self.ROW_HEIGHT / 2) - 15
            draw.text(
                (tirage_x, tirage_y),
                user.tirage,
                fill=self.TEXT_COLOR,
                font=self.font_regular,
            )

            score_x = x_offsets[3]
            score_y = y_pos + (self.ROW_HEIGHT / 2) - 15
            self._draw_fitted(
                draw,
                user.score,
                score_x,
                score_y,
                140,
                self.font_regular,
                self.TEXT_COLOR,
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
