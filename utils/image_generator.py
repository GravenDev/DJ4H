import pathlib
from io import BytesIO
import typing

import discord
from PIL import Image, ImageDraw, ImageFont

from config import LOGGER
from utils.rngdle import Tier

SPACE_WIDTH = 8
NUM_WIDTH = 18.5
TIER_SQUARE_SIZE = 40

type FontType = ImageFont.FreeTypeFont | ImageFont.ImageFont
type ColorType = tuple[int, int, int]


class LeaderboardUser:
    user: discord.User
    rank: int

    column_headers: list[str] = []
    column_x_offsets: list[int] = []
    column_max_widths: list[int] = []

    def get_column_values(self) -> list[str]:
        raise NotImplementedError


class RNGdleLeaderboardUser(LeaderboardUser):
    score: str
    tirage: str
    tier: Tier
    tier_text: str
    percent_text: str
    tier_color: ColorType

    column_headers = ["Tirage", "Rareté", "Score", "Placement"]
    column_x_offsets = [500, 640, 840, 990]
    # Can add an extrac width to be used as a margin spacer on the right of the image
    column_max_widths = [140, 180, 130, 180, 20]

    def get_column_values(self) -> list[str]:
        return [self.tirage, self.tier_text, self.score, self.percent_text]


class JD4HLeaderboardUser(LeaderboardUser):
    score: str

    column_headers = ["Score"]
    column_x_offsets = [650]
    column_max_widths = [140]

    def get_column_values(self) -> list[str]:
        return [self.score]


class LeaderboardGenerator:
    PODIUM_BRONZE: Image.Image
    PODIUM_SILVER: Image.Image
    PODIUM_GOLD: Image.Image

    WIDTH: int = 800
    ROW_HEIGHT: int = 90
    HEADER_HEIGHT: int = 100

    BG_COLOR: ColorType = (25, 25, 25)  # Dark background
    TEXT_COLOR: ColorType = (255, 255, 255)  # White text
    # Slightly lighter header background
    HEADER_BG_COLOR: ColorType = (50, 50, 50)
    ROW_EVEN_COLOR: ColorType = (35, 35, 35)  # Even row background
    ROW_ODD_COLOR: ColorType = (45, 45, 45)  # Odd row background
    HIGHLIGHT_COLOR: ColorType = (0, 100, 200)  # For "async" button

    def __init__(self):
        self.font_path: pathlib.Path | None = None
        self.base_path: pathlib.Path = (
            pathlib.Path(__file__).parent.resolve() / ".." / "ressources"
        )

        self._load_static_resources()

    def _load_static_resources(self):
        self.PODIUM_BRONZE = (
            Image.open(self.base_path / "images" / "medal_bronze.png")
            .convert("RGBA")
            .resize((50, 50))
        )
        self.PODIUM_SILVER = (
            Image.open(self.base_path / "images" / "medal_silver.png")
            .convert("RGBA")
            .resize((50, 50))
        )
        self.PODIUM_GOLD = (
            Image.open(self.base_path / "images" / "medal_gold.png")
            .convert("RGBA")
            .resize((50, 50))
        )

        try:
            self.font_path = self.base_path / "font" / "outfit.ttf"
            self.font_header = ImageFont.truetype(self.font_path, 40)
            self.font_regular = ImageFont.truetype(self.font_path, 30)
            self.font_small = ImageFont.truetype(self.font_path, 24)

            self.font_mono_path = self.base_path / "font" / "spacemono_bold.ttf"
            self.font_mono_regular = ImageFont.truetype(self.font_mono_path, 30)
        except IOError:
            LOGGER.warning(
                "Warning: Could not load specified font. Using Pillow's default font."
            )
            self.font_path = None
            self.font_header = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

            self.font_mono_regular = ImageFont.load_default()

    def _draw_fitted(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: float,
        y: float,
        max_width: float,
        base_font: FontType,
        fill: ColorType,
        anchor: str = "lt",
    ):
        if self.font_path is None:
            draw.text((x, y), text, fill=fill, font=base_font, anchor=anchor)
            return
        font = base_font
        font_path = getattr(font, "path", self.font_path)
        font_size = getattr(font, "size", 30)  # 30 is regular font size
        while draw.textlength(text, font=font) > max_width and font_size > 1:
            font_size -= 1
            font = ImageFont.truetype(font_path, font_size)
        draw.text((x, y), text, fill=fill, font=font, anchor=anchor)

    def _draw_fitted_align_right(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: float,
        y: float,
        max_width: float,
        base_font: FontType,
        fill: ColorType,
    ):
        self._draw_fitted(
            draw,
            text,
            x + max_width,
            y,
            max_width,
            base_font,
            fill,
            anchor="rt",
        )

    async def generate_leaderboard(self, users: list[LeaderboardUser]):
        if not users:
            raise ValueError("No users provided")

        model = type(users[0])

        total_height = self.HEADER_HEIGHT + (len(users) * self.ROW_HEIGHT)
        min_possible_width = self.WIDTH
        if model.column_x_offsets:
            last_start_pos = model.column_x_offsets[-1]
            has_spacer = len(model.column_x_offsets) != len(
                model.column_max_widths
            )
            last_width = (
                model.column_max_widths[-2]
                if has_spacer
                else model.column_max_widths[-1]
            )
            spacer_width = model.column_max_widths[-1] if has_spacer else 0
            total_width = last_start_pos + last_width + spacer_width

            min_possible_width = max(min_possible_width, total_width)

        img = Image.new(
            "RGB", (min_possible_width, total_height), self.BG_COLOR
        )
        draw = ImageDraw.Draw(img)

        draw.rectangle(
            [0, 0, min_possible_width, self.HEADER_HEIGHT],
            fill=self.HEADER_BG_COLOR,
        )

        headers = ["Rang", "Pseudo", *model.column_headers]
        x_offsets = [15, 190, *model.column_x_offsets]

        for i, header in enumerate(headers):
            x, y = x_offsets[i], self.HEADER_HEIGHT / 2 - 15

            anchor = "lt"
            if model == RNGdleLeaderboardUser and i >= 2:
                # Anchor to the right and fix the x position for the text
                anchor = "rt"
                x += model.column_max_widths[i - 2]

            draw.text(
                (x, y),
                header,
                fill=self.TEXT_COLOR,
                font=self.font_regular,
                anchor=anchor,
            )

        for user in users:
            y_pos = self.HEADER_HEIGHT + ((user.rank - 1) * self.ROW_HEIGHT)
            row_color = (
                self.ROW_EVEN_COLOR
                if (user.rank - 1) % 2 == 0
                else self.ROW_ODD_COLOR
            )
            draw.rectangle(
                [0, y_pos, min_possible_width, y_pos + self.ROW_HEIGHT],
                fill=row_color,
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

            for col_idx, col_value in enumerate(user.get_column_values()):
                col_x = model.column_x_offsets[col_idx]
                col_y = y_pos + (self.ROW_HEIGHT / 2) - 15
                max_width = model.column_max_widths[col_idx]

                font = self.font_regular
                text_color = self.TEXT_COLOR

                if isinstance(user, RNGdleLeaderboardUser):

                    if user.column_headers[col_idx] == "Tirage":  # RNGdle draw
                        # Left pad the number string to be at least 7 chars long for even rendering
                        col_value = f"{col_value:>7}"
                        font = self.font_mono_regular
                        text_color = user.tier_color

                    elif user.column_headers[col_idx] == "Rareté":
                        text_color = user.tier_color

                self._draw_fitted_align_right(
                    draw,
                    col_value,
                    col_x,
                    col_y,
                    max_width,
                    font,
                    text_color,
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
