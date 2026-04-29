"""Pillow rendering engine — V4 spec, 6-slide structured storytelling."""

import math
import os
import random
from PIL import Image, ImageFilter, ImageDraw, ImageFont

PLATFORM_SIZES = {"tiktok": (1080, 1920), "insta": (1080, 1350)}

NEON_GREEN = (57, 255, 20, 255)

# ── Safe zone (reference: 1080×1350) ─────────────────────────────────────────
# Avoids TikTok/Instagram UI chrome on all sides (buttons on right = 200px)
SAFE_TOP    = 150
SAFE_BOTTOM = 350
SAFE_LEFT   = 150
SAFE_RIGHT  = 200   # right UI buttons

# ── Per-slide brand colour cycles (slides 2/3/4 each get a distinct palette) ─
SLIDE_COLOR_CYCLES = {
    "migraine_cast": [
        {"bg": "#FFD6E0", "hl": "#1A1A1A", "body": "#5D2E46"},  # Petal Pink  (slide 2)
        {"bg": "#2D1B5E", "hl": "#FFFFFF",  "body": "#D4B8FF"},  # Deep Purple (slide 3)
        {"bg": "#2D3748", "hl": "#FFFFFF",  "body": "#E2E8F0"},  # Slate       (slide 4)
    ],
    "calm_sos": [
        {"bg": "#CE9FFC", "hl": "#1A1A1A", "body": "#2D1B5E"},  # Lavender    (slide 2)
        {"bg": "#2D1B5E", "hl": "#FFFFFF",  "body": "#D4B8FF"},  # Deep Purple (slide 3)
        {"bg": "#4B527E", "hl": "#FFFFFF",  "body": "#E8EDFF"},  # Indigo Slate (slide 4)
    ],
}

FONT_DIRS = [
    os.path.join(os.path.dirname(__file__), "fonts"),
    "/System/Library/Fonts",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/truetype/liberation",
]

PREFERRED_EXTRABOLD = ["Montserrat-ExtraBold.ttf", "Inter-ExtraBold.ttf",
                        "Montserrat-Bold.ttf", "Inter-Bold.ttf",
                        "Helvetica.ttc", "DejaVuSans-Bold.ttf"]
PREFERRED_BOLD      = ["Montserrat-Bold.ttf", "Inter-Bold.ttf",
                        "Helvetica.ttc", "DejaVuSans-Bold.ttf"]
PREFERRED_REG       = ["Montserrat-Regular.ttf", "Inter-Regular.ttf",
                        "Helvetica.ttc", "DejaVuSans.ttf"]


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────

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


def _wrap(draw, text: str, font, max_px: int) -> str:
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


def _safe_zone(w, h):
    """Return (top, bottom_y, left_x, right_x) scaled from 1350 reference."""
    s    = h / 1350
    top  = int(SAFE_TOP    * s)
    bot  = h - int(SAFE_BOTTOM * s)
    left = SAFE_LEFT                  # width is always 1080
    right = w - SAFE_RIGHT
    return top, bot, left, right


def _text_cx(left, right):
    """Horizontal centre of the safe zone."""
    return (left + right) // 2


def _draw_centered(draw, text: str, font, y: int, cx: int, fill: tuple,
                   line_gap: int = 8) -> int:
    for line in text.split("\n"):
        lb = draw.textbbox((0, 0), line, font=font)
        lw, lh = lb[2]-lb[0], lb[3]-lb[1]
        draw.text((cx - lw // 2, y), line, font=font, fill=fill)
        y += lh + line_gap
    return y


def _fit_neon_font(draw, text: str, max_width: int, initial_size: int):
    """Auto-scale neon word font so it always fits the safe zone width."""
    size = initial_size
    if len(text) > 7:
        size = int(size * 0.75)
    font = _find_font(PREFERRED_EXTRABOLD, size)
    while True:
        w = draw.textbbox((0, 0), text, font=font)[2]
        if w <= max_width or size <= 40:
            break
        size = int(size * (max_width / w) * 0.97)   # 3% margin
        font = _find_font(PREFERRED_EXTRABOLD, size)
    return font


def _round_image(img: Image.Image) -> Image.Image:
    s = min(img.size)
    img = img.crop(((img.width-s)//2, (img.height-s)//2,
                    (img.width+s)//2, (img.height+s)//2)).convert("RGBA")
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s-1, s-1], fill=255)
    img.putalpha(mask)
    return img


def _load_logo(path: str, size: int, fallback_color: tuple) -> Image.Image:
    if os.path.exists(path):
        try:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((size, size), Image.LANCZOS)
            return _round_image(img)
        except Exception:
            pass
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([0, 0, size-1, size-1], fill=(*fallback_color, 220))
    d.text((size//2, size//2), "A", font=_find_font(PREFERRED_BOLD, max(10, size//3)),
           fill=(255, 255, 255, 255), anchor="mm")
    return img


def _draw_stars(draw, cx, cy, star_r, n, gap, color):
    total_w = n * star_r * 2 + (n - 1) * gap
    x0 = cx - total_w // 2 + star_r
    for i in range(n):
        sx = x0 + i * (star_r * 2 + gap)
        pts = []
        for j in range(10):
            angle = math.pi / 5 * j - math.pi / 2
            r = star_r if j % 2 == 0 else int(star_r * 0.42)
            pts.append((sx + r * math.cos(angle), cy + r * math.sin(angle)))
        draw.polygon(pts, fill=color)


def _fit_checklist(draw, items, max_text, check_size, scale, available_h, row_gap):
    """Return (font, wrapped_items) that fit within available_h.
    Reduces font size first, then trims items (always keeping the last one),
    never going below 3 items."""
    item_text_w = max_text - check_size - int(20 * scale)
    max_pt = max(20, int(44 * scale))
    min_pt = max(16, int(28 * scale))

    for n in range(len(items), 2, -1):
        subset = (items[:n - 1] + [items[-1]]) if n < len(items) else list(items)
        for pt in range(max_pt, min_pt - 1, -2):
            font = _find_font(PREFERRED_REG, pt)
            wrapped = []
            for text in subset:
                w = _wrap(draw, text, font, item_text_w)
                ib = draw.multiline_textbbox((0, 0), w, font=font)
                row_h = max(check_size, ib[3] - ib[1]) + int(8 * scale)
                wrapped.append((w, row_h))
            total_h = sum(r for _, r in wrapped) + row_gap * max(0, len(wrapped) - 1)
            if total_h <= available_h:
                return font, wrapped

    # Absolute fallback: 3 items at minimum font
    font = _find_font(PREFERRED_REG, min_pt)
    subset = items[:2] + [items[-1]]
    wrapped = []
    for text in subset:
        w = _wrap(draw, text, font, item_text_w)
        ib = draw.multiline_textbbox((0, 0), w, font=font)
        row_h = max(check_size, ib[3] - ib[1]) + int(8 * scale)
        wrapped.append((w, row_h))
    return font, wrapped


def _draw_checkmark(draw, x, y, size, color):
    lw = max(2, size // 7)
    draw.rounded_rectangle([x, y, x+size, y+size], radius=size//5, outline=color, width=lw)
    m  = size // 6
    p1 = (x + m,            y + size // 2)
    p2 = (x + int(size*.42), y + size - m - 1)
    p3 = (x + size - m,     y + m + 2)
    draw.line([p1, p2], fill=color, width=lw)
    draw.line([p2, p3], fill=color, width=lw)


def _top_bar(canvas, profile, slide_idx, total_slides, h):
    """Logo top-left, counter top-right. Returns draw handle."""
    w     = canvas.width
    scale = h / 1350
    pad   = int(40 * scale)
    lsize = int(68 * scale)
    accent = _hex_rgb(profile["accent_color"])

    logo     = _load_logo(profile["logo_path"], lsize, accent)
    logo_pad = int(20 * scale)   # extra inset — avoids rounded-corner/Live UI clip
    canvas.paste(logo, (pad + logo_pad, pad + logo_pad), logo)

    draw = ImageDraw.Draw(canvas)
    cfont = _find_font(PREFERRED_REG, max(14, int(26 * scale)))
    ctxt  = f"{slide_idx + 1} / {total_slides}"
    cb    = draw.textbbox((0, 0), ctxt, font=cfont)
    draw.text((w - pad - (cb[2]-cb[0]), pad + (lsize-(cb[3]-cb[1]))//2),
              ctxt, font=cfont, fill=(*accent, 220))
    return draw


def _bottom_bar(draw, w, h, accent_rgb):
    bh = max(6, int(8 * h / 1350))
    draw.rectangle([0, h-bh, w, h], fill=(*accent_rgb, 255))


def _find_screenshot(app_key: str):
    folder = os.path.join("assets", "screenshots", app_key)
    if os.path.exists(folder):
        for fname in sorted(os.listdir(folder)):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                return os.path.join(folder, fname)
    return None


def _make_paper_bg(w: int, h: int) -> Image.Image:
    rng   = random.Random(42)
    base  = (242, 237, 224)
    tw, th = 160, 160
    pixels = []
    for _ in range(tw * th):
        n = rng.randint(-20, 20)
        pixels.append((max(0,min(255,base[0]+n)), max(0,min(255,base[1]+n)),
                       max(0,min(255,base[2]+n))))
    tile   = Image.new("RGB", (tw, th)); tile.putdata(pixels)
    result = Image.new("RGB", (w, h))
    for y in range(0, h, th):
        for x in range(0, w, tw):
            result.paste(tile, (x, y))
    return result


# ──────────────────────────────────────────────
#  SLIDE 1: HOOK
# ──────────────────────────────────────────────

def render_hook_slide(bg_image, slide_data, profile, platform, slide_idx, total_slides):
    w, h = PLATFORM_SIZES[platform]
    safe_top, safe_bot, safe_left, safe_right = _safe_zone(w, h)
    cx       = w // 2   # true canvas centre — safe zone cx (515) drifts left
    max_text = safe_right - safe_left
    scale    = h / 1350

    # 1. Resize + 2px blur
    canvas = bg_image.resize((w, h), Image.LANCZOS).convert("RGBA")
    canvas = canvas.filter(ImageFilter.GaussianBlur(radius=2))

    # 2. 60% black overlay (153/255 ≈ 60%)
    canvas = Image.alpha_composite(canvas, Image.new("RGBA", (w, h), (0, 0, 0, 153)))

    neon_word = slide_data.get("neon_word", "NOW")
    hook_text = slide_data.get("hook", "")

    draw = ImageDraw.Draw(canvas)

    # 3. Neon word — auto-scaled to fit safe zone width
    neon_pt   = max(80, int(210 * scale))
    neon_font = _fit_neon_font(draw, neon_word, max_text, neon_pt)
    nb        = draw.textbbox((0, 0), neon_word, font=neon_font)
    nw, nh    = nb[2]-nb[0], nb[3]-nb[1]

    hook_pt   = max(24, int(50 * scale))
    hook_font = _find_font(PREFERRED_REG, hook_pt)
    hook_wrap = _wrap(draw, hook_text, hook_font, max_text)
    hb        = draw.multiline_textbbox((0, 0), hook_wrap, font=hook_font)
    hh        = hb[3]-hb[1]

    gap      = int(28 * scale)
    content_h = nh + gap + hh
    start_y  = safe_top + ((safe_bot - safe_top) - content_h) // 2
    neon_x   = cx - nw // 2
    neon_y   = start_y

    # 4. Neon glow layer
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    for dx, dy in [(-4,0),(4,0),(0,-4),(0,4),(-3,-3),(3,-3),(-3,3),(3,3),(0,0)]:
        gd.text((neon_x+dx, neon_y+dy), neon_word, font=neon_font, fill=(57,255,20,65))
    glow   = glow.filter(ImageFilter.GaussianBlur(radius=5))
    canvas = Image.alpha_composite(canvas, glow)
    draw   = ImageDraw.Draw(canvas)

    # 5. Neon word + hook
    draw.text((neon_x, neon_y), neon_word, font=neon_font, fill=NEON_GREEN)
    _draw_centered(draw, hook_wrap, hook_font, neon_y + nh + gap, cx,
                   (255,255,255,215), line_gap=int(8*scale))

    draw = _top_bar(canvas, profile, slide_idx, total_slides, h)
    return canvas.convert("RGB")


# ──────────────────────────────────────────────
#  SLIDES 2-4: BRAND  (colour-cycled)
# ──────────────────────────────────────────────

def render_brand_slide(slide_data, profile, platform, slide_idx, total_slides,
                        bridge=False, bridge_side=None):
    """
    bridge_side: None | "exit" (slide 3 — line exits right) | "entry" (slide 4 — line enters left)
    """
    w, h = PLATFORM_SIZES[platform]
    safe_top, safe_bot, safe_left, safe_right = _safe_zone(w, h)
    cx       = _text_cx(safe_left, safe_right)
    max_text = safe_right - safe_left
    scale    = h / 1350

    # Colour cycle: slide_idx 1→0, 2→1, 3→2
    # Prefer pillar-specific cycle injected into profile; fall back to app default
    color_idx = max(0, slide_idx - 1)
    if "slide_color_cycle" in profile:
        cycle = profile["slide_color_cycle"]
    else:
        app_key = next(k for k, v in __import__("profiles").APP_PROFILES.items()
                       if v["name"] == profile["name"])
        cycle = SLIDE_COLOR_CYCLES.get(app_key, SLIDE_COLOR_CYCLES["migraine_cast"])
    colors = cycle[color_idx % len(cycle)]

    bg_rgb  = _hex_rgb(colors["bg"])
    hl_rgb  = _hex_rgb(colors["hl"])
    body_rgb = _hex_rgb(colors["body"])
    accent_rgb = _hex_rgb(profile["accent_color"])

    canvas = Image.new("RGBA", (w, h), (*bg_rgb, 255))
    draw   = ImageDraw.Draw(canvas)

    header = slide_data.get("header", "")
    body   = slide_data.get("body", "")

    header_pt   = max(40, int(84 * scale))
    body_pt     = max(20, int(44 * scale))
    header_font = _find_font(PREFERRED_BOLD, header_pt)
    body_font   = _find_font(PREFERRED_REG,  body_pt)

    header_wrap = _wrap(draw, header, header_font, max_text)
    body_wrap   = _wrap(draw, body,   body_font,   max_text)
    hb = draw.multiline_textbbox((0,0), header_wrap, font=header_font)
    bb = draw.multiline_textbbox((0,0), body_wrap,   font=body_font)

    sep_h   = max(3, int(4 * scale))
    sep_gap = int(24 * scale)
    content_h = (hb[3]-hb[1]) + sep_gap + sep_h + sep_gap + (bb[3]-bb[1])

    # "Clear Lane" rule for slide 4 — keep text above bridge line (y=675 scaled)
    bridge_y = int(675 * h / 1350)
    if bridge_side == "entry":
        # Top-heavy: start early, end before bridge line
        start_y = int(250 * h / 1350)
    else:
        start_y = safe_top + ((safe_bot - safe_top) - content_h) // 2

    # Header
    _draw_centered(draw, header_wrap, header_font, start_y, cx,
                   (*hl_rgb, 255), line_gap=int(8*scale))

    sep_y = start_y + (hb[3]-hb[1]) + sep_gap
    sep_w = int(90 * scale)
    draw.rectangle([(cx-sep_w//2, sep_y), (cx+sep_w//2, sep_y+sep_h)],
                   fill=(*accent_rgb, 255))

    _draw_centered(draw, body_wrap, body_font, sep_y + sep_h + sep_gap, cx,
                   (*body_rgb, 225), line_gap=int(8*scale))

    # Bridge line (neon, thick)
    if bridge:
        line_w = max(4, int(6 * scale))
        if bridge_side == "exit":
            # Exits off the RIGHT edge — visible from x=1000 to x=w
            x0 = int(1000 * w / 1080)
            draw.line([(x0, bridge_y), (w, bridge_y)], fill=NEON_GREEN, width=line_w)
        elif bridge_side == "entry":
            # Enters from the LEFT edge — visible from x=0 to x=80
            x1 = int(80 * w / 1080)
            draw.line([(0, bridge_y), (x1, bridge_y)], fill=NEON_GREEN, width=line_w)

    draw = _top_bar(canvas, profile, slide_idx, total_slides, h)
    _bottom_bar(draw, w, h, accent_rgb)
    return canvas.convert("RGB")


# ──────────────────────────────────────────────
#  SLIDE 5: THE PROTOCOL  (paper texture checklist)
# ──────────────────────────────────────────────

def render_checklist_slide(slide_data, profile, platform, slide_idx, total_slides):
    w, h = PLATFORM_SIZES[platform]
    safe_top, safe_bot, safe_left, safe_right = _safe_zone(w, h)
    cx       = _text_cx(safe_left, safe_right)
    max_text = safe_right - safe_left
    scale    = h / 1350

    # Background: use pillar's last slide color for visual continuity (not paper)
    cycle  = profile.get("slide_color_cycle") or SLIDE_COLOR_CYCLES.get(
        next((k for k, v in __import__("profiles").APP_PROFILES.items()
              if v["name"] == profile["name"]), "migraine_cast"),
        SLIDE_COLOR_CYCLES["migraine_cast"]
    )
    bg_hex    = cycle[2]["bg"]
    body_hex  = cycle[2]["body"]
    canvas    = Image.new("RGBA", (w, h), (*_hex_rgb(bg_hex), 255))

    draw       = ImageDraw.Draw(canvas)
    accent_rgb = _hex_rgb(profile["accent_color"])
    dark_text  = (*_hex_rgb(body_hex), 255)

    # Always "THE PROTOCOL" — the save magnet
    title = "THE PROTOCOL"
    items = slide_data.get("checklist", [])

    # Auto-scale title to fit safe zone width (730px) — prevents bleed
    title_pt   = max(48, int(100 * scale))
    title_font = _fit_neon_font(draw, title, max_text, title_pt)
    item_pt    = max(20, int(44 * scale))
    item_font  = _find_font(PREFERRED_REG, item_pt)

    tb      = draw.textbbox((0, 0), title, font=title_font)
    title_h = tb[3]-tb[1]
    title_w = min(tb[2]-tb[0], max_text)   # cap displayed width to safe zone

    check_size = max(26, int(46 * scale))
    row_gap    = int(20 * scale)
    gap        = int(40 * scale)
    start_y    = int(200 * h / 1350)

    # Title in accent colour, centred within safe zone — stroke adds visual weight
    stroke_w = max(2, int(3 * scale))
    draw.text((cx - title_w//2, start_y), title, font=title_font, fill=(*accent_rgb, 255),
              stroke_width=stroke_w, stroke_fill=(*accent_rgb, 255))

    # Neon underline (same width as title)
    ul_y = start_y + title_h + int(6*scale)
    draw.line([(cx - title_w//2, ul_y), (cx + title_w//2, ul_y)],
              fill=NEON_GREEN, width=max(3, int(4*scale)))

    # Auto-fit checklist: scale font / trim items until everything sits above safe_bot
    item_y      = ul_y + int(10*scale) + gap
    available_h = safe_bot - item_y
    item_font, wrapped_items = _fit_checklist(
        draw, items, max_text, check_size, scale, available_h, row_gap)

    item_x = safe_left
    for wrapped, row_h in wrapped_items:
        _draw_checkmark(draw, item_x, item_y, check_size, (*accent_rgb, 255))
        tx = item_x + check_size + int(20*scale)
        draw.multiline_text((tx, item_y), wrapped, font=item_font, fill=dark_text,
                            spacing=int(6*scale))
        item_y += row_h + row_gap

    draw = _top_bar(canvas, profile, slide_idx, total_slides, h)
    _bottom_bar(draw, w, h, accent_rgb)
    return canvas.convert("RGB")


# ──────────────────────────────────────────────
#  SLIDE 6: CTA  (phone mockup — humanises the app)
# ──────────────────────────────────────────────

def render_cta_slide(slide_data, profile, platform, slide_idx, total_slides,
                      app_key, review=None):
    w, h = PLATFORM_SIZES[platform]
    safe_top, safe_bot, safe_left, safe_right = _safe_zone(w, h)
    cx       = _text_cx(safe_left, safe_right)
    max_text = safe_right - safe_left
    scale    = h / 1350

    accent_rgb   = _hex_rgb(profile["accent_color"])
    headline_rgb = _hex_rgb(profile["footer_text_color"])
    bg_rgb       = _hex_rgb(profile["primary_color"])

    # Background: real hand-holding-phone screenshot humanises the app
    screenshot = _find_screenshot(app_key)
    on_dark    = False
    if screenshot:
        try:
            bg      = Image.open(screenshot).convert("RGBA").resize((w, h), Image.LANCZOS)
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 165))
            canvas  = Image.alpha_composite(bg, overlay)
            on_dark = True
        except Exception:
            canvas = Image.new("RGBA", (w, h), (*bg_rgb, 255))
    else:
        canvas = Image.new("RGBA", (w, h), (*bg_rgb, 255))

    draw = ImageDraw.Draw(canvas)

    text_main  = (255, 255, 255, 255) if on_dark else (*headline_rgb, 255)
    text_dim   = (255, 255, 255, 190) if on_dark else (*headline_rgb, 200)

    y = safe_top

    # Logo — centred, large
    logo_size = int(170 * scale)
    logo      = _load_logo(profile["logo_path"], logo_size, accent_rgb)
    canvas.paste(logo, ((w - logo.width)//2, y), logo)
    draw = ImageDraw.Draw(canvas)
    y   += logo.height + int(24 * scale)

    # Accent underline
    ul_w = int(60 * scale)
    ul_h = max(3, int(5 * scale))
    draw.rectangle([(cx-ul_w//2, y), (cx+ul_w//2, y+ul_h)], fill=(*accent_rgb, 255))
    y += ul_h + int(32*scale)

    # Social proof CTA — smaller font to prevent multi-line overflow
    cta_text = slide_data.get("cta", "100% of trial users stay. Find out why.")
    cta_pt   = max(28, int(52 * scale))
    cta_font = _find_font(PREFERRED_BOLD, cta_pt)
    cta_wrap = _wrap(draw, cta_text, cta_font, max_text)
    y        = _draw_centered(draw, cta_wrap, cta_font, y, cx, text_main,
                               line_gap=int(10*scale))
    y       += int(28*scale)

    # Review card
    if review:
        qfont = _find_font(PREFERRED_REG, max(14, int(30*scale)))
        afont = _find_font(PREFERRED_REG, max(12, int(22*scale)))
        inner = max_text - int(40*scale)

        qwrap  = _wrap(draw, f'"{review["text"]}"', qfont, inner)
        atxt   = f'— {review["reviewer"]}, {review["source"]}'
        star_r = max(10, int(16*scale))
        pad_v  = int(18*scale)
        qb = draw.multiline_textbbox((0,0), qwrap, font=qfont)
        ab = draw.textbbox((0,0), atxt, font=afont)
        card_h = pad_v + star_r*2 + pad_v//2 + (qb[3]-qb[1]) + pad_v//2 + (ab[3]-ab[1]) + pad_v

        cl = Image.new("RGBA", (w, h), (0,0,0,0))
        ImageDraw.Draw(cl).rounded_rectangle([safe_left, y, safe_right, y+card_h],
                                              radius=int(14*scale), fill=(255,255,255,28))
        canvas = Image.alpha_composite(canvas, cl)
        draw   = ImageDraw.Draw(canvas)

        cy = y + pad_v
        _draw_stars(draw, cx, cy+star_r, star_r, 5, max(5, int(9*scale)),
                    (*accent_rgb, 255))
        cy += star_r*2 + pad_v//2
        cy  = _draw_centered(draw, qwrap, qfont, cy, cx, text_dim, line_gap=int(4*scale))
        cy += pad_v//2
        aw  = ab[2]-ab[0]
        draw.text((cx-aw//2, cy), atxt, font=afont,
                  fill=(255,255,255,130) if on_dark else (*headline_rgb,130))
        y += card_h + int(24*scale)

    # Bottom row: "Link in bio." left  |  @handle right
    # Pinned just above the accent bar at the true bottom of the canvas
    bar_h      = max(6, int(8 * scale))
    bot_font   = _find_font(PREFERRED_BOLD, max(16, int(30*scale)))
    lib_txt    = "Link in bio."
    handle_txt = profile.get("tiktok_handle", "")
    lb  = draw.textbbox((0, 0), lib_txt,    font=bot_font)
    hb  = draw.textbbox((0, 0), handle_txt, font=bot_font)
    bot_h = lb[3] - lb[1]
    bot_y = h - bar_h - bot_h - int(24*scale)    # flush to canvas bottom, above accent bar

    # MigraineCast only: localisation line sits just above the bottom row
    if app_key == "migraine_cast":
        loc_txt  = "Available in English, Dutch, French, German, & Spanish."
        loc_font = _find_font(PREFERRED_REG, max(12, int(22*scale)))
        lb2      = draw.textbbox((0, 0), loc_txt, font=loc_font)
        loc_h    = lb2[3] - lb2[1]
        loc_y    = bot_y - loc_h - int(10*scale)
        loc_w    = lb2[2] - lb2[0]
        draw.text((cx - loc_w//2, loc_y), loc_txt, font=loc_font,
                  fill=(255, 255, 255, 140) if on_dark else (*headline_rgb, 140))

    draw.text((safe_left,                    bot_y), lib_txt,    font=bot_font, fill=NEON_GREEN)
    draw.text((safe_right - (hb[2]-hb[0]),   bot_y), handle_txt, font=bot_font,
              fill=(255,255,255,200) if on_dark else (*accent_rgb, 220))

    draw = _top_bar(canvas, profile, slide_idx, total_slides, h)
    _bottom_bar(draw, w, h, accent_rgb)
    return canvas.convert("RGB")
