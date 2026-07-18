from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .scenarios import Stage


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_frame(stage: Stage, sequence: int, scenario_name: str) -> bytes:
    width, height = 640, 480
    image = Image.new("RGB", (width, height), "#10171b")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        shade = int(16 + 20 * y / height)
        draw.line((0, y, width, y), fill=(shade, shade + 6, shade + 8))
    draw.rectangle((42, 74, 598, 432), fill="#1d292d", outline="#37484d", width=2)
    draw.rectangle((74, 294, 348, 408), fill="#263235", outline="#47575a", width=2)
    draw.ellipse((122, 318, 286, 370), fill="#111719", outline="#5b696b", width=3)
    draw.rectangle((410, 244, 548, 410), fill="#20292b", outline="#48585b", width=2)

    if scenario_name == "hard_negative" and stage.fire > 0:
        draw.rectangle((155, 205, 318, 260), fill="#d64b20")
        draw.ellipse((350, 150, 500, 300), fill="#e57026")

    if stage.smoke >= 0.55:
        haze = Image.new("RGBA", image.size, (0, 0, 0, 0))
        haze_draw = ImageDraw.Draw(haze)
        for index in range(8):
            offset = index * 16
            haze_draw.ellipse(
                (180 + offset, 85 - offset // 2, 390 + offset, 250 + offset // 2),
                fill=(150, 164, 159, 20 + index * 3),
            )
        haze = haze.filter(ImageFilter.GaussianBlur(18))
        image = Image.alpha_composite(image.convert("RGBA"), haze).convert("RGB")
        draw = ImageDraw.Draw(image)

    if stage.fire >= 0.55:
        scale = stage.area_scale
        cx, bottom = 238, 358
        flame_w, flame_h = int(74 * scale), int(116 * scale)
        flame = [
            (cx, bottom - flame_h),
            (cx + flame_w // 2, bottom - flame_h // 3),
            (cx + flame_w // 3, bottom),
            (cx - flame_w // 3, bottom),
            (cx - flame_w // 2, bottom - flame_h // 3),
        ]
        draw.polygon(flame, fill="#ff6b1a")
        inner = [(cx, bottom - flame_h * 3 // 5), (cx + 18, bottom), (cx - 18, bottom)]
        draw.polygon(inner, fill="#ffd166")

    draw.rounded_rectangle((20, 18, 620, 58), radius=10, fill="#0a0f11", outline="#38484c")
    draw.text(
        (36, 30),
        f"IGNIS REPLAY · {scenario_name.upper()} · FRAME {sequence:05d}",
        fill="#d7e3df",
        font=_font(18),
    )
    draw.text((48, 443), "SIMULATED CAMERA FEED — NOT QNX HARDWARE", fill="#9fb1ad", font=_font(14))
    output = BytesIO()
    image.save(output, "JPEG", quality=78, optimize=True)
    return output.getvalue()
