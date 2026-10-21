"""Approach 2: Groq chooses Python tools to process an inventory.

Run: python 02_agentic_tools_inventory.py --trace YES
Requires: common.py, inventory.csv, and a .env file with GROQ_API_KEY.
"""

import argparse
import csv
import json
import os

from dotenv import load_dotenv
from openai import OpenAI
from common import ROOT, DATA, read_product, restock_row, print_report, save_report


# STEP 1 - SETUP
load_dotenv(ROOT / ".env")

parser = argparse.ArgumentParser()
parser.add_argument("--trace", choices=["YES", "NO"], default="YES")
args = parser.parse_args()

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


def pause(message):
    if args.trace == "YES":
        input(message + "  Press Enter...")
    else:
        print(message)


# STEP 2 - LOCAL PYTHON FUNCTIONS
FUNCTIONS = {
    "read_product": read_product,
    "restock_row": restock_row,
    "print_report": print_report,
    "save_report": save_report,
}


# STEP 3 - DESCRIBE THE TOOLS TO GROQ
def tool(name, description, properties=None):
    properties = properties or {}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    tool("read_product", "Read a CSV product by row number.", {
        "row_number": {"type": "integer", "description": "Data row starting at 1"}
    }),
    tool("restock_row", "Calculate restocking for the current product."),
    tool("print_report", "Print the completed inventory report."),
    tool("save_report", "Save the completed inventory report."),
]

print("Available tools:", ", ".join(FUNCTIONS))


def ask_LLM(messages):
    """Let LLM choose a tool, or decide that no tool is needed."""
    pause("Ask Groq to choose a tool.")
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
    )
    assistant = response.choices[0].message
    messages.append(assistant.model_dump(exclude_none=True))
    return assistant.tool_calls or []


def send_result(messages, call, result):
    """Give LLM the result of the Python function it requested."""
    messages.append({
        "role": "tool",
        "tool_call_id": call.id,
        "content": json.dumps(result),
    })


# STEP 4 - COUNT CSV ROWS
with open(DATA, newline="", encoding="utf-8-sig") as file:
    total_products = sum(1 for _ in csv.DictReader(file))

report = []
transcript = []


# STEP 5 - PROCESS EACH PRODUCT
for row_number in range(1, total_products + 1):
    print(f"\nPRODUCT {row_number} OF {total_products}")
    product = None
    finished = False

    messages = [
        {"role": "system", "content": (
            "You manage inventory using Python tools. "
            "First call read_product for the specified row. "
            "Then call restock_row. Never calculate costs yourself. "
            "Do not print or save the full report yet."
        )},
        {"role": "user", "content": f"Process product row {row_number}."},
    ]

    for round in range(8):
        calls = ask_LLM(messages)
        if not calls:
            print("No tool selected; skipping this product.")
            break
        pause(f"round {round+1},..")
        for call in calls:
            name = call.function.name
            params = json.loads(call.function.arguments or "{}")
            print("Groq selected:", name, params)

            try:
                if name == "read_product":
                    # Python controls which CSV row is processed.
                    if product is not None or params.get("row_number") != row_number:
                        raise ValueError("Read the current row only, once.")
                    pause("Execute read_product.")
                    product = FUNCTIONS[name](row_number)
                    product["quantity"] = int(product["quantity"])
                    product["minimum_stock"] = int(product["minimum_stock"])
                    product["price"] = float(product["price"])
                    if (product["quantity"] < 0 or product["minimum_stock"] < 0
                            or product["price"] < 0):
                        raise ValueError("Negative stock or price")
                    result = {"product": product}

                elif name == "restock_row":
                    if product is None:
                        raise ValueError("Read the product first.")
                    pause("Execute restock_row.")
                    result = FUNCTIONS[name](product)
                    report.append(result)
                    finished = True
                    print("Calculated:", result)

                else:
                    raise ValueError("Use reporting tools after all products.")

            except (ValueError, TypeError, KeyError, OverflowError) as error:
                result = {"error": str(error)}
                print("Tool error:", error)
                # Skip bad CSV numeric inputs without stopping the whole inventory.
                if name == "read_product" and product is not None:
                    finished = True

            transcript.append(f"Product {row_number}: {name} -> {result}")
            send_result(messages, call, result)

        if finished:
            break

    if not finished:
        print("Product not completed; moving to the next row.")
    pause("Next product.")


# STEP 6 - LET GROQ CHOOSE PRINT AND SAVE
messages = [
    {"role": "system", "content": (
        "All products are processed. Call print_report and save_report. "
        "Do not read or recalculate any product."
    )},
    {"role": "user", "content": "Print and save the inventory report."},
]

printed = False
saved = False

for round in range(8):
    if printed and saved:
        break

    calls = ask_LLM(messages)
    if not calls:
        break
    pause(f"round {round+1},..")
    for call in calls:
        name = call.function.name
        print("Groq selected:", name)
        if name == "print_report":
            if not printed:
                pause("Execute print_report.")
                FUNCTIONS[name](report)
                printed = True
            result = {"status": "printed"}

        elif name == "save_report":
            if not saved:
                pause("Execute save_report.")
                transcript.append("Saved inventory report")
                FUNCTIONS[name]("02_agentic_tools_inventory.csv", report, transcript)
                saved = True
            result = {"status": "saved"}

        else:
            result = {"error": "Only print_report and save_report are allowed now."}

        send_result(messages, call, result)

print(f"\nFinished: {len(report)} products calculated.")
print("Printed:", printed, "| Saved:", saved)
