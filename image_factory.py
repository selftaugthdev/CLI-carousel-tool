"""Image generation providers. Each returns ONE Image for the whole carousel."""

import io
import os
import base64
from PIL import Image

# Source image sizes — generate larger than final canvas so crops have room to move
GEMINI_RATIOS = {"tiktok": "9:16", "insta": "4:5"}

# OpenAI supported sizes closest to our targets
OPENAI_SIZES = {"tiktok": "1024x1792", "insta": "1024x1024"}


class ProviderGemini:
    """Imagen 4 via google-genai. Switch MODEL to imagen-4.0-fast-generate-001 to save cost."""

    MODEL = "imagen-4.0-generate-001"

    def __init__(self):
        from google import genai
        from google.genai import types as genai_types

        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self._types = genai_types

    def generate(self, prompt: str, platform: str) -> Image.Image:
        response = self._client.models.generate_images(
            model=self.MODEL,
            prompt=prompt,
            config=self._types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=GEMINI_RATIOS[platform],
                safety_filter_level="block_low_and_above",
            ),
        )
        image_bytes = response.generated_images[0].image.image_bytes
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")


class ProviderOpenAI:
    """GPT-Image-2 — gpt-image-1 via OpenAI."""

    MODEL = "gpt-image-1"

    def __init__(self):
        from openai import OpenAI

        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def generate(self, prompt: str, platform: str) -> Image.Image:
        size = OPENAI_SIZES[platform]
        response = self._client.images.generate(
            model=self.MODEL,
            prompt=prompt,
            size=size,
            n=1,
            output_format="png",
        )
        image_bytes = base64.b64decode(response.data[0].b64_json)
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Pad 1024x1024 to ~4:5 for Instagram
        if platform == "insta" and img.size == (1024, 1024):
            target_h = int(1024 * 5 / 4)
            padded = Image.new("RGB", (1024, target_h), (0, 0, 0))
            padded.paste(img, (0, (target_h - 1024) // 2))
            img = padded

        return img


PROVIDERS = {"gemini": ProviderGemini, "openai": ProviderOpenAI}


def get_provider(name: str):
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider '{name}'. Choose: {list(PROVIDERS)}")
    return PROVIDERS[name]()
