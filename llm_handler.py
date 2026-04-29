"""Gemini-powered carousel content generator — two-phase: hooks then carousel."""

import json
import os
from google import genai
from google.genai import types as genai_types
from profiles import APP_PROFILES, PILLARS

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


TOPIC_DOMAINS = {
    "migraine_cast": "migraine science, barometric pressure, and neurology",
    "calm_sos": "anxiety, panic attacks, and mental wellness",
}

_MIGRAINECAST_HOOK_RULES = """\
HOOK RULES — MigraineCast:
- HARD RULE: Every hook MUST be a full sentence of at least 5 words. Single-word hooks are FORBIDDEN.
  Before including any hook, count its words. If the count is 1, discard it and write a replacement.
- Must create tension, curiosity, or instant recognition in the reader
- No generic health copy, no clinical language
- Write like someone who lives with migraines, not a brand

Use one hook per formula:
Formula 1 — The overlooked truth: something obvious that migraine sufferers keep missing or being told wrong
Formula 2 — The specific moment: second-person, describes an exact situation the reader has lived
Formula 3 — The reframe: takes something the reader already believes and flips it slightly"""

_CALM_SOS_HOOK_RULES = """\
HOOK RULES — Calm SOS:
- Can be ONE emotionally loaded word OR a full sentence
- One-word hooks must describe a feeling the reader already knows — NOT label the topic
- Good one-word hooks: CRASH, BREATHE, DISMISSED, INVISIBLE, AGAIN, STILL, HIDDEN
- Bad one-word hooks: ANXIETY, PANIC, STRESS (topic labels, not feelings)
- Write like someone who lives with anxiety, not a brand

Use one hook per formula:
Formula 1 — The overlooked truth
Formula 2 — The specific moment (second-person, exact situation the reader has lived)
Formula 3 — The reframe (flip something the reader already believes)"""

_HOOKS_PROMPT = """\
Generate exactly 3 hook options for a TikTok carousel.

App: {app_name}
Topic: {topic}
Pillar: {pillar_name}
Audience: {audience}
Content focus: {content_guidance}

{hook_rules}

For each hook provide:
- hook: the hook text
- formula: which formula it uses
- tension: what tension or curiosity it creates and why
- emotion: the specific emotion it targets in the reader

Return ONLY a valid JSON array — no markdown fences, no explanation.
[{{"hook": "...", "formula": "...", "tension": "...", "emotion": "..."}}, ...]
"""

_CAROUSEL_PROMPT = """\
Act as a viral TikTok creator for {app_name}.
Generate a 6-slide carousel JSON.

App: {app_name} ({topic_domain})
Topic: {topic}
Pillar: {pillar_name} — {content_guidance}
Audience: {audience}
Tone: {tone} — {persona_description}
Chosen hook — use this EXACTLY as the "hook" field on slide 1: "{chosen_hook}"

CONTENT RULES:
- Write like someone who lives with the condition, never like a health brand
- Second-person present tense: "You cancelled again and told no one why"
- Specific physical and social experiences the audience recognises instantly
- Slides 2-4: deepen the emotional experience — make the reader feel seen, not educated
- NEVER write Wikipedia-style descriptions ("migraines present with pulsating pain")
- No filler: "did you know", "in conclusion", "it's important to"
- No generic therapeutic phrases: "be gentle with yourself", "you are enough"
- No em-dashes (—). Use a period or rewrite the sentence instead.

SLIDE RULES:
- slide 1 → "neon_word": 1 ALL-CAPS emotionally loaded word (a feeling, NOT a topic label). "hook": the chosen hook text EXACTLY.
- slides 2-4 → "header": ≤4 words ALL CAPS. "body": ≤20 words, emotional and specific. (slide 4 MUST be 25-30 words for dwell time)
- slide 5 → "summary_title": ≤3 words ALL CAPS. "checklist": 4-5 action items.
  HARD RULE for slide 5: Before writing the checklist, re-read slides 2-4. Every step must be a direct response to the specific frustration, moment, or experience described there. If the carousel is about cancelling plans, the steps reference reclaiming control over social life. If it is about food triggers, the steps reference food specifically. Generic advice that could appear on any health website is forbidden. Each step should make the reader feel this protocol was written for their exact situation, not copy-pasted from a general checklist.
- slide 6 → "cta": ≤20 words. Flows naturally from the carousel — the app earns its place, never forced.
- "image_prompt": {background_style}. Ultra cinematic, 8k, high contrast.
- "caption": 120-150 words, SEO-optimised, ends with 5 relevant hashtags on their own line.
  Caption rules: (1) First line = hook sentence for TikTok search indexing. (2) Explain the biological or scientific WHY. (3) Link the problem to a specific feature or use case in {app_name}. (4) Always name "{app_name}" — never "the app" or a community nickname. (5) No generic therapeutic phrases. (6) Separate paragraphs with \\n\\n — not one block. Hashtags on their own paragraph at the end. (7) No em-dashes (—).

Return ONLY valid JSON — no markdown fences, no explanation.

{{
  "image_prompt": "...",
  "slides": [
    {{"neon_word": "WORD", "hook": "{chosen_hook}"}},
    {{"header": "HEADER", "body": "..."}},
    {{"header": "HEADER", "body": "..."}},
    {{"header": "HEADER", "body": "25-30 word body..."}},
    {{"summary_title": "TITLE", "checklist": ["item 1", "item 2", "item 3", "item 4"]}},
    {{"cta": "..."}}
  ],
  "caption": "..."
}}
"""


def generate_hooks(app_key: str, topic: str, pillar_num: int) -> list:
    """Phase 1 — return 3 hook options as a list of dicts."""
    profile = APP_PROFILES[app_key]
    pillar  = PILLARS[app_key][pillar_num]
    hook_rules = _MIGRAINECAST_HOOK_RULES if app_key == "migraine_cast" else _CALM_SOS_HOOK_RULES

    prompt = _HOOKS_PROMPT.format(
        app_name=profile["name"],
        topic=topic,
        pillar_name=pillar["name"],
        audience=pillar["audience"],
        content_guidance=pillar["content_guidance"],
        hook_rules=hook_rules,
    )

    for attempt in range(3):
        response = _get_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.9,
            ),
        )
        hooks = json.loads(response.text)[:3]

        if app_key == "migraine_cast":
            bad = [h for h in hooks if len(h.get("hook", "").split()) < 2]
            if not bad:
                break
            if attempt < 2:
                print(f"  Single-word hook detected — retrying (attempt {attempt + 2}/3)…")
        else:
            break

    return hooks


def generate_carousel(app_key: str, topic: str, pillar_num: int, chosen_hook: str) -> dict:
    """Phase 2 — generate full 6-slide carousel with pillar and hook locked in."""
    profile = APP_PROFILES[app_key]
    pillar  = PILLARS[app_key][pillar_num]

    prompt = _CAROUSEL_PROMPT.format(
        app_name=profile["name"],
        topic_domain=TOPIC_DOMAINS.get(app_key, "health and wellness"),
        topic=topic,
        pillar_name=pillar["name"],
        content_guidance=pillar["content_guidance"],
        audience=pillar["audience"],
        tone=profile["tone"],
        persona_description=profile["persona_description"],
        chosen_hook=chosen_hook,
        background_style=pillar["background_style"],
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

    slides = data.get("slides", [])
    while len(slides) < 6:
        slides.append({})
    data["slides"] = slides[:6]

    # Lock hook on slide 1 exactly as chosen
    data["slides"][0]["hook"] = chosen_hook

    # Protocol slide (index 4): last checkpoint always "Use <App Name>"
    checklist = data["slides"][4].get("checklist", [])
    if checklist:
        checklist[-1] = f"Use {profile['name']}"
    else:
        checklist = [f"Use {profile['name']}"]
    data["slides"][4]["checklist"] = checklist

    return data
