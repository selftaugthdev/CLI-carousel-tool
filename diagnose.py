"""Run this to see which image-generation models your Gemini key can access."""
import os
from dotenv import load_dotenv
load_dotenv()

from google import genai

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

print("Models supporting generateContent or generateImages:\n")
for m in client.models.list():
    actions = getattr(m, "supported_actions", None) or []
    if any(a in str(actions) for a in ("generateImage", "predict", "generateContent")):
        print(f"  {m.name}  —  {actions}")
