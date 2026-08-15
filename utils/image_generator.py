import pathlib
from io import BytesIO
import typing

import discord
from PIL import Image, ImageDraw, ImageFont

from config import LOGGER
from utils.number_utils import format_number
from utils.rngdle import (
    Tier,
    format_percent,
    format_tier,
    get_score_percent,
    get_score_tier,
    get_tier_color,
)

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
    percent: float
    percent_text: str
    tier_color: ColorType

    column_headers = ["Tirage", "Score", "Placement"]
    column_x_offsets = [500, 650, 810]
    # Can add an extra width to be used as a margin spacer on the right of the image
    column_max_widths = [140, 130, 180, 20]

    def get_column_values(self) -> list[str]:
        return [self.tirage, self.score, self.percent_text]

    @classmethod
    def create_user_instance(cls, user: discord.User, score: int, number: int, rank: int):
        new_user = cls()
        new_user.user = user
        new_user.score = format_number(score)
        new_user.tirage = f"{number:,}".replace(",", " ")
        new_user.rank = rank
        new_user.tier = get_score_tier(score)
        new_user.tier_text = format_tier(new_user.tier)
        new_user.percent = get_score_percent(score)
        new_user.percent_text = format_percent(new_user.percent)
        new_user.tier_color = get_tier_color(new_user.tier)
        return new_user


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

    # Slightly lighter header background
    BG_COLOR: ColorType = (25, 25, 25)  # Dark background
    TEXT_COLOR: ColorType = (255, 255, 255)  # White text

    HEADER_BG_COLOR: ColorType = (50, 50, 50)
    ROW_EVEN_COLOR: ColorType = (35, 35, 35)  # Even row background
    ROW_ODD_COLOR: ColorType = (45, 45, 45)  # Odd row background
    HIGHLIGHT_COLOR: ColorType = (0, 100, 200)  # For "async" button

    def __init__(self):
        self.font_path: pathlib.Path | None = None
        self.base_path: pathlib.Path = pathlib.Path(__file__).parent.resolve() / ".." / "ressources"

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

        self._ARROW_UP = Image.open(self.base_path / "rngdle" / "arrow_up.png").resize((40, 40))

        self._TRASH = (
            Image.open(self.base_path / "rngdle" / "trash.png").convert("RGBA").resize((40, 40))
        )

        self.ARROW_UP_EVEN = self._color_transparent_background(self._ARROW_UP, self.ROW_EVEN_COLOR)
        self.ARROW_UP_ODD = self._color_transparent_background(self._ARROW_UP, self.ROW_ODD_COLOR)
        self.TRASH_EVEN = self._color_transparent_background(self._TRASH, self.ROW_EVEN_COLOR)
        self.TRASH_ODD = self._color_transparent_background(self._TRASH, self.ROW_ODD_COLOR)

        try:
            self.font_path = self.base_path / "font" / "outfit.ttf"
            self.font_header = ImageFont.truetype(self.font_path, 40)
            self.font_regular = ImageFont.truetype(self.font_path, 30)
            self.font_small = ImageFont.truetype(self.font_path, 24)

            self.font_mono_path = self.base_path / "font" / "spacemono_bold.ttf"
            self.font_mono_regular = ImageFont.truetype(self.font_mono_path, 30)
        except IOError:
            LOGGER.warning("Warning: Could not load specified font. Using Pillow's default font.")
            self.font_path = None
            self.font_header = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

            self.font_mono_regular = ImageFont.load_default()

    def _color_transparent_background(self, base_image: Image.Image, new_background: ColorType):
        channels = [img.getdata() for img in base_image.split()]

        new_data: list[ColorType] = []
        for r, g, b, a in zip(*channels):
            if a == 0:
                r, g, b = new_background
            new_data.append((r, g, b))

        new_image = base_image.convert("RGB")
        new_image.putdata(new_data)
        return new_image

    def _get_fitted_text_font(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        max_width: float,
        base_font: FontType,
    ):
        if self.font_path is None:
            return base_font
        font = base_font
        font_path = getattr(font, "path", self.font_path)
        font_size = getattr(font, "size", 30)  # 30 is regular font size
        while draw.textlength(text, font=font) > max_width and font_size > 1:
            font_size -= 1
            font = ImageFont.truetype(font_path, font_size)
        return font

    def _get_fittex_text_length(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        max_width: float,
        base_font: FontType,
    ):
        font = self._get_fitted_text_font(draw, text, max_width, base_font)
        return draw.textlength(text, font=font)

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
        anchor: str = "rt",
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
            has_spacer = len(model.column_x_offsets) != len(model.column_max_widths)
            last_width = model.column_max_widths[-2] if has_spacer else model.column_max_widths[-1]
            spacer_width = model.column_max_widths[-1] if has_spacer else 0
            total_width = last_start_pos + last_width + spacer_width

            min_possible_width = max(min_possible_width, total_width)

        img = Image.new("RGB", (min_possible_width, total_height), self.BG_COLOR)
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
            row_color = self.ROW_EVEN_COLOR if (user.rank - 1) % 2 == 0 else self.ROW_ODD_COLOR
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
                self.create_avatar_mask(avatar_img, avatar_size, avatar_x, avatar_y, img)
            except Exception:
                default_avatar = Image.new("RGBA", (avatar_size, avatar_size), (120, 120, 120, 255))
                self.create_avatar_mask(default_avatar, avatar_size, avatar_x, avatar_y, img)

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

            for col_idx, col_text in enumerate(user.get_column_values()):
                col_x = model.column_x_offsets[col_idx]
                col_y = y_pos + (self.ROW_HEIGHT / 2) - 15
                max_width = model.column_max_widths[col_idx]

                font = self.font_regular
                text_color = self.TEXT_COLOR

                draw_func = self._draw_fitted

                if model == RNGdleLeaderboardUser:
                    draw_func = self._draw_fitted_align_right
                    user = typing.cast(RNGdleLeaderboardUser, user)

                    if user.column_headers[col_idx] == "Tirage":  # RNGdle draw
                        # Left pad the number string to be at least 7 chars long for even rendering
                        col_text = f"{col_text:>7}"
                        font = self.font_mono_regular
                        text_color = user.tier_color
                    elif user.column_headers[col_idx] == "Rareté":
                        text_color = user.tier_color
                    elif user.column_headers[col_idx] == "Placement":
                        text_color = user.tier_color

                        if user.percent > 50:
                            arrow_img = self.ARROW_UP_EVEN if user.rank % 2 else self.ARROW_UP_ODD
                        else:
                            arrow_img = self.TRASH_EVEN if user.rank % 2 else self.TRASH_ODD

                        text_length = self._get_fittex_text_length(draw, col_text, max_width, font)
                        text_x_right = col_x + max_width
                        text_x_left = text_x_right - text_length
                        arrow_x_right = text_x_left - 10
                        arrow_x_left = int(arrow_x_right - arrow_img.width)
                        arrow_y_top = int(col_y - 10)
                        draw._image.paste(arrow_img, (arrow_x_left, arrow_y_top))

                draw_func(
                    draw,
                    col_text,
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


class ProfileGenerator:
    WIDTH: int = 800
    HEIGHT: int = 610
    HEADER_HEIGHT: int = 150

    BG_COLOR: ColorType = (25, 25, 25)
    TEXT_COLOR: ColorType = (255, 255, 255)
    HEADER_BG_COLOR: ColorType = (50, 50, 50)
    BOX_COLOR: ColorType = (35, 35, 35)
    TITLE_COLOR: ColorType = (200, 200, 200)
    SUBTEXT_COLOR: ColorType = (170, 170, 170)

    def __init__(self):
        self.base_path: pathlib.Path = pathlib.Path(__file__).parent.resolve() / ".." / "ressources"
        self._load_fonts()
        self._load_images()

    def _load_fonts(self):
        font_file = self.base_path / "font" / "outfit.ttf"
        try:
            self.font_title = ImageFont.truetype(str(font_file), 50)
            self.font_large = ImageFont.truetype(str(font_file), 42)
            self.font_regular = ImageFont.truetype(str(font_file), 30)
            self.font_small = ImageFont.truetype(str(font_file), 22)
            self.font_tiny = ImageFont.truetype(str(font_file), 18)
            self.font_rank = ImageFont.truetype(str(font_file), 80)
        except IOError:
            self.font_title = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()
            self.font_rank = ImageFont.load_default()

    def _load_images(self):
        try:
            img_dir = self.base_path / "images"
            self.PODIUM_BRONZE = (
                Image.open(str(img_dir / "medal_bronze.png")).convert("RGBA").resize((93, 90))
            )
            self.PODIUM_SILVER = (
                Image.open(str(img_dir / "medal_silver.png")).convert("RGBA").resize((93, 90))
            )
            self.PODIUM_GOLD = (
                Image.open(str(img_dir / "medal_gold.png")).convert("RGBA").resize((90, 90))
            )
        except Exception:
            self.PODIUM_BRONZE = None
            self.PODIUM_SILVER = None
            self.PODIUM_GOLD = None

    async def generate_profile(self, user: discord.User, username: str, stats: dict):
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, self.WIDTH, self.HEADER_HEIGHT], fill=self.HEADER_BG_COLOR)

        avatar_x, avatar_y, avatar_size = 40, 25, 100
        try:
            if user:
                avatar_data = await user.avatar.read()
                avatar_img = (
                    Image.open(BytesIO(avatar_data))
                    .resize((avatar_size, avatar_size))
                    .convert("RGBA")
                )
            else:
                raise Exception()
            self.create_avatar_mask(avatar_img, avatar_size, avatar_x, avatar_y, img)
        except Exception:
            default_avatar = Image.new("RGBA", (avatar_size, avatar_size), (120, 120, 120, 255))
            self.create_avatar_mask(default_avatar, avatar_size, avatar_x, avatar_y, img)

        draw.text((170, 35), username, fill=self.TEXT_COLOR, font=self.font_title)

        rank = stats.get("server_rank", 0)
        if rank > 0:
            if rank == 1 and self.PODIUM_GOLD:
                img.paste(self.PODIUM_GOLD, (670, 30), self.PODIUM_GOLD)
            elif rank == 2 and self.PODIUM_SILVER:
                img.paste(self.PODIUM_SILVER, (667, 30), self.PODIUM_SILVER)
            elif rank == 3 and self.PODIUM_BRONZE:
                img.paste(self.PODIUM_BRONZE, (667, 30), self.PODIUM_BRONZE)
            else:
                rank_str = f"#{rank}"
                rank_width = draw.textlength(rank_str, font=self.font_rank)
                draw.text(
                    (760 - rank_width, 25),
                    rank_str,
                    fill=(150, 150, 150),
                    font=self.font_rank,
                )

        best_roll_y = 180
        tier = get_score_tier(stats["highest_score"])
        rarity_color = get_tier_color(tier)

        draw.rounded_rectangle(
            [40, best_roll_y, 760, best_roll_y + 130],
            radius=15,
            fill=self.BOX_COLOR,
            outline=rarity_color,
            width=2,
        )

        lucky_seed_str = f"{stats['lucky_seed']:,}".replace(",", " ")
        score_str = f"({stats['highest_score']:,} EP)".replace(",", " ")

        draw.text(
            (65, best_roll_y + 15),
            "BEST ROLL",
            fill=rarity_color,
            font=self.font_small,
        )
        draw.text(
            (65, best_roll_y + 50),
            lucky_seed_str,
            fill=rarity_color,
            font=self.font_large,
        )

        seed_width = draw.textlength(lucky_seed_str + " ", font=self.font_large)
        draw.text(
            (65 + seed_width, best_roll_y + 50),
            score_str,
            fill=(215, 215, 215),
            font=self.font_large,
        )

        date_str = f"Date : {stats['highest_date']}"
        date_width = draw.textlength(date_str, font=self.font_small)
        draw.text(
            (735 - date_width, best_roll_y + 60),
            date_str,
            fill=self.SUBTEXT_COLOR,
            font=self.font_small,
        )

        def draw_stat_box(
            x,
            y,
            title,
            value,
            subtext=None,
            value_font=None,
            outline_color=None,
            value_color=None,
        ):
            if value_font is None:
                value_font = self.font_regular
            if value_color is None:
                value_color = self.TEXT_COLOR

            if outline_color:
                draw.rounded_rectangle(
                    [x, y, x + 350, y + 110],
                    radius=12,
                    fill=self.BOX_COLOR,
                    outline=outline_color,
                    width=2,
                )
            else:
                draw.rounded_rectangle([x, y, x + 350, y + 110], radius=12, fill=self.BOX_COLOR)

            draw.text(
                (x + 20, y + 15),
                title,
                fill=self.TITLE_COLOR,
                font=self.font_small,
            )
            y_offset = 48 if value_font == self.font_small else 45
            draw.text((x + 20, y + y_offset), value, fill=value_color, font=value_font)
            if subtext:
                draw.text(
                    (x + 20, y + 82),
                    subtext,
                    fill=self.SUBTEXT_COLOR,
                    font=self.font_tiny,
                )

        avg_score_str = f"{stats['avg_score']:,}".replace(",", " ") + " EP"
        overall_score_str = f"{stats['total_score_sum']:,}".replace(",", " ") + " EP"
        avg_tier = get_score_tier(stats["avg_score"])
        avg_color = get_tier_color(avg_tier)

        draw_stat_box(40, 340, "Total Rolls", str(stats["total_rolls"]))
        draw_stat_box(
            410,
            340,
            "Average Score",
            avg_score_str,
            outline_color=avg_color,
            value_color=avg_color,
        )
        draw_stat_box(40, 470, "Max Badges", f"{stats['max_badges']} badges at once")
        draw_stat_box(410, 470, "Overall Score", overall_score_str)

        return img

    @staticmethod
    def create_avatar_mask(avatar_img, avatar_size, avatar_x, avatar_y, img):
        mask = Image.new("L", (avatar_size * 4, avatar_size * 4), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar_size * 4, avatar_size * 4), fill=255)
        mask = mask.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        avatar_img.putalpha(mask)
        img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)
