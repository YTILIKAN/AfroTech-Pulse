# pipeline/summarize.py — Agent résumé LLM (Mistral) : 3 lignes, angle africain, en français

import os

from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MODEL = "mistral-small-latest"

client = Mistral(api_key=MISTRAL_API_KEY)

