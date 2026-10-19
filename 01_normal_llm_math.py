
"""Approach 1: Normal LLM using Groq.
Run:
python 01_normal_llm_math.py --expression "12 + 8 * 3 - 10 / 5"
"""

import argparse
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

FOLDER = Path(__file__).resolve().parent
load_dotenv(FOLDER / ".env")

OUTDIR = FOLDER / "OUTPUT"
OUT = OUTDIR / "01_normal_llm_result.txt"

parser = argparse.ArgumentParser()
parser.add_argument(
    "--expression",
    default="12 + 8 * 3 - 10 / 5"
)
parser.add_argument(
    "--model",
    default=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
)
args = parser.parse_args()

# Load Groq API key from .env file
if not os.getenv("GROQ_API_KEY"):
    raise SystemExit(
        "GROQ_API_KEY missing. "
        "Copy .env.example to .env and add your key."
    )

# Create Groq client using OpenAI-compatible API
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

print("=" * 70)
print("APPROACH 1 - NORMAL LLM (GROQ)")
print("=" * 70)
print("Expression:", args.expression)
print("Model:", args.model)
print("LLM calculates directly; no local math tools are exposed.\n")

print("#" * 100)
print("# Create main prompt and send it to LLM")

response = client.chat.completions.create(
    model=args.model,
    messages=[
        {
            "role": "system",
            "content": (
                "Calculate carefully. "
                "Give the final numeric answer and short steps. "
                "If the expression is mathematically undefined, "
                "explain why."
            )
        },
        {
            "role": "user",
            "content": f"Calculate: {args.expression}"
        }
    ]
)

print(f"response={response}")

input("Press <Enter> to continue...")

# Extract text from Groq response
text = (response.choices[0].message.content or "").strip()

print(f"response = {text}")

# Create output folder if it does not exist
OUTDIR.mkdir(parents=True, exist_ok=True)

# Save LLM reply
OUT.write_text(text + "\n", encoding="utf-8")

print("\nSaved:", OUT)
