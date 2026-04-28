#!/usr/bin/env python3
"""AppFactory CLI — 6-slide structured storytelling engine."""

import argparse
import json
import random
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def _unique_out_dir(app_key: str, slug: str) -> Path:
    base = Path("output") / app_key / slug
    if not base.exists():
        return base
    i = 2
    while True:
        candidate = Path("output") / app_key / f"{slug}_{i:02d}"
        if not candidate.exists():
            return candidate
        i += 1


def _platform(args) -> str:
    return "insta" if args.insta else "tiktok"


def _format_caption(caption: str, topic: str, cta: str) -> str:
    """Prepend topic title, ensure paragraphs, enforce fixed CTA before hashtags."""
    paragraphs = [p.strip() for p in caption.strip().split("\n\n") if p.strip()]

    # Pull off the hashtag block (last paragraph starting with #)
    hashtags = ""
    if paragraphs and paragraphs[-1].lstrip().startswith("#"):
        hashtags = paragraphs.pop()

    # Enforce fixed CTA as the last body paragraph
    paragraphs[-1] = cta

    parts = [topic] + paragraphs
    if hashtags:
        parts.append(hashtags)
    return "\n\n".join(parts)


def _load_review(app_key: str):
    path = Path("assets") / "reviews" / f"{app_key}.json"
    if path.exists():
        try:
            reviews = json.loads(path.read_text())
            return random.choice(reviews) if reviews else None
        except Exception:
            pass
    return None


def _process_topic(topic: str, app_key: str, platform: str, provider_name: str,
                   topic_number: int = None):
    from profiles import APP_PROFILES
    from llm_handler import generate_carousel
    from image_factory import get_provider
    from topic_manager import mark_used, parse_topic_list
    from renderer import (render_hook_slide, render_brand_slide,
                          render_checklist_slide, render_cta_slide)

    profile  = APP_PROFILES[app_key]
    provider = get_provider(provider_name)

    out_dir = _unique_out_dir(app_key, _slugify(topic))
    out_dir.mkdir(parents=True, exist_ok=True)

    total_slides = 6

    # ── Step 1: Gemini generates all copy + image prompt ──────────────────
    print(f"\n[{profile['name']}] Topic: {topic!r}")
    print("  Generating 6-slide JSON via Gemini…")
    data         = generate_carousel(app_key, topic)
    slides       = data["slides"]
    image_prompt = data.get("image_prompt", topic)
    caption      = data.get("caption", "")
    print(f"  ✓ Copy ready")

    # ── Step 2: Gemini Imagen generates Slide 1 background ────────────────
    print(f"  Generating background image via {provider_name.upper()}…")
    bg_image = provider.generate(
        f"{image_prompt}, ultra cinematic, 8k, high contrast",
        platform,
    )
    print(f"  ✓ Background ready ({bg_image.size[0]}×{bg_image.size[1]})")

    # ── Step 3: Render all 6 slides ────────────────────────────────────────
    review = _load_review(app_key)

    renders = [
        # Slide 1 — Hook: AI image + overlay + neon word
        render_hook_slide(bg_image, slides[0], profile, platform, 0, total_slides),

        # Slide 2 — Brand colour, no bridge
        render_brand_slide(slides[1], profile, platform, 1, total_slides,
                           bridge=False),

        # Slide 3 — Brand colour, line exits right edge (swipe nudge)
        render_brand_slide(slides[2], profile, platform, 2, total_slides,
                           bridge=True, bridge_side="exit"),

        # Slide 4 — Brand colour, line enters from left edge + clear lane
        render_brand_slide(slides[3], profile, platform, 3, total_slides,
                           bridge=True, bridge_side="entry"),

        # Slide 5 — Paper texture checklist
        render_checklist_slide(slides[4], profile, platform, 4, total_slides),

        # Slide 6 — Phone mockup CTA
        render_cta_slide(slides[5], profile, platform, 5, total_slides, app_key, review),
    ]

    for i, img in enumerate(renders, start=1):
        path = out_dir / f"slide_{i:02d}.png"
        img.save(path, "PNG")
        print(f"  Saved slide {i}/6 → {path.name}")

    # ── Step 4: Save caption ───────────────────────────────────────────────
    if caption:
        caption = _format_caption(caption, topic, profile["caption_cta"])
        (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
        print(f"  Saved caption.txt")

    print(f"\n  ✓ Carousel complete → {out_dir}/")

    # Mark topic as used in history (only when auto-picked from master list)
    if topic_number is not None and profile.get("topic_list"):
        total = len(parse_topic_list(profile["topic_list"]))
        mark_used(app_key, topic_number, total)


def main():
    parser = argparse.ArgumentParser(
        description="AppFactory CLI — 6-slide AI carousel generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --app migraine_cast --topic "Barometric Pressure and Migraines" --tiktok
  python main.py --app calm_sos --topic "5-minute panic reset" --insta
  python main.py --app migraine_cast --batch topics.txt --tiktok --provider openai
""",
    )

    parser.add_argument("--app",      required=True, choices=["calm_sos", "migraine_cast"])
    parser.add_argument("--topic",    type=str)
    parser.add_argument("--batch",    metavar="FILE")
    parser.add_argument("--auto",     action="store_true",
                        help="Auto-pick next unused topic from the app's master list.")
    parser.add_argument("--history",  action="store_true",
                        help="Show topic usage history and exit.")
    parser.add_argument("--tiktok",   action="store_true", help="1080×1920 — default")
    parser.add_argument("--insta",    action="store_true", help="1080×1350")
    parser.add_argument("--provider", choices=["gemini", "openai"], default="gemini")

    args = parser.parse_args()

    # --history: show stats and exit
    if args.history:
        from profiles import APP_PROFILES
        from topic_manager import show_history
        profile = APP_PROFILES[args.app]
        topic_list = profile.get("topic_list")
        if not topic_list:
            sys.exit(f"No topic list configured for {args.app}.")
        show_history(args.app, topic_list)
        sys.exit(0)

    if not args.topic and not args.batch and not args.auto:
        parser.error("Provide --topic, --batch, or --auto.")
    if args.tiktok and args.insta:
        parser.error("Use --tiktok or --insta, not both.")

    platform = _platform(args)
    print(f"Platform: {platform.upper()}  |  Provider: {args.provider.upper()}  |  App: {args.app}")

    # Build topic list
    topics        = []   # list of (topic_text, topic_number_or_None)
    topic_number  = None

    if args.auto:
        from profiles import APP_PROFILES
        from topic_manager import pick_topic
        profile    = APP_PROFILES[args.app]
        topic_list = profile.get("topic_list")
        if not topic_list:
            sys.exit(f"No topic list configured for {args.app}. Add 'topic_list' to profiles.py.")
        topic_number, topic_text = pick_topic(args.app, topic_list)
        print(f"  Auto-selected topic #{topic_number}: {topic_text!r}")
        topics.append((topic_text, topic_number))

    if args.topic:
        topics.append((args.topic, None))

    if args.batch:
        p = Path(args.batch)
        if not p.exists():
            sys.exit(f"Batch file not found: {args.batch}")
        topics.extend((ln.strip(), None) for ln in p.read_text().splitlines() if ln.strip())

    for topic_text, t_num in topics:
        try:
            _process_topic(topic_text, args.app, platform, args.provider, topic_number=t_num)
        except Exception as exc:
            print(f"ERROR [{topic_text!r}]: {exc}", file=sys.stderr)
            if len(topics) == 1:
                raise


if __name__ == "__main__":
    main()
