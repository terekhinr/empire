#!/usr/bin/env python3
"""Build Telegram sticker (512) and custom emoji (100) packs from generated art."""

from __future__ import annotations

import os
import shutil
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC = Path("/root/.cursor/projects/root-projects-empire/assets")
OUT = Path("/root/projects/empire/telegram_emoji_pack")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

ITEMS = [
    {
        "key": "01_obstanovka_zamechatelnaya",
        "caption": "ОБСТАНОВКА\nЗАМЕЧАТЕЛЬНАЯ",
        "emoji": "😄",
    },
    {
        "key": "02_ty_ne_stalin",
        "caption": "ТЫ НЕ\nСТАЛИН",
        "emoji": "🙅",
    },
    {
        "key": "03_v_pitere_zhit_tvorit_lyubit",
        "caption": "В ПИТЕРЕ\nЖИТЬ ТВОРИТЬ\nЛЮБИТЬ",
        "emoji": "❤️",
    },
    {
        "key": "04_ya_tebe_takie_mesta_pokazhu",
        "caption": "Я ТЕБЕ ТАКИЕ\nМЕСТА ПОКАЖУ",
        "emoji": "🌲",
    },
    {
        "key": "05_gardemariny_govno",
        "caption": "ГАРДЕМАРИНЫ\n....АВНО!",
        "emoji": "🫡",
    },
    {
        "key": "06_sofya_aleshka_gena",
        "caption": "СОФЬЯ,\nАЛЕШКА,\nГЕНА",
        "emoji": "🎭",
    },
    {
        "key": "07_aleshka_kartoshka",
        "caption": "АЛЕШКА, АЛЕШКА!\nПОЙДЕМ КОПАТЬ\nКАРТОШКУ!",
        "emoji": "🥔",
    },
    {
        "key": "08_ah_seryozha_nasosy",
        "caption": "АХ, СЕРЁЖА!\nНЕ НУЖНЫ МНЕ\nНАСОСЫ!",
        "emoji": "🎤",
    },
    {
        "key": "09_ne_zabudem_ne_prostim",
        "caption": "НЕ ЗАБУДЕМ!\nНЕ ПРОСТИМ!",
        "emoji": "😐",
    },
    {
        "key": "10_v_kandaly_menya",
        "caption": "В КАНДАЛЫ\nМЕНЯ!",
        "emoji": "⛓️",
    },
    {
        "key": "11_gardemariny_luchshiy_film",
        "caption": "ГАРДЕМАРИНЫ —\nЛУЧШИЙ ФИЛЬМ!",
        "emoji": "🎬",
    },
    {
        "key": "12_gardemariny_luchshiy_radost",
        "caption": "ГАРДЕМАРИНЫ —\nЛУЧШИЙ ФИЛЬМ!",
        "emoji": "🤩",
    },
        {
        "key": "13_zhil_v_yaroslavle",
        "caption": "ЖИЛ Я ПОТОМ\nВ ЯРОСЛАВЛЕ,\nДАЖЕ В НОРИЛЬСКЕ\nБЫВАЛ",
        "emoji": "📍",
    },
    {
        "key": "14_belyy_plyvyot_parahod",
        "caption": "БЕЛЫЙ ПЛЫВЁТ\nПАРАХОД",
        "emoji": "🚢",
    },
    {
        "key": "15_ot_praskovi_petrovny",
        "caption": "ОТ ПРАСКОВЬИ\nПЕТРОВНЫ",
        "emoji": "🥕",
    },
    {
        "key": "16_spelye_yabloki",
        "caption": "СПЕЛЫЕ ЯВЛОКИ\nЗЕМЛЮ С ДЕРЕВА\nПАДАЮТ НА",
        "emoji": "🍎",
    },
    {
        "key": "17_vse_eto_pticy_utki",
        "caption": "Я ТЕБЕ РАССКАЖУ,\nПОТОМУ ЧТО ТЫ МНЕ,\nКАК РОДНОЙ\nВСЁ ЭТО ПТИЦЫ,\nЭТО ВСЁ УТКИ.",
        "emoji": "🦆",
    },
    {
        "key": "18_ya_vam_takie_mesta_pled",
        "caption": "Я ВАМ ТАКИЕ\nМЕСТА ПОКАЖУ\n(ПРИПОДНИМАЕТ ПЛЕД)",
        "emoji": "🛏️",
    },
    {
        "key": "19_tokar_2_razryada",
        "caption": "ТОКАРЬ\n2-ГО РАЗРЯДА",
        "emoji": "🤘",
    },
    {
        "key": "20_chto_ty_govorish",
        "caption": "ЧТО ТЫ\nГОВОРИШЬ!",
        "emoji": "😮",
    },
    {
        "key": "21_poderzhi_arbuz",
        "caption": "ПОДЕРЖИ\nАРБУЗ",
        "emoji": "🍉",
    },
    {
        "key": "22_konechno",
        "caption": "КОНЕЧНО...",
        "emoji": "🎣",
    },
]

STEMS = [
    "obstanovka",
    "stalin",
    "piter",
    "kuzmich",
    "gardemariny",
    "sofya",
    "kartoshka",
    "seryozha",
    "nezabudem",
    "kandaly",
    "luchshiy",
    "radost",
    "yaroslavl",
    "parahod",
    "morkov",
    "yabloki",
    "utki",
    "mesta_pled",
    "tokar",
    "chto_govorish",
    "arbuz",
    "konechno",
]

VARIANTS = [
    ("variant_1_foto", "v1_{stem}_photo.png", STEMS),
    ("variant_2_mult", "v2_{stem}_cartoon.png", STEMS),
    ("variant_3_vintazh", "v3_{stem}_vintage.png", STEMS),
]


def is_green_screen(rgb: np.ndarray) -> np.ndarray:
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    # Neon chroma green; olive uniforms stay (G not far above R).
    neon = (g > 150) & (g > r + 50) & (g > b + 50)
    neon |= (g > 200) & (r < 80) & (b < 80)
    return neon


def flood_from_border(candidate: np.ndarray) -> np.ndarray:
    h, w = candidate.shape
    out = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def try_seed(y: int, x: int) -> None:
        if candidate[y, x] and not out[y, x]:
            out[y, x] = True
            q.append((y, x))

    for x in range(w):
        try_seed(0, x)
        try_seed(h - 1, x)
    for y in range(h):
        try_seed(y, 0)
        try_seed(y, w - 1)

    while q:
        y, x = q.popleft()
        if y > 0 and candidate[y - 1, x] and not out[y - 1, x]:
            out[y - 1, x] = True
            q.append((y - 1, x))
        if y + 1 < h and candidate[y + 1, x] and not out[y + 1, x]:
            out[y + 1, x] = True
            q.append((y + 1, x))
        if x > 0 and candidate[y, x - 1] and not out[y, x - 1]:
            out[y, x - 1] = True
            q.append((y, x - 1))
        if x + 1 < w and candidate[y, x + 1] and not out[y, x + 1]:
            out[y, x + 1] = True
            q.append((y, x + 1))
    return out


def cutout(im: Image.Image) -> Image.Image:
    rgb = np.array(im.convert("RGB"))
    h, w = rgb.shape[:2]
    bg = flood_from_border(is_green_screen(rgb))

    alpha = np.where(bg, 0, 255).astype(np.uint8)
    # Soften the cut edge so leftover green fringe disappears.
    alpha_img = Image.fromarray(alpha, mode="L")
    alpha_img = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.2))
    alpha = np.array(alpha_img)
    alpha = np.where(bg, np.minimum(alpha, 40), np.maximum(alpha, 215))
    # Kill remaining neon-green pixels even if not connected (specks).
    leftover = is_green_screen(rgb) & (alpha > 0)
    alpha[leftover] = 0

    rgba = np.dstack([rgb, alpha])
    out = Image.fromarray(rgba, mode="RGBA")

    # Despill: pull green toward neighbor luminance on semi-transparent edge.
    px = np.array(out)
    edge = (px[:, :, 3] > 20) & (px[:, :, 3] < 250)
    g = px[:, :, 1].astype(np.int16)
    rb = ((px[:, :, 0].astype(np.int16) + px[:, :, 2].astype(np.int16)) // 2)
    spill = edge & (g > rb + 25)
    px[spill, 1] = rb[spill]
    return Image.fromarray(px, mode="RGBA")


def bbox_with_pad(im: Image.Image, pad: int = 12) -> Image.Image:
    alpha = im.split()[-1]
    box = alpha.getbbox()
    if not box:
        return im
    l, t, r, b = box
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(im.width, r + pad)
    b = min(im.height, b + pad)
    return im.crop((l, t, r, b))


def fit_into(im: Image.Image, box_w: int, box_h: int) -> Image.Image:
    im = im.copy()
    im.thumbnail((box_w, box_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    x = (box_w - im.width) // 2
    y = box_h - im.height  # sit on the bottom of the art box
    canvas.paste(im, (x, y), im)
    return canvas


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size)


def text_block_size(draw: ImageDraw.ImageDraw, lines: list[str], font: ImageFont.FreeTypeFont, spacing: int):
    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=0)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    w = max(widths) if widths else 0
    h = sum(heights) + spacing * (len(lines) - 1)
    return w, h, widths, heights


def draw_caption(canvas: Image.Image, caption: str, area: tuple[int, int, int, int]) -> None:
    draw = ImageDraw.Draw(canvas)
    lines = caption.split("\n")
    ax, ay, aw, ah = area
    size = 72
    font = load_font(size)
    spacing = 6
    while size >= 22:
        font = load_font(size)
        tw, th, _, _ = text_block_size(draw, lines, font, spacing)
        if tw <= aw - 8 and th <= ah - 4:
            break
        size -= 2
    tw, th, widths, heights = text_block_size(draw, lines, font, spacing)
    y = ay + (ah - th) // 2
    stroke = max(4, size // 10)
    for line, lw, lh in zip(lines, widths, heights):
        x = ax + (aw - lw) // 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke,
            stroke_fill=(20, 16, 12, 255),
            anchor="lt",
        )
        y += lh + spacing


def make_sticker(cut: Image.Image, caption: str) -> Image.Image:
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    lines = caption.count("\n") + 1
    if lines <= 2:
        text_h = 118
    elif lines == 3:
        text_h = 168
    elif lines == 4:
        text_h = 196
    else:
        text_h = 232
    art = fit_into(bbox_with_pad(cut, 8), 500, 512 - text_h - 10)
    canvas.paste(art, (6, 4), art)
    draw_caption(canvas, caption, (8, 512 - text_h, 496, text_h - 6))
    return canvas


def make_emoji(cut: Image.Image) -> Image.Image:
    art = bbox_with_pad(cut, 16)
    canvas = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    art.thumbnail((96, 96), Image.Resampling.LANCZOS)
    x = (100 - art.width) // 2
    y = (100 - art.height) // 2
    canvas.paste(art, (x, y), art)
    return canvas


def pngquant(path: Path, max_kb: int | None = None) -> None:
    tmp = path.with_suffix(".q.png")
    cmd = ["pngquant", "--force", "--quality=60-95", "--output", str(tmp), str(path)]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        if tmp.exists():
            shutil.move(str(tmp), str(path))
    except (subprocess.CalledProcessError, FileNotFoundError):
        if tmp.exists():
            tmp.unlink()
    if max_kb is not None and path.stat().st_size > max_kb * 1024:
        # Second pass, more aggressive.
        cmd = ["pngquant", "--force", "--quality=40-80", "--speed=1", "--output", str(tmp), str(path)]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            if tmp.exists():
                shutil.move(str(tmp), str(path))
        except subprocess.CalledProcessError:
            if tmp.exists():
                tmp.unlink()


def checkerboard(size: int = 512, cell: int = 16) -> Image.Image:
    im = Image.new("RGB", (size, size), (220, 220, 220))
    d = ImageDraw.Draw(im)
    for y in range(0, size, cell):
        for x in range(0, size, cell):
            if ((x // cell) + (y // cell)) % 2 == 0:
                d.rectangle([x, y, x + cell, y + cell], fill=(190, 190, 190))
    return im


def main() -> None:
    preview_cells: list[Image.Image] = []
    manifest: list[str] = []

    for folder, tmpl, stems in VARIANTS:
        sticker_dir = OUT / folder / "stickers_512"
        emoji_dir = OUT / folder / "emoji_100"
        sticker_dir.mkdir(parents=True, exist_ok=True)
        emoji_dir.mkdir(parents=True, exist_ok=True)

        for item, stem in zip(ITEMS, stems):
            src = SRC / tmpl.format(stem=stem)
            if not src.exists():
                raise SystemExit(f"missing {src}")
            cut = cutout(Image.open(src))
            sticker = make_sticker(cut, item["caption"])
            emoji = make_emoji(cut)

            sp = sticker_dir / f"{item['key']}.png"
            ep = emoji_dir / f"{item['key']}.png"
            sticker.save(sp, "PNG", optimize=True)
            emoji.save(ep, "PNG", optimize=True)
            # Stickers stay RGBA for quality (Telegram allows up to 512 KB).
            # Custom emoji must stay small; quantize those only.
            pngquant(ep, max_kb=60)

            prev = checkerboard(512)
            prev.paste(sticker, (0, 0), sticker)
            preview_cells.append(prev)

            s_kb = sp.stat().st_size / 1024
            e_kb = ep.stat().st_size / 1024
            line = f"{folder}/{item['key']}: sticker {s_kb:.1f}KB  emoji {e_kb:.1f}KB  map {item['emoji']}"
            print(line)
            manifest.append(line)

    cols = len(ITEMS)
    rows = len(VARIANTS)
    sheet = Image.new("RGB", (cols * 512 + 40, rows * 512 + 40), (32, 32, 32))
    for i, cell in enumerate(preview_cells):
        r, c = divmod(i, cols)
        sheet.paste(cell, (20 + c * 512, 20 + r * 512))
    preview_path = OUT / "_preview" / "all_stickers_512.png"
    sheet.save(preview_path, "PNG", optimize=True)
    print(f"preview -> {preview_path}")

    (OUT / "MANIFEST.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
