#!/usr/bin/env python3
"""AppFactory CLI v2 — Multi-Brand Social Content Engine."""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def _unique_out_dir(app_key: str, slug: str) -> Path:
    """Return output/app/slug, or output/app/slug_02, _03 … if it already exists."""
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


def _load_review(app_key: str):
    path = Path("assets") / "reviews" / f"{app_key}.json"
    if path.exists():
        try:
            reviews = json.loads(path.read_text())
            return random.choice(reviews) if reviews else None
        except Exception:
            pass
    return None


def _process_topic(topic: str, app_key: str, platform: str, provider_name: str, num_slides: int):
    from profiles import APP_PROFILES
    from llm_handler import generate_copy
    from image_factory import get_provider
    from renderer import render_slide, render_cta_slide

    profile = APP_PROFILES[app_key]
    provider = get_provider(provider_name)

    slug = _slugify(topic)
    out_dir = _unique_out_dir(app_key, slug)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_slides = num_slides + 1  # +1 for the CTA slide

    # 1. Claude generates copy for content slides
    print(f"\n[{profile['name']}] Topic: {topic!r}")
    slides = generate_copy(app_key, topic, num_slides)
    print(f"  ✓ {len(slides)} content slides from Claude")

    # 2. ONE AI background image for the whole carousel
    image_prompt = (
        f"{slides[0].get('image_prompt', topic)}, "
        f"{profile['background_style']}, ultra high quality, cinematic"
    )
    print(f"  Generating background via {provider_name.upper()} (1 call for {total_slides} slides)…")
    base_image = provider.generate(image_prompt, platform)
    print(f"  ✓ Background ready ({base_image.size[0]}×{base_image.size[1]})")

    # 3. Render content slides
    for i, slide in enumerate(slides):
        print(f"  Rendering slide {i + 1}/{total_slides}…")
        rendered = render_slide(base_image, slide, profile, platform, i, total_slides)
        rendered.save(out_dir / f"slide_{i + 1:02d}.png", "PNG")

    # 4. Render CTA slide (always last)
    print(f"  Rendering CTA slide {total_slides}/{total_slides}…")
    review = _load_review(app_key)
    cta = render_cta_slide(base_image, profile, platform, total_slides, total_slides, review)
    cta.save(out_dir / f"slide_{total_slides:02d}.png", "PNG")

    print(f"  ✓ Carousel saved → {out_dir}/")


def main():
    parser = argparse.ArgumentParser(
        description="AppFactory CLI v2 — generate branded carousels with AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --app calm_sos --topic "breathing exercises" --tiktok
  python main.py --app migraine_cast --topic "migraine triggers" --insta --provider openai
  python main.py --app calm_sos --batch topics.txt --tiktok --slides 6
""",
    )

    parser.add_argument("--app", required=True, choices=["calm_sos", "migraine_cast"])
    parser.add_argument("--topic", type=str)
    parser.add_argument("--batch", metavar="FILE")
    parser.add_argument("--tiktok", action="store_true", help="1080×1920 — default")
    parser.add_argument("--insta",  action="store_true", help="1080×1350")
    parser.add_argument("--provider", choices=["gemini", "openai"], default="gemini")
    parser.add_argument("--slides", type=int, default=5, metavar="N",
                        help="Content slides before CTA (default: 5)")

    args = parser.parse_args()

    if not args.topic and not args.batch:
        parser.error("Provide --topic or --batch.")
    if args.tiktok and args.insta:
        parser.error("Use --tiktok or --insta, not both.")

    platform = _platform(args)
    print(f"Platform: {platform.upper()}  |  Provider: {args.provider.upper()}  |  App: {args.app}")

    topics: list = []
    if args.topic:
        topics.append(args.topic)
    if args.batch:
        p = Path(args.batch)
        if not p.exists():
            sys.exit(f"Batch file not found: {args.batch}")
        topics.extend(ln.strip() for ln in p.read_text().splitlines() if ln.strip())

    for topic in topics:
        try:
            _process_topic(topic, args.app, platform, args.provider, args.slides)
        except Exception as exc:
            print(f"ERROR [{topic!r}]: {exc}", file=sys.stderr)
            if len(topics) == 1:
                raise


if __name__ == "__main__":
    main()
