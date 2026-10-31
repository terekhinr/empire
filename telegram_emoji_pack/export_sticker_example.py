#!/usr/bin/env python3
"""Re-export stickers with white stroke + drop shadow, matching StickerExample.psd."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path("/root/projects/empire/telegram_emoji_pack")
VARIANTS = ["variant_1_foto", "variant_2_mult", "variant_3_vintazh"]


def apply_sticker_example(
    im: Image.Image,
    canvas: int = 512,
    stroke: int = 6,
    sh_off: tuple[int, int] = (4, 6),
    sh_blur: int = 7,
    sh_a: int = 100,
) -> Image.Image:
    src = im.convert("RGBA")
    bbox = src.split()[-1].getbbox()
    if bbox:
        src = src.crop(bbox)
    alpha = src.split()[-1]
    hard = alpha.point(lambda p: 255 if p > 16 else 0)

    stroke_mask = hard
    for _ in range(stroke):
        stroke_mask = stroke_mask.filter(ImageFilter.MaxFilter(3))

    pad = stroke + sh_blur + max(sh_off) + 12
    w, h = src.size
    cw, ch = w + pad * 2, h + pad * 2

    white_layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    white = Image.new("RGBA", (cw, ch), (255, 255, 255, 255))
    sm = Image.new("L", (cw, ch), 0)
    sm.paste(stroke_mask, (pad, pad))
    white_layer.paste(white, mask=sm)

    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    black = Image.new("RGBA", (cw, ch), (0, 0, 0, sh_a))
    shmask = sm.filter(ImageFilter.GaussianBlur(sh_blur))
    shadow.paste(black, mask=shmask)

    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out.alpha_composite(shadow, dest=sh_off)
    out.alpha_composite(white_layer)
    body = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    body.paste(src, (pad, pad), src)
    out.alpha_composite(body)

    bb = out.split()[-1].getbbox()
    if bb:
        out = out.crop(bb)

    margin = 8
    out.thumbnail((canvas - margin * 2, canvas - margin * 2), Image.Resampling.LANCZOS)
    canvas_im = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    x = (canvas - out.width) // 2
    y = (canvas - out.height) // 2
    canvas_im.paste(out, (x, y), out)
    return canvas_im


def main() -> None:
    preview_cells: list[Image.Image] = []
    n = 0
    for variant in VARIANTS:
        src_dir = ROOT / variant / "stickers_512"
        dst_dir = ROOT / variant / "export_png"
        dst_dir.mkdir(parents=True, exist_ok=True)
        for src in sorted(src_dir.glob("*.png")):
            styled = apply_sticker_example(Image.open(src))
            out = dst_dir / src.name
            styled.save(out, "PNG", optimize=True)
            kb = out.stat().st_size / 1024
            if kb > 500:
                # Telegram static sticker limit is 512 KB.
                styled.save(out, "PNG", optimize=True, compress_level=9)
                kb = out.stat().st_size / 1024
            print(f"{variant}/{src.name}: {kb:.1f}KB")
            n += 1
            chk = Image.new("RGB", (512, 512), (230, 230, 230))
            chk.paste(styled, mask=styled.split()[-1])
            preview_cells.append(chk)

    cols = 22
    rows = 3
    sheet = Image.new("RGB", (cols * 256 + 20, rows * 256 + 20), (40, 40, 40))
    for i, cell in enumerate(preview_cells):
        r, c = divmod(i, cols)
        sheet.paste(cell.resize((256, 256), Image.Resampling.LANCZOS), (10 + c * 256, 10 + r * 256))
    preview = ROOT / "_preview" / "export_png_all.png"
    sheet.save(preview, "PNG", optimize=True)
    print(f"exported {n} files; preview {preview}")


if __name__ == "__main__":
    main()
