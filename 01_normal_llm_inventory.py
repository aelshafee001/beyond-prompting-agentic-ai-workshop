"""Approach 1: Normal LLM analyzes inventory without Python tools.

Run: python 01_normal_llm_inventory.py --trace YES
Needs: common.py, inventory.csv, and .env containing GROQ_API_KEY.

Python loads and saves data. Groq calculates the restocking report itself.
No functions or tool definitions are sent to the LLM.
"""

import argparse
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from common import ROOT, load_inventory, print_report, save_report


# STEP 1 - SETUP (same style as Approach 2)
load_dotenv(ROOT / ".env")

parser = argparse.ArgumentParser()
parser.add_argument("--trace", choices=["YES", "NO"], default="YES")
args = parser.parse_args()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
if not os.getenv("GROQ_API_KEY"):
    raise SystemExit("GROQ_API_KEY missing from .env")

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)


def pause(message):
    """Pause during the live demonstration, or just print the step."""
    if args.trace == "YES":
        input(message + "  Press Enter...")
    else:
        print(message)


# STEP 2 - ASK LLM (NO TOOL CALLING)
def ask_LLM(messages):
    """Send the inventory to LLM and return its written answer."""
    pause("Ask LLM to analyze the inventory.")
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    assistant = response.choices[0].message
    messages.append({"role": "assistant", "content": assistant.content or ""})
    return (assistant.content or "").strip()


# STEP 3 - READ INVENTORY
print("=" * 65)
print("APPROACH 1 - NORMAL LLM INVENTORY (NO TOOLS)")
print("=" * 65)

pause("Read inventory.csv.")
products = load_inventory()

if not products:
    raise SystemExit("No valid inventory products found.")

# Prices can be floats or Decimal values; turn them into JSON-friendly strings.
records = []
for product in products:
    record = product.copy()
    #record["price"] = str(product["price"])
    records.append(record)

print("Products loaded:", len(records))


# STEP 4 - SEND PRODUCTS TO THE NORMAL LLM
instructions = (
    "You are an inventory assistant. Calculate restocking for every product. "
    "needs_restock = quantity < minimum_stock. "
    "units_to_order = max(0, minimum_stock - quantity). "
    "estimated_cost_egp = units_to_order * price, formatted to 2 decimals. "
    "Return ONLY a JSON array in the same order, with these fields for each item: "
    "product_id, name, needs_restock, units_to_order, estimated_cost_egp. "
    "Do not invent or omit products."
)

messages = [
    {"role": "system", "content": instructions},
    {"role": "user", "content": "Analyze these products:\n" + json.dumps(records)},
]

answer = ask_LLM(messages)
print("\nLLM ANSWER:\n", answer)


# STEP 5 - READ THE JSON RESPONSE
pause("Convert LLM's answer into a Python report.")

# Remove Markdown fences if the LLM added them.
if answer.startswith("```"):
    answer = "\n".join(answer.splitlines()[1:-1]).strip()

try:
    report = json.loads(answer)
    if not isinstance(report, list) or len(report) != len(products):
        raise ValueError("Expected one JSON result per inventory product.")
except (ValueError, TypeError) as error:
    raise SystemExit("Invalid LLM report: " + str(error))


# STEP 6 - PRINT AND SAVE (NORMAL LOCAL PYTHON, NOT LLM TOOLS)
pause("Print LLM's inventory report.")
print_report(report)

pause("Save the report and LLM response.")
save_report("01_normal_llm_inventory.csv", report, ["Model: " + MODEL, answer])
print("Finished:", len(report), "products analyzed.")

# Note: Python only parses and displays the reply; it does not verify LLM math.
