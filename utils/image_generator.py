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
    HEIGHT: int = 840
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
            LOGGER.warning("Warning: Could not load specified font for ProfileGenerator.")
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
        total_players = stats.get("total_players", 0)

        if rank > 0:
            total_str = f" / {total_players}"
            total_width = draw.textlength(total_str, font=self.font_regular)

            sub_y = 70
            icon_y = 15

            if rank == 1 and self.PODIUM_GOLD:
                img.paste(self.PODIUM_GOLD, (int(760 - total_width - 90), icon_y), self.PODIUM_GOLD)
                draw.text(
                    (760 - total_width, sub_y),
                    total_str,
                    fill=self.SUBTEXT_COLOR,
                    font=self.font_regular,
                )
            elif rank == 2 and self.PODIUM_SILVER:
                img.paste(
                    self.PODIUM_SILVER, (int(760 - total_width - 93), icon_y), self.PODIUM_SILVER
                )
                draw.text(
                    (760 - total_width, sub_y),
                    total_str,
                    fill=self.SUBTEXT_COLOR,
                    font=self.font_regular,
                )
            elif rank == 3 and self.PODIUM_BRONZE:
                img.paste(
                    self.PODIUM_BRONZE, (int(760 - total_width - 93), icon_y), self.PODIUM_BRONZE
                )
                draw.text(
                    (760 - total_width, sub_y),
                    total_str,
                    fill=self.SUBTEXT_COLOR,
                    font=self.font_regular,
                )
            else:
                rank_str = f"#{rank}"
                rank_width = draw.textlength(rank_str, font=self.font_rank)

                draw.text(
                    (760 - total_width - rank_width, 25),
                    rank_str,
                    fill=(150, 150, 150),
                    font=self.font_rank,
                )
                draw.text(
                    (760 - total_width, sub_y),
                    total_str,
                    fill=self.SUBTEXT_COLOR,
                    font=self.font_regular,
                )

        def draw_box(
            x,
            y,
            w,
            h,
            title,
            value,
            subtext=None,
            value_font=None,
            outline_color=None,
            value_color=None,
            score_suffix=None,
        ):
            if value_font is None:
                value_font = self.font_regular
            if value_color is None:
                value_color = self.TEXT_COLOR

            if outline_color:
                draw.rounded_rectangle(
                    [x, y, x + w, y + h],
                    radius=12,
                    fill=self.BOX_COLOR,
                    outline=outline_color,
                    width=2,
                )
            else:
                draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=self.BOX_COLOR)

            draw.text(
                (x + 20, y + 15),
                title,
                fill=self.TITLE_COLOR,
                font=self.font_small,
            )
            y_offset = 48 if value_font == self.font_small else 45
            draw.text((x + 20, y + y_offset), str(value), fill=value_color, font=value_font)

            if score_suffix:
                val_width = draw.textlength(str(value) + " ", font=value_font)
                draw.text(
                    (x + 20 + val_width, y + y_offset),
                    score_suffix,
                    fill=(215, 215, 215),
                    font=self.font_regular,
                )

            if subtext:
                draw.text(
                    (x + 20, y + 80),
                    subtext,
                    fill=self.SUBTEXT_COLOR,
                    font=self.font_tiny,
                )

        best_roll_y = 180

        best_tier = get_score_tier(stats["highest_score"])
        best_color = get_tier_color(best_tier)
        best_seed_str = f"{stats['lucky_seed']:,}".replace(",", " ")
        best_score_str = f"({stats['highest_score']:,} EP)".replace(",", " ")

        worst_tier = get_score_tier(stats["lowest_score"])
        worst_color = get_tier_color(worst_tier)
        worst_seed_str = f"{stats['unlucky_seed']:,}".replace(",", " ")
        worst_score_str = f"({stats['lowest_score']:,} EP)".replace(",", " ")

        draw_box(
            40,
            best_roll_y,
            345,
            110,
            "Best Roll",
            best_seed_str,
            subtext=f"Date : {stats['highest_date']}",
            value_color=best_color,
            outline_color=best_color,
            score_suffix=best_score_str,
        )

        draw_box(
            415,
            best_roll_y,
            345,
            110,
            "Worst Roll",
            worst_seed_str,
            subtext=f"Date : {stats['lowest_date']}",
            value_color=worst_color,
            outline_color=worst_color,
            score_suffix=worst_score_str,
        )

        avg_score_str = f"{stats['avg_score']:,}".replace(",", " ") + " EP"
        overall_score_str = f"{stats['total_score_sum']:,}".replace(",", " ") + " EP"
        avg_tier = get_score_tier(stats["avg_score"])
        avg_color = get_tier_color(avg_tier)

        draw_box(40, 310, 345, 110, "Total Rolls", str(stats["total_rolls"]))
        draw_box(
            415,
            310,
            345,
            110,
            "Average Score",
            avg_score_str,
            outline_color=avg_color,
            value_color=avg_color,
        )
        draw_box(40, 440, 345, 110, "Max Badges", f"{stats['max_badges']} badges at once")
        draw_box(415, 440, 345, 110, "Overall Score", overall_score_str)

        draw.rounded_rectangle([40, 570, 760, 810], radius=12, fill=self.BOX_COLOR)
        draw.text((60, 585), "Tier Breakdown", fill=self.TITLE_COLOR, font=self.font_small)

        tiers = ["MYTHIC", "ANOMALY", "EPIC", "RARE", "UNCOMMON", "COMMON", "TRASH"]
        col_x = [80, 440]
        start_y = 630

        for i, tier_name in enumerate(tiers):
            count = stats["rarities"].get(tier_name, 0)
            color = get_tier_color(Tier[tier_name])

            col_index = 0 if i < 4 else 1
            row_index = i if i < 4 else i - 4

            x_pos = col_x[col_index]
            y_pos = start_y + (40 * row_index)

            draw.text((x_pos, y_pos), f"{tier_name}:", fill=color, font=self.font_small)

            count_str = f"{count:,}".replace(",", " ")
            count_width = draw.textlength(count_str, font=self.font_small)
            draw.text(
                (x_pos + 220 - count_width, y_pos),
                count_str,
                fill=self.TEXT_COLOR,
                font=self.font_small,
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


class ServerStatGenerator:
    WIDTH: int = 800
    HEIGHT: int = 710
    HEADER_HEIGHT: int = 150

    BG_COLOR = (25, 25, 25)
    TEXT_COLOR = (255, 255, 255)
    HEADER_BG_COLOR = (50, 50, 50)
    BOX_COLOR = (35, 35, 35)
    TITLE_COLOR = (200, 200, 200)
    SUBTEXT_COLOR = (170, 170, 170)

    def __init__(self):
        self.base_path = pathlib.Path(__file__).parent.resolve() / ".." / "ressources"
        self._load_fonts()

    def _load_fonts(self):
        font_file = self.base_path / "font" / "outfit.ttf"
        try:
            self.font_title = ImageFont.truetype(str(font_file), 45)
            self.font_large = ImageFont.truetype(str(font_file), 38)
            self.font_regular = ImageFont.truetype(str(font_file), 28)
            self.font_small = ImageFont.truetype(str(font_file), 22)
            self.font_tiny = ImageFont.truetype(str(font_file), 18)
        except IOError:
            self.font_title = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

    async def generate_server_stat(self, guild: discord.Guild, stats: dict):
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, self.WIDTH, self.HEADER_HEIGHT], fill=self.HEADER_BG_COLOR)

        icon_x, icon_y, icon_size = 40, 25, 100
        try:
            if guild.icon:
                icon_data = await guild.icon.read()
                icon_img = (
                    Image.open(BytesIO(icon_data)).resize((icon_size, icon_size)).convert("RGBA")
                )
            else:
                raise Exception()
            self.create_avatar_mask(icon_img, icon_size, icon_x, icon_y, img)
        except Exception:
            default_icon = Image.new("RGBA", (icon_size, icon_size), (120, 120, 120, 255))
            self.create_avatar_mask(default_icon, icon_size, icon_x, icon_y, img)

        draw.text((170, 45), "RNGdle - Server Stats", fill=self.TEXT_COLOR, font=self.font_title)

        async def fetch_avatar(member, size):
            if member:
                try:
                    data = await member.display_avatar.read()
                    return Image.open(BytesIO(data)).resize((size, size)).convert("RGBA")
                except:
                    pass
            return Image.new("RGBA", (size, size), (120, 120, 120, 255))

        best_avatar = await fetch_avatar(stats["best_roll"].get("member"), 32)
        worst_avatar = await fetch_avatar(stats["worst_roll"].get("member"), 32)

        tier_avatars = {}
        for t, members_list in stats.get("tier_members", {}).items():
            tier_avatars[t] = []
            for member in members_list:
                if member:
                    avatar = await fetch_avatar(member, 24)
                    tier_avatars[t].append(avatar)

        def draw_box(
            x,
            y,
            w,
            h,
            title,
            value,
            subtext=None,
            value_color=None,
            outline_color=None,
            score_suffix=None,
            avatar=None,
        ):
            if value_color is None:
                value_color = self.TEXT_COLOR

            if outline_color:
                draw.rounded_rectangle(
                    [x, y, x + w, y + h],
                    radius=12,
                    fill=self.BOX_COLOR,
                    outline=outline_color,
                    width=2,
                )
            else:
                draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=self.BOX_COLOR)

            draw.text((x + 20, y + 15), title, fill=self.TITLE_COLOR, font=self.font_small)

            if avatar:
                av_x = int(x + w - avatar.width - 15)
                av_y = int(y + 10)
                self.create_avatar_mask(avatar, avatar.width, av_x, av_y, img)

            draw.text((x + 20, y + 45), value, fill=value_color, font=self.font_regular)

            if score_suffix:
                val_width = draw.textlength(value + " ", font=self.font_regular)
                draw.text(
                    (x + 20 + val_width, y + 45),
                    score_suffix,
                    fill=(215, 215, 215),
                    font=self.font_regular,
                )

            if subtext:
                draw.text((x + 20, y + 80), subtext, fill=self.SUBTEXT_COLOR, font=self.font_tiny)

        best_color = get_tier_color(get_score_tier(stats["best_roll"]["score"]))
        worst_color = get_tier_color(get_score_tier(stats["worst_roll"]["score"]))

        best_number_str = f"{stats['best_roll']['number']:,}".replace(",", " ")
        best_score_str = f"({stats['best_roll']['score']:,} EP)".replace(",", " ")

        worst_number_str = f"{stats['worst_roll']['number']:,}".replace(",", " ")
        worst_score_str = f"({stats['worst_roll']['score']:,} EP)".replace(",", " ")

        draw_box(
            40,
            180,
            345,
            110,
            "Best Roll OAT",
            best_number_str,
            f"by {stats['best_roll']['user']}",
            value_color=best_color,
            outline_color=best_color,
            score_suffix=best_score_str,
            avatar=best_avatar,
        )
        draw_box(
            415,
            180,
            345,
            110,
            "Worst Roll OAT",
            worst_number_str,
            f"by {stats['worst_roll']['user']}",
            value_color=worst_color,
            outline_color=worst_color,
            score_suffix=worst_score_str,
            avatar=worst_avatar,
        )

        box_w = 226
        avg_color = get_tier_color(get_score_tier(stats["avg_score"]))

        draw_box(40, 310, box_w, 110, "Total Rolls", f"{stats['total_rolls']:,}".replace(",", " "))
        draw_box(
            286,
            310,
            box_w,
            110,
            "Average Score",
            f"{stats['avg_score']:,} EP".replace(",", " "),
            value_color=avg_color,
            outline_color=avg_color,
        )
        draw_box(
            532,
            310,
            box_w,
            110,
            "Overall Score",
            f"{stats['overall_score']:,} EP".replace(",", " "),
        )

        draw.rounded_rectangle([40, 440, 760, 680], radius=12, fill=self.BOX_COLOR)
        draw.text((60, 455), "Tier Breakdown", fill=self.TITLE_COLOR, font=self.font_small)

        tiers = ["MYTHIC", "ANOMALY", "EPIC", "RARE", "UNCOMMON", "COMMON", "TRASH"]
        col_x = [80, 440]
        start_y = 500

        for i, tier in enumerate(tiers):
            count = stats["rarities"].get(tier, 0)
            color = get_tier_color(Tier[tier])

            col_index = 0 if i < 4 else 1
            row_index = i if i < 4 else i - 4

            x_pos = col_x[col_index]
            y_pos = start_y + (45 * row_index)

            draw.text((x_pos, y_pos), f"{tier}:", fill=color, font=self.font_small)

            count_str = f"{count:,}".replace(",", " ")
            count_width = draw.textlength(count_str, font=self.font_small)
            draw.text(
                (x_pos + 220 - count_width, y_pos),
                count_str,
                fill=self.TEXT_COLOR,
                font=self.font_small,
            )

            if tier in tier_avatars:
                avatars_to_draw = tier_avatars[tier][:3]

                # We draw the list in reverse order so that #1 (index 0) is drawn last
                # and thus appears visually "on top" of the others
                for idx, avatar in reversed(list(enumerate(avatars_to_draw))):
                    # A 14-pixel difference for 24-pixel images results in a 10-pixel overlap
                    avatar_x = int(x_pos + 235 + (idx * 14))
                    avatar_y = int(y_pos - 1)

                    # Draw a dark gray circle (BOX_COLOR) behind the avatar to create
                    # a small border that "cuts off" the bottom of the avatar and separates them neatly
                    draw.ellipse(
                        [avatar_x - 2, avatar_y - 2, avatar_x + 24 + 2, avatar_y + 24 + 2],
                        fill=self.BOX_COLOR,
                    )

                    self.create_avatar_mask(avatar, 24, avatar_x, avatar_y, img)

        return img

    @staticmethod
    def create_avatar_mask(avatar_img, avatar_size, avatar_x, avatar_y, img):
        mask = Image.new("L", (avatar_size * 4, avatar_size * 4), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, avatar_size * 4, avatar_size * 4), fill=255)
        mask = mask.resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
        avatar_img.putalpha(mask)
        img.paste(avatar_img, (avatar_x, avatar_y), avatar_img)


class OverallLeaderboardGenerator:
    WIDTH: int = 800
    ROW_HEIGHT: int = 90
    HEADER_HEIGHT: int = 100

    BG_COLOR = (25, 25, 25)
    TEXT_COLOR = (255, 255, 255)
    HEADER_BG_COLOR = (50, 50, 50)
    ROW_EVEN_COLOR = (35, 35, 35)
    ROW_ODD_COLOR = (45, 45, 45)

    def __init__(self):
        self.base_path: pathlib.Path = pathlib.Path(__file__).parent.resolve() / ".." / "ressources"
        self._load_fonts()
        self._load_images()

    def _load_fonts(self):
        font_file = self.base_path / "font" / "outfit.ttf"
        try:
            self.font_header = ImageFont.truetype(str(font_file), 40)
            self.font_regular = ImageFont.truetype(str(font_file), 30)
        except IOError:
            self.font_header = ImageFont.load_default()
            self.font_regular = ImageFont.load_default()

    def _load_images(self):
        try:
            img_dir = self.base_path / "images"
            self.PODIUM_BRONZE = (
                Image.open(str(img_dir / "medal_bronze.png")).convert("RGBA").resize((50, 50))
            )
            self.PODIUM_SILVER = (
                Image.open(str(img_dir / "medal_silver.png")).convert("RGBA").resize((50, 50))
            )
            self.PODIUM_GOLD = (
                Image.open(str(img_dir / "medal_gold.png")).convert("RGBA").resize((50, 50))
            )
        except Exception:
            self.PODIUM_BRONZE = None
            self.PODIUM_SILVER = None
            self.PODIUM_GOLD = None

    @staticmethod
    def format_short_number(num: int) -> str:
        if num >= 1_000_000_000:
            formatted = f"{num / 1_000_000_000:.1f}"
            return f"{formatted.replace('.0', '')}Md"
        elif num >= 1_000_000:
            formatted = f"{num / 1_000_000:.1f}"
            return f"{formatted.replace('.0', '')}M"
        elif num >= 1_000:
            formatted = f"{num / 1_000:.1f}"
            return f"{formatted.replace('.0', '')}k"
        else:
            return str(num)

    def _draw_fitted(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: float,
        y: float,
        max_width: float,
        base_font,
        fill,
        anchor="lt",
    ):
        font = base_font
        font_path = getattr(font, "path", None)
        font_size = getattr(font, "size", 30)

        if font_path:
            while draw.textlength(text, font=font) > max_width and font_size > 1:
                font_size -= 1
                font = ImageFont.truetype(font_path, font_size)

        draw.text((x, y), text, fill=fill, font=font, anchor=anchor)

    async def _draw_user_row(self, draw, img, data, rank, y_pos, row_color):
        draw.rectangle([0, y_pos, self.WIDTH, y_pos + self.ROW_HEIGHT], fill=row_color)

        rank_text_x = 30
        rank_text_y = y_pos + (self.ROW_HEIGHT / 2) - 15

        if rank == 1 and self.PODIUM_GOLD:
            img.paste(self.PODIUM_GOLD, (rank_text_x - 15, int(rank_text_y - 10)), self.PODIUM_GOLD)
        elif rank == 2 and self.PODIUM_SILVER:
            img.paste(
                self.PODIUM_SILVER, (rank_text_x - 15, int(rank_text_y - 10)), self.PODIUM_SILVER
            )
        elif rank == 3 and self.PODIUM_BRONZE:
            img.paste(
                self.PODIUM_BRONZE, (rank_text_x - 15, int(rank_text_y - 10)), self.PODIUM_BRONZE
            )
        else:
            draw.text(
                (rank_text_x, rank_text_y), str(rank), fill=self.TEXT_COLOR, font=self.font_regular
            )

        avatar_x = 100
        avatar_y = y_pos + 15
        avatar_size = 60

        try:
            if data["discord_user"]:
                avatar_data = await data["discord_user"].display_avatar.read()
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

        username_x = 190
        username_y = y_pos + (self.ROW_HEIGHT / 2) - 15
        display_name = (
            data["discord_user"].name if data["discord_user"] else data["rngdle_username"]
        )
        self._draw_fitted(
            draw, display_name, username_x, username_y, 320, self.font_regular, self.TEXT_COLOR
        )

        short_score = self.format_short_number(data["total_score"])
        score_str = f"{short_score} EP"

        score_x = 770
        score_y = y_pos + (self.ROW_HEIGHT / 2) - 15
        self._draw_fitted(
            draw, score_str, score_x, score_y, 250, self.font_regular, (251, 251, 251), anchor="rt"
        )

    async def generate_leaderboard(
        self, users_data: list[dict], start_rank: int = 1, caller_info: dict = None
    ):
        GAP = 20
        base_rows = len(users_data)
        total_height = self.HEADER_HEIGHT + (base_rows * self.ROW_HEIGHT)

        if caller_info:
            total_height += self.ROW_HEIGHT + GAP

        img = Image.new("RGB", (self.WIDTH, total_height), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, self.WIDTH, self.HEADER_HEIGHT], fill=self.HEADER_BG_COLOR)

        headers = ["Rang", "Pseudo", "Overall Score"]
        x_offsets = [15, 190, 770]
        anchors = ["lt", "lt", "rt"]

        for i, header in enumerate(headers):
            x, y = x_offsets[i], self.HEADER_HEIGHT / 2 - 15
            draw.text(
                (x, y), header, fill=self.TEXT_COLOR, font=self.font_regular, anchor=anchors[i]
            )

        for index, data in enumerate(users_data):
            y_pos = self.HEADER_HEIGHT + (index * self.ROW_HEIGHT)
            row_color = self.ROW_EVEN_COLOR if index % 2 == 0 else self.ROW_ODD_COLOR
            await self._draw_user_row(draw, img, data, start_rank + index, y_pos, row_color)

        if caller_info:
            base_y = self.HEADER_HEIGHT + (base_rows * self.ROW_HEIGHT)
            line_y = base_y + (GAP // 2)

            draw.line([(0, line_y), (self.WIDTH, line_y)], fill=(80, 80, 80), width=2)

            caller_y = base_y + GAP
            await self._draw_user_row(
                draw, img, caller_info["data"], caller_info["rank"], caller_y, self.ROW_EVEN_COLOR
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
