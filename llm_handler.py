"""Gemini-powered carousel content generator — one master call, full 6-slide JSON."""

import json
import os
from google import genai
from google.genai import types as genai_types
from profiles import APP_PROFILES

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


MASTER_PROMPT = """\
Act as a viral TikTok creator and expert on {topic_domain}.
Generate a 6-slide carousel JSON for: "{topic}"

App: {app_name}
Tone: {tone} — {persona_description}
Brand: {branding_keywords}

STRICT RULES:
- slide 1 → "neon_word": exactly 1 ALL-CAPS word. "hook": ≤12 words, punchy.
- slides 2-4 → "header": ≤4 words, ALL CAPS. "body": ≤20 words (slide 4 MUST be 25-30 words for dwell time).
- slide 5 → "summary_title": ≤3 words ALL CAPS. "checklist": 4-5 short action items.
- slide 6 → "cta": ≤20 words, first-person, urgent.
- "image_prompt": cinematic, moody, high-contrast scene. Style: {background_style}. 8k, minimalist.
- "caption": 120-150 words, SEO-optimised, ends with 5 relevant hashtags on their own line.
  Caption rules: (1) First line = hook sentence optimised for TikTok search indexing. (2) Explain the biological or scientific WHY — make the reader feel they just learned something. (3) Link the problem to a specific feature or use case in {app_name}. (4) Always name the app as "{app_name}" — never "the app", "our app", or a community nickname. (5) NEVER use generic therapeutic phrases like "be gentle with yourself", "you are enough", "your mental wellness is paramount", or "always here for you". (6) Separate each paragraph with \\n\\n so the text is NOT one block. Hashtags go on their own paragraph at the end.

Return ONLY valid JSON — no markdown fences, no explanation.

{{
  "image_prompt": "...",
  "slides": [
    {{"neon_word": "WORD", "hook": "..."}},
    {{"header": "HEADER", "body": "..."}},
    {{"header": "HEADER", "body": "..."}},
    {{"header": "HEADER", "body": "25-30 word body here..."}},
    {{"summary_title": "TITLE", "checklist": ["item 1", "item 2", "item 3", "item 4"]}},
    {{"cta": "..."}}
  ],
  "caption": "..."
}}
"""

TOPIC_DOMAINS = {
    "migraine_cast": "migraine science, barometric pressure, and neurology",
    "calm_sos": "anxiety, panic attacks, and mental wellness",
}


def generate_carousel(app_key: str, topic: str) -> dict:
    profile = APP_PROFILES[app_key]
    prompt = MASTER_PROMPT.format(
        topic_domain=TOPIC_DOMAINS.get(app_key, "health and wellness"),
        topic=topic,
        app_name=profile["name"],
        tone=profile["tone"],
        persona_description=profile["persona_description"],
        branding_keywords=profile["branding_keywords"],
        background_style=profile["background_style"],
    )

    response = _get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.85,
        ),
    )

    data = json.loads(response.text)

    # Ensure we always have exactly 6 slides
    slides = data.get("slides", [])
    while len(slides) < 6:
        slides.append({})
    data["slides"] = slides[:6]

    # Protocol slide (index 4): last checkpoint always "Use <App Name>"
    checklist = data["slides"][4].get("checklist", [])
    if checklist:
        checklist[-1] = f"Use {profile['name']}"
    elif checklist == []:
        checklist = [f"Use {profile['name']}"]
    data["slides"][4]["checklist"] = checklist

    return data
