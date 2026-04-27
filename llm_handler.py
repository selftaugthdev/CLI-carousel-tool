import os
import json
import anthropic
from profiles import APP_PROFILES

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


SYSTEM_TEMPLATE = """\
You generate social media carousel copy for {app_name}.

TONE: {tone} — {persona_description}
BRAND: {branding_keywords}
COLORS: {primary_color} (primary), {footer_text_color} (text on footer)

Rules:
- Respond with valid JSON only. No markdown fences, no extra text.
- Generate exactly {num_slides} slides.
- Each slide: "headline" (≤40 characters, punchy — strict hard limit, keep it breathable), "body" (≤20 words), "image_prompt" (vivid AI image description matching brand style: {background_style}).
- Slide order: hook → problem → insight → solution → cta

JSON schema:
{{
  "slides": [
    {{"slide_number": 1, "type": "hook", "headline": "...", "body": "...", "image_prompt": "..."}}
  ]
}}
"""


def generate_copy(app_key: str, topic: str, num_slides: int = 5) -> list:
    profile = APP_PROFILES[app_key]
    system = SYSTEM_TEMPLATE.format(
        app_name=profile["name"],
        tone=profile["tone"],
        persona_description=profile["persona_description"],
        branding_keywords=profile["branding_keywords"],
        primary_color=profile["primary_color"],
        footer_text_color=profile["footer_text_color"],
        background_style=profile["background_style"],
        num_slides=num_slides,
    )

    msg = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": f"Topic: {topic}"}],
    )

    data = json.loads(msg.content[0].text.strip())
    return data["slides"]
