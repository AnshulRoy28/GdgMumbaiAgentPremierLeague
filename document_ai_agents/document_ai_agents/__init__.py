import os
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

if (Path(__file__).parents[1] / ".env").is_file():
    load_dotenv(dotenv_path=Path(__file__).parents[1] / ".env")


api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key, transport="rest")
else:
    print("WARNING: GOOGLE_API_KEY and GEMINI_API_KEY are missing from environment.")
