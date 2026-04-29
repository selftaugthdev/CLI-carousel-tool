PILLARS = {
    "migraine_cast": {
        1: {
            "name": "Emotional Validation",
            "audience": "Migraine sufferers",
            "content_guidance": "Personal experiences, social situations, invisible symptoms, the emotional cost of living with migraines, being dismissed or misunderstood",
            "accent_color": "#E91E63",
            "slide_color_cycle": [
                {"bg": "#FFD6E0", "hl": "#1A1A1A", "body": "#5D2E46"},
                {"bg": "#2D1B5E", "hl": "#FFFFFF",  "body": "#D4B8FF"},
                {"bg": "#2D3748", "hl": "#FFFFFF",  "body": "#E2E8F0"},
            ],
            "background_style": "cinematic moody storm clouds, deep purple and midnight blue, barometric pressure visualization, dramatic atmospheric lighting, minimalist 8k",
        },
        2: {
            "name": "Educational / Warning",
            "audience": "Migraine sufferers seeking information",
            "content_guidance": "Triggers, surprising symptom-related content, warning signs, things doctors don't always explain",
            "accent_color": "#39FF14",
            "slide_color_cycle": [
                {"bg": "#0D1117", "hl": "#39FF14", "body": "#E0E0E0"},
                {"bg": "#1A1A2E", "hl": "#FFFFFF",  "body": "#B0BEC5"},
                {"bg": "#16213E", "hl": "#FFFFFF",  "body": "#90A4AE"},
            ],
            "background_style": "stormy dark atmospheric sky, deep navy near-black, dramatic lightning, ultra high contrast, cinematic 8k",
        },
        3: {
            "name": "Caregiver",
            "audience": "Partners, parents, friends of migraine sufferers",
            "content_guidance": "How to help, what not to say, what living with migraines looks like from the outside",
            "accent_color": "#4ECDC4",
            "slide_color_cycle": [
                {"bg": "#1A3A4A", "hl": "#4ECDC4", "body": "#E0F0EE"},
                {"bg": "#0F2637", "hl": "#FFFFFF",  "body": "#B2D8D8"},
                {"bg": "#2C3E50", "hl": "#FFFFFF",  "body": "#95A5A6"},
            ],
            "background_style": "warm calm home interior, soft natural window light, grounded peaceful atmosphere, cinematic 8k",
        },
    },
    "calm_sos": {
        1: {
            "name": "Emotional Validation",
            "audience": "Anxiety and panic attack sufferers",
            "content_guidance": "Specific physical sensations, social situations caused by anxiety, moments of overwhelm",
            "accent_color": "#9B59F7",
            "slide_color_cycle": [
                {"bg": "#CE9FFC", "hl": "#1A1A1A", "body": "#2D1B5E"},
                {"bg": "#2D1B5E", "hl": "#FFFFFF",  "body": "#D4B8FF"},
                {"bg": "#4B527E", "hl": "#FFFFFF",  "body": "#E8EDFF"},
            ],
            "background_style": "cinematic moody twilight sky, deep lavender and indigo storm clouds, ethereal soft light, dramatic atmosphere, ultra high contrast",
        },
        2: {
            "name": "Educational / Techniques",
            "audience": "People seeking coping tools",
            "content_guidance": "Breathing techniques, grounding methods, what anxiety actually is biologically",
            "accent_color": "#7B2FBE",
            "slide_color_cycle": [
                {"bg": "#0D0D1A", "hl": "#CE9FFC", "body": "#E8EDFF"},
                {"bg": "#1A0A2E", "hl": "#FFFFFF",  "body": "#D4B8FF"},
                {"bg": "#2D1B5E", "hl": "#FFFFFF",  "body": "#B8A4E8"},
            ],
            "background_style": "minimal dark space, soft purple gradient, clean abstract calm, cinematic 8k",
        },
        3: {
            "name": "Caregiver / Support",
            "audience": "People who love someone with anxiety",
            "content_guidance": "How to help, what not to say, what anxiety looks like from the outside",
            "accent_color": "#C77DFF",
            "slide_color_cycle": [
                {"bg": "#2D1B3D", "hl": "#C77DFF", "body": "#E8DCFF"},
                {"bg": "#1A1030", "hl": "#FFFFFF",  "body": "#D4B8FF"},
                {"bg": "#3D2B50", "hl": "#FFFFFF",  "body": "#C4A8E8"},
            ],
            "background_style": "warm soft candlelit dark interior, gentle comfort atmosphere, cinematic 8k",
        },
    },
}


APP_PROFILES = {
    "calm_sos": {
        "name": "Calm SOS",
        "logo_path": "assets/Calm SOS LOGO.png",
        "primary_color": "#CE9FFC",       # Soft lavender — slides 2-4 background
        "accent_color": "#9B59F7",         # Purple — bars, counters, accents
        "footer_text_color": "#4B527E",    # Muted dusty indigo — headlines
        "body_text_color": "#FFF8DC",      # Cream — body copy on brand slides
        "branding_keywords": "Lavender Lounge",
        "tone": "Empathetic",
        "persona_description": (
            "You are a warm, empathetic friend who truly understands anxiety and stress. "
            "Speak softly, validate feelings, and gently guide toward calm. "
            "Never clinical — always human and reassuring."
        ),
        "background_style": (
            "cinematic moody twilight sky, deep lavender and indigo storm clouds, "
            "ethereal soft light, dramatic atmosphere, ultra high contrast"
        ),
        "tiktok_handle": "@calmsos.app",
        "topic_list": "assets/Calm_SOS_90_Topics.md",
        "cta_tagline": "Real-time tools built for the exact moment panic starts — not after.",
        "cta_download": "Download Calm SOS free on the App Store. Link in bio.",
        "caption_cta": "Panic is physical. Your recovery should be too.  Join the thousands who finally found their 'Off Switch.' Calm SOS is free to download. Link in bio.",
    },
    "migraine_cast": {
        "name": "MigraineCast",
        "logo_path": "assets/New LOGO MigraineCast.png",
        "primary_color": "#FFD6E0",        # Pastel petal pink — slides 2-4 background
        "accent_color": "#E91E63",          # Hot pink — bars, counters, accents
        "footer_text_color": "#5D2E46",    # Deep mauve — headlines
        "body_text_color": "#FFF0F3",      # Blush white — body copy
        "branding_keywords": "Modern Medical",
        "tone": "Clinical/Expert",
        "persona_description": (
            "You are a knowledgeable medical expert who cuts through the noise. "
            "Be precise, evidence-based, and authoritative yet accessible. "
            "Tone: Empathetic, Scientific, Blunt."
        ),
        "background_style": (
            "cinematic moody storm clouds, deep purple and midnight blue, "
            "barometric pressure visualization, dramatic atmospheric lighting, minimalist 8k"
        ),
        "tiktok_handle": "@migrainecast",
        "topic_list": "assets/MigraineCast-Topic_Master_List.md",
        "cta_tagline": "Science-backed forecasts. Real predictions. Real relief.",
        "cta_download": "Download MigraineCast free on the App Store. Link in bio.",
        "caption_cta": "Stop guessing. Start predicting.  Take your life back from the weather. Download MigraineCast for free (Link in Bio).",
    },
}
