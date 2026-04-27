"""Pillow rendering engine — one AI background, smart crops per slide."""

import math
import os
import random
from PIL import Image, ImageFilter, ImageDraw, ImageFont

PLATFORM_SIZES = {"tiktok": (1080, 1920), "insta": (1080, 1350)}

FONT_DIRS = [
    os.path.join(os.path.dirname(__file__), "fonts"),
    "/System/Library/Fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
]

PREFERRED_BOLD = ["Inter-Bold.ttf", "Montserrat-Bold.ttf", "Helvetica.ttc", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
PREFERRED_REG  = ["Inter-Regular.ttf", "Montserrat-Regular.ttf", "Helvetica.ttc", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]


def _find_font(names, size: int) -> ImageFont.FreeTypeFont:
    for name in names:
        for d in FONT_DIRS:
            path = os.path.join(d, name)
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def _hex_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _round_image(img: Image.Image) -> Image.Image:
    """Crop to square, then apply a circular alpha mask."""
    s = min(img.size)
    img = img.crop(((img.width - s) // 2, (img.height - s) // 2,
                    (img.width + s) // 2, (img.height + s) // 2)).convert("RGBA")
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
    img.putalpha(mask)
    return img


def _draw_stars(draw: ImageDraw.ImageDraw, cx: int, cy: int, star_r: int, n: int, gap: int, color: tuple):
    """Draw n filled 5-pointed stars in a horizontal row centred on cx, cy."""
    total_w = n * star_r * 2 + (n - 1) * gap
    x0 = cx - total_w // 2 + star_r
    for i in range(n):
        sx = x0 + i * (star_r * 2 + gap)
        outer, inner = star_r, int(star_r * 0.42)
        pts = []
        for j in range(10):
            angle = math.pi / 5 * j - math.pi / 2
            r = outer if j % 2 == 0 else inner
            pts.append((sx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(pts, fill=color)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_px: int) -> str:
    words, lines, current = text.split(), [], []
    for word in words:
        test = " ".join(current + [word])
        if draw.textbbox((0, 0), test, font=font)[2] > max_px and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def _draw_centered_lines(draw, text: str, font, y: int, w: int, fill: tuple, line_gap: int = 6) -> int:
    """Draw multi-line centred text, returns y after last line."""
    for line in text.split("\n"):
        lb = draw.textbbox((0, 0), line, font=font)
        lw = lb[2] - lb[0]
        lh = lb[3] - lb[1]
        draw.text(((w - lw) // 2, y), line, font=font, fill=fill)
        y += lh + line_gap
    return y


def _make_slide_bg(base: Image.Image, slide_idx: int, target_w: int, target_h: int) -> Image.Image:
    """Deterministic crop + transform + blur of base image per slide index."""
    rng = random.Random(slide_idx)
    zoom = rng.uniform(0.80, 0.92)
    crop_w = int(base.width * zoom)
    crop_h = int(base.height * zoom)
    x = int(rng.uniform(0, max(0, base.width - crop_w)))
    y = int(rng.uniform(0, max(0, base.height - crop_h)))
    frame = base.crop((x, y, x + crop_w, y + crop_h))
    if rng.random() > 0.5:
        frame = frame.transpose(Image.FLIP_LEFT_RIGHT)
    angle = rng.uniform(-4, 4)
    if abs(angle) > 0.5:
        frame = frame.rotate(angle, resample=Image.BICUBIC, expand=False)
    frame = frame.resize((target_w, target_h), Image.LANCZOS)
    return frame.filter(ImageFilter.GaussianBlur(radius=rng.uniform(10, 20)))


def _load_logo(path: str, size: int, fallback_color: tuple) -> Image.Image:
    if os.path.exists(path):
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size), Image.LANCZOS)
            return _round_image(img)
        except Exception:
            pass
    # Placeholder circle
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=(*fallback_color, 220))
    font = _find_font(PREFERRED_BOLD, max(10, size // 3))
    d.text((size // 2, size // 2), "A", font=font, fill=(255, 255, 255, 255), anchor="mm")
    return img


# ──────────────────────────────────────────────
#  REGULAR SLIDE
# ──────────────────────────────────────────────

def render_slide(base_image, copy, profile, platform, slide_index, total_slides):
    w, h = PLATFORM_SIZES[platform]
    scale = h / 1920

    canvas = _make_slide_bg(base_image, slide_index, w, h).convert("RGBA")

    # Glassmorphism footer — bottom 20%, strong white panel
    footer_h = int(h * 0.20)
    footer_y = h - footer_h
    margin = int(60 * scale)

    glass = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glass_draw = ImageDraw.Draw(glass)
    fade_px = 80
    for i in range(fade_px):
        alpha = int(220 * (i / fade_px))
        glass_draw.line([(0, footer_y - fade_px + i), (w, footer_y - fade_px + i)], fill=(255, 255, 255, alpha))
    glass_draw.rectangle([0, footer_y, w, h], fill=(255, 255, 255, 220))
    canvas = Image.alpha_composite(canvas, glass)
    draw = ImageDraw.Draw(canvas)

    headline_pt = max(42, int(90 * scale))
    body_pt     = max(20, int(45 * scale))
    headline_font = _find_font(PREFERRED_BOLD, headline_pt)
    body_font     = _find_font(PREFERRED_REG, body_pt)

    footer_rgb = _hex_rgb(profile["footer_text_color"])
    max_text_w = w - 2 * margin
    pad = int(18 * scale)

    headline_text = _wrap(draw, copy.get("headline", ""), headline_font, max_text_w)
    body_text     = _wrap(draw, copy.get("body", ""), body_font, max_text_w)

    hl_y = footer_y + pad
    shadow_off = max(2, int(3 * scale))
    draw.text((margin + shadow_off, hl_y + shadow_off), headline_text, font=headline_font, fill=(0, 0, 0, 40))
    draw.text((margin, hl_y), headline_text, font=headline_font, fill=(*footer_rgb, 255))

    hl_bbox = draw.multiline_textbbox((margin, hl_y), headline_text, font=headline_font)
    draw.text((margin, hl_bbox[3] + pad), body_text, font=body_font, fill=(*footer_rgb, 210))

    # Logo — top left
    logo_size = int(80 * scale)
    logo_pad  = int(40 * scale)
    logo = _load_logo(profile["logo_path"], logo_size, _hex_rgb(profile["accent_color"]))
    canvas.paste(logo, (logo_pad, logo_pad), logo)

    # Slide counter — top centre
    counter_font = _find_font(PREFERRED_REG, max(14, int(26 * scale)))
    counter = f"{slide_index + 1} / {total_slides}"
    cb = draw.textbbox((0, 0), counter, font=counter_font)
    draw.text(((w - cb[2]) // 2, logo_pad), counter, font=counter_font, fill=(255, 255, 255, 180))

    return canvas.convert("RGB")


# ──────────────────────────────────────────────
#  CTA SLIDE  (last slide — reuses AI background)
# ──────────────────────────────────────────────

def render_cta_slide(base_image, profile, platform, slide_number, total_slides, review=None):
    w, h = PLATFORM_SIZES[platform]
    scale = h / 1920
    margin = int(60 * scale)

    # 1. Same smart-crop background (unique index = total_slides ensures a fresh crop)
    canvas = _make_slide_bg(base_image, total_slides, w, h).convert("RGBA")

    # 2. Cinematic dark gradient so white text is readable throughout
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(grad)
    for i in range(h):
        alpha = int(200 * (i / h) ** 1.2)
        grad_draw.line([(0, i), (w, i)], fill=(0, 0, 0, alpha))
    canvas = Image.alpha_composite(canvas, grad)
    draw = ImageDraw.Draw(canvas)

    white       = (255, 255, 255, 255)
    white_dim   = (255, 255, 255, 190)
    white_muted = (255, 255, 255, 140)
    accent      = (*_hex_rgb(profile["accent_color"]), 255)

    # 3. Top bar: app name (left) + counter (right)
    label_font = _find_font(PREFERRED_REG, max(18, int(32 * scale)))
    draw.text((margin, margin), profile["name"], font=label_font, fill=white_dim)
    counter_text = f"{slide_number} / {total_slides}"
    cb = draw.textbbox((0, 0), counter_text, font=label_font)
    draw.text((w - margin - (cb[2] - cb[0]), margin), counter_text, font=label_font, fill=accent)

    y = int(160 * scale)

    # 4. Logo — centred, large
    logo_size = int(200 * scale)
    logo = _load_logo(profile["logo_path"], logo_size, _hex_rgb(profile["accent_color"]))
    lx = (w - logo.width) // 2
    canvas.paste(logo, (lx, y), logo)
    draw = ImageDraw.Draw(canvas)
    y += logo.height + int(24 * scale)

    # 5. Accent underline
    line_w_px = int(70 * scale)
    line_h_px = max(4, int(5 * scale))
    draw.rectangle([(w - line_w_px) // 2, y, (w + line_w_px) // 2, y + line_h_px], fill=accent)
    y += line_h_px + int(36 * scale)

    # 6. Headline — bold, white, centred
    hl_pt = max(44, int(96 * scale))
    hl_font = _find_font(PREFERRED_BOLD, hl_pt)
    hl_text = profile.get("cta_headline", profile["name"]).upper()
    hl_wrapped = _wrap(draw, hl_text, hl_font, w - 2 * margin)
    y = _draw_centered_lines(draw, hl_wrapped, hl_font, y, w, white, line_gap=int(10 * scale))
    y += int(36 * scale)

    # 7. Review card
    if review:
        quote_pt = max(16, int(34 * scale))
        attr_pt  = max(13, int(26 * scale))
        quote_font = _find_font(PREFERRED_REG, quote_pt)
        attr_font  = _find_font(PREFERRED_REG, attr_pt)

        inner_w = w - 2 * margin - int(64 * scale)
        quote_text = f'"{review["text"]}"'
        attr_text  = f'— {review["reviewer"]}, {review["source"]}'
        quote_wrapped = _wrap(draw, quote_text, quote_font, inner_w)

        star_r = max(12, int(22 * scale))   # radius of each star
        star_row_h = star_r * 2

        pad_v = int(24 * scale)
        qb = draw.multiline_textbbox((0, 0), quote_wrapped, font=quote_font)
        ab = draw.textbbox((0, 0), attr_text, font=attr_font)
        card_h = pad_v + star_row_h + pad_v//2 + (qb[3]-qb[1]) + pad_v//2 + (ab[3]-ab[1]) + pad_v

        card_x = margin
        card_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_layer)
        card_draw.rounded_rectangle(
            [card_x, y, card_x + (w - 2 * margin), y + card_h],
            radius=int(18 * scale),
            fill=(255, 255, 255, 28),
        )
        canvas = Image.alpha_composite(canvas, card_layer)
        draw = ImageDraw.Draw(canvas)

        cy = y + pad_v

        # Geometrically drawn stars — no font glyph needed
        gap = max(6, int(10 * scale))
        _draw_stars(draw, w // 2, cy + star_r, star_r, 5, gap, accent)
        cy += star_row_h + pad_v // 2

        cy = _draw_centered_lines(draw, quote_wrapped, quote_font, cy, w, white_dim, line_gap=int(4 * scale))
        cy += pad_v // 2

        ab_w = ab[2] - ab[0]
        draw.text(((w - ab_w) // 2, cy), attr_text, font=attr_font, fill=white_muted)

        y += card_h + int(40 * scale)

    # 8. Tagline
    tag_pt = max(16, int(36 * scale))
    tag_font = _find_font(PREFERRED_REG, tag_pt)
    tag_wrapped = _wrap(draw, profile.get("cta_tagline", ""), tag_font, w - 2 * margin)
    y = _draw_centered_lines(draw, tag_wrapped, tag_font, y, w, white_dim, line_gap=int(4 * scale))
    y += int(24 * scale)

    # 9. Download + link in bio
    dl_pt = max(16, int(36 * scale))
    dl_font = _find_font(PREFERRED_BOLD, dl_pt)
    dl_wrapped = _wrap(draw, profile.get("cta_download", ""), dl_font, w - 2 * margin)
    _draw_centered_lines(draw, dl_wrapped, dl_font, y, w, white, line_gap=int(4 * scale))

    # 10. Bottom accent bar
    bar_h = max(6, int(8 * scale))
    draw.rectangle([0, h - bar_h, w, h], fill=accent)

    return canvas.convert("RGB")
