from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    # List first 10 models
    count = 0
    for m in client.models.list():
        print(f"Model: {m.name}")
        count += 1
        if count >= 10:
            break
except Exception as e:
    print(f"Error: {e}")
