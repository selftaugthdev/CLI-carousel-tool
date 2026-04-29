#!/usr/bin/env python3
"""AppFactory CLI — 6-slide AI carousel generator."""

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

    hashtags = ""
    if paragraphs and paragraphs[-1].lstrip().startswith("#"):
        hashtags = paragraphs.pop()

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


def _prompt_pillar(app_key: str) -> int:
    from profiles import PILLARS
    pillars = PILLARS[app_key]
    print("\n  Select a pillar:")
    for n, p in pillars.items():
        print(f"    {n}. {p['name']}  —  {p['audience']}")
    while True:
        choice = input("  Pillar (1/2/3): ").strip()
        if choice in ("1", "2", "3"):
            return int(choice)
        print("  Please enter 1, 2, or 3.")


def _prompt_hook(hooks: list) -> str:
    print()
    for i, h in enumerate(hooks, 1):
        print(f"  {i}.  {h['hook']}")
        print(f"      Formula : {h['formula']}")
        print(f"      Tension : {h['tension']}")
        print(f"      Emotion : {h['emotion']}")
        print()
    while True:
        choice = input("  Which hook — 1, 2, or 3? ").strip()
        if choice in ("1", "2", "3"):
            return hooks[int(choice) - 1]["hook"]
        print("  Please enter 1, 2, or 3.")


def _process_topic(topic: str, app_key: str, platform: str, provider_name: str,
                   topic_number: int = None, pillar_num: int = None,
                   chosen_hook: str = None):
    from profiles import APP_PROFILES, PILLARS
    from llm_handler import generate_hooks, generate_carousel
    from image_factory import get_provider
    from topic_manager import mark_used, mark_pillar, parse_topic_list
    from renderer import (render_hook_slide, render_brand_slide,
                          render_checklist_slide, render_cta_slide)

    base_profile = APP_PROFILES[app_key]
    provider     = get_provider(provider_name)

    # ── Step 1: Resolve pillar ─────────────────────────────────────────────
    if pillar_num is None:
        pillar_num = _prompt_pillar(app_key)
    pillar = PILLARS[app_key][pillar_num]
    print(f"\n[{base_profile['name']}] Pillar {pillar_num}: {pillar['name']}")
    print(f"  Topic: {topic!r}")

    # Merge pillar colours into a working profile copy
    profile = {**base_profile,
               "accent_color":      pillar["accent_color"],
               "slide_color_cycle": pillar["slide_color_cycle"]}

    # ── Step 2: Hook selection ─────────────────────────────────────────────
    if chosen_hook is None:
        print("  Generating hooks…")
        hooks = generate_hooks(app_key, topic, pillar_num)
        chosen_hook = _prompt_hook(hooks)

    print(f"  Hook: {chosen_hook!r}")

    out_dir = _unique_out_dir(app_key, _slugify(topic))
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 3: Generate carousel copy ────────────────────────────────────
    print("  Generating 6-slide JSON via Gemini…")
    data         = generate_carousel(app_key, topic, pillar_num, chosen_hook)
    slides       = data["slides"]
    image_prompt = data.get("image_prompt", topic)
    caption      = data.get("caption", "")
    print("  ✓ Copy ready")

    # ── Step 4: Generate background image ─────────────────────────────────
    print(f"  Generating background image via {provider_name.upper()}…")
    bg_image = provider.generate(
        f"{image_prompt}, ultra cinematic, 8k, high contrast",
        platform,
    )
    print(f"  ✓ Background ready ({bg_image.size[0]}×{bg_image.size[1]})")

    # ── Step 5: Render all 6 slides ───────────────────────────────────────
    total_slides = 6
    review       = _load_review(app_key)

    renders = [
        render_hook_slide(bg_image, slides[0], profile, platform, 0, total_slides),
        render_brand_slide(slides[1], profile, platform, 1, total_slides, bridge=False),
        render_brand_slide(slides[2], profile, platform, 2, total_slides,
                           bridge=True, bridge_side="exit"),
        render_brand_slide(slides[3], profile, platform, 3, total_slides,
                           bridge=True, bridge_side="entry"),
        render_checklist_slide(slides[4], profile, platform, 4, total_slides),
        render_cta_slide(slides[5], profile, platform, 5, total_slides, app_key, review),
    ]

    for i, img in enumerate(renders, start=1):
        path = out_dir / f"slide_{i:02d}.png"
        img.save(path, "PNG")
        print(f"  Saved slide {i}/6 → {path.name}")

    # ── Step 6: Save caption ──────────────────────────────────────────────
    if caption:
        caption = _format_caption(caption, topic, base_profile["caption_cta"])
        (out_dir / "caption.txt").write_text(caption, encoding="utf-8")
        print("  Saved caption.txt")

    print(f"\n  ✓ Carousel complete → {out_dir}/")

    # Track history
    if topic_number is not None and base_profile.get("topic_list"):
        total = len(parse_topic_list(base_profile["topic_list"]))
        mark_used(app_key, topic_number, total)
    mark_pillar(app_key, pillar_num)


def main():
    parser = argparse.ArgumentParser(
        description="AppFactory CLI — 6-slide AI carousel generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --app migraine_cast --topic "Barometric Pressure and Migraines" --tiktok
  python main.py --app calm_sos --topic "5-minute panic reset" --pillar 1 --insta
  python main.py --app migraine_cast --batch topics.txt --tiktok --provider openai
  python main.py --app calm_sos --auto --count 14 --tiktok
""",
    )

    parser.add_argument("--app",      required=True, choices=["calm_sos", "migraine_cast"])
    parser.add_argument("--topic",    type=str)
    parser.add_argument("--batch",    metavar="FILE")
    parser.add_argument("--auto",     action="store_true",
                        help="Auto-pick next unused topic from the app's master list.")
    parser.add_argument("--count",    type=int, default=1, metavar="N",
                        help="Number of carousels to generate with --auto (default: 1). Use 14 for a full week.")
    parser.add_argument("--pillar",   type=int, choices=[1, 2, 3],
                        help="Content pillar: 1=Emotional Validation, 2=Educational, 3=Caregiver. "
                             "Prompted interactively for --topic if omitted. Auto-cycled for --auto.")
    parser.add_argument("--history",  action="store_true",
                        help="Show topic usage history and exit.")
    parser.add_argument("--tiktok",   action="store_true", help="1080×1920 — default")
    parser.add_argument("--insta",    action="store_true", help="1080×1350")
    parser.add_argument("--provider", choices=["gemini", "openai"], default="gemini")

    args = parser.parse_args()

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

    # ── Build work queue: [(topic_text, topic_number, pillar_num)] ────────
    queue = []

    if args.auto:
        from profiles import APP_PROFILES
        from topic_manager import pick_topics, get_next_pillar
        profile    = APP_PROFILES[args.app]
        topic_list = profile.get("topic_list")
        if not topic_list:
            sys.exit(f"No topic list configured for {args.app}. Add 'topic_list' to profiles.py.")
        picked = pick_topics(args.app, topic_list, args.count)
        for num, text in picked:
            print(f"  Auto-selected topic #{num}: {text!r}")
        # Cycle pillars starting from the next one after last used
        start_pillar = get_next_pillar(args.app)
        for i, (num, text) in enumerate(picked):
            p = ((start_pillar - 1 + i) % 3) + 1
            queue.append((text, num, p))

    if args.topic:
        queue.append((args.topic, None, args.pillar))  # pillar may be None → prompted interactively

    if args.batch:
        p = Path(args.batch)
        if not p.exists():
            sys.exit(f"Batch file not found: {args.batch}")
        for ln in p.read_text().splitlines():
            if ln.strip():
                queue.append((ln.strip(), None, args.pillar))

    for topic_text, t_num, pillar_num in queue:
        try:
            _process_topic(topic_text, args.app, platform, args.provider,
                           topic_number=t_num, pillar_num=pillar_num)
        except Exception as exc:
            print(f"ERROR [{topic_text!r}]: {exc}", file=sys.stderr)
            if len(queue) == 1:
                raise


if __name__ == "__main__":
    main()
