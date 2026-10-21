"""Approach 3: One tool call per round, up to three trials per call.

Run: python 03_graph_harness_inventory.py --trace YES
Needs: common.py, inventory.csv, and .env containing GROQ_API_KEY.

For each product, Groq freely chooses one tool per round.
The harness validates the tool against current Python state.
Each round contains up to three attempts at ONE action.
Any round that fails all three attempts skips the entire product.
"""

import argparse
import csv
import json
import math
import os

from dotenv import load_dotenv
from openai import OpenAI
from common import ROOT, DATA, OUTDIR, read_product, restock_row, print_report, save_report

# STEP 1 - SETUP
load_dotenv(ROOT / ".env")
parser = argparse.ArgumentParser()
parser.add_argument("--trace", choices=["YES", "NO"], default="YES")
args = parser.parse_args()
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
client = OpenAI(api_key=os.environ["GROQ_API_KEY"], base_url="https://api.groq.com/openai/v1")
MAX_ROUNDS = 8
MAX_TRIALS = 3


def pause(message):
    if args.trace == "YES":
        input(message + " Press Enter...")
    else:
        print(message)


# STEP 2 - REGISTER LOCAL FUNCTIONS
FUNCTIONS = {
    "read_product": read_product,
    "restock_row": restock_row,
    "print_report": print_report,
    "save_report": save_report,
}

# STEP 3 - DESCRIBE TOOLS TO LLM
# Here a small helper avoids repeating the tool JSON structure.
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
    tool("read_product", "Read a product by CSV data row number.", {
        "row_number": {"type": "integer", "description": "Data row starting at 1"}
    }),
    tool("restock_row", "Calculate restocking for the currently read product."),
    tool("print_report", "Print the completed report."),
    tool("save_report", "Save the completed report."),
]


def ask_llm(messages):
    pause("DECISION - Ask Groq to choose a tool.")
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
    )
    assistant = response.choices[0].message
    calls = assistant.tool_calls or []
    if len(calls) == 1:
        messages.append(assistant.model_dump(exclude_none=True))
    return calls


def send_result(messages, call, result):
    messages.append({
        "role": "tool",
        "tool_call_id": call.id,
        "content": json.dumps(result),
    })


# STEP 4 - COUNT PRODUCTS AND PREPARE REPORT
with open(DATA, newline="", encoding="utf-8-sig") as file:
    total_products = sum(1 for _ in csv.DictReader(file))

report = []
transcript = []
skipped = []
print("APPROACH 3 - INVENTORY GRAPH / HARNESS / LOOP")
print("Products:", total_products)
print("Structure: PRODUCT -> ROUND -> TRIAL")


# STEP 5 - PROCESS EACH PRODUCT
for row_number in range(1, total_products + 1):
    print(f"\n{'=' * 60}\nPRODUCT {row_number}/{total_products}")

    product = None
    product_id = ""
    completed = False
    feedback = "None"

    # Keep the same conversation across rounds and retries.
    messages = [
        {"role": "system", "content": (
            "You are choosing Python tools for one inventory product. "
            "Choose the most useful next tool for processing the product. "
            "You have access to the tool results and conversation history. "
            "Do not calculate inventory quantities or costs yourself. "
            "Select exactly one tool per response. "
            "Use error feedback to revise an unsuccessful request. "
            "Reporting is a separate task after all products are processed."
        )},
        {"role": "user", "content": f"Process CSV data row {row_number}."},
    ]

    # Each ROUND handles exactly ONE successful tool call.
    for round_number in range(1, MAX_ROUNDS + 1):
        print(f"\nROUND {round_number}/{MAX_ROUNDS} | Groq chooses the next tool")
        round_succeeded = False

        # Three trials for THIS tool call, not three full workflows.
        for trial in range(1, MAX_TRIALS + 1):
            print(f"  TRIAL {trial}/{MAX_TRIALS} | Feedback: {feedback}")
            pause("Start trial.")

            # Give context, but NEVER prescribe the tool name.
            messages.append({"role": "user", "content": (
                f"Continue processing CSV data row {row_number}. "
                f"Choose the next useful action. Feedback: {feedback}"
            )})

            try:
                calls = ask_llm(messages)
                if len(calls) != 1:
                    raise ValueError("Select exactly one tool call in this round.")

                call = calls[0]
                name = call.function.name
                params = json.loads(call.function.arguments or "{}")
                print("VALIDATION - Requested:", name, params)

                try:
                    # The LLM decides the tool; Python enforces valid state transitions.
                    if name == "read_product":
                        if params != {"row_number": row_number}:
                            raise ValueError(f"Use row_number={row_number}.")
                        pause("EXECUTION - Read CSV product.")
                        raw = FUNCTIONS[name](row_number)  # Read again on every retry.
                        product_id = raw.get("product_id", "")
                        raw["quantity"] = int(raw["quantity"])
                        raw["minimum_stock"] = int(raw["minimum_stock"])
                        raw["price"] = float(raw["price"])
                        if (raw["quantity"] < 0 or raw["minimum_stock"] < 0
                                or raw["price"] < 0 or not math.isfinite(raw["price"])):
                            raise ValueError("Invalid stock or price.")
                        product = raw  # Store only after successful read and conversion.
                        result = {"product": product}

                    elif name == "restock_row":
                        if product is None:
                            raise ValueError("Cannot calculate yet: no product has been read.")
                        if params:
                            raise ValueError("restock_row takes no arguments.")
                        pause("EXECUTION - Calculate restocking.")
                        result = FUNCTIONS[name](product)
                        report.append(result)
                        completed = True

                    else:
                        raise ValueError(
                            "This tool cannot run while processing an individual product."
                        )

                    round_succeeded = True
                    feedback = "None"
                    print("STATE UPDATE - Success:", result)

                except Exception as error:
                    feedback = str(error)
                    result = {"error": feedback}
                    print("FAILED ACTION:", feedback)

                transcript.append(
                    f"Product {row_number}, round {round_number}, "
                    f"trial {trial}: {name} -> {result}"
                )
                send_result(messages, call, result)

            except Exception as error:
                feedback = str(error)
                print("DECISION ERROR:", feedback)
                transcript.append(
                    f"Product {row_number}, round {round_number}, "
                    f"trial {trial}: ERROR - {feedback}"
                )
                messages.append({"role": "user", "content": f"Error: {feedback}"})

            if round_succeeded:
                print(f"ROUND {round_number} COMPLETE (trial {trial})")
                break  # End trials; next round handles the next tool call.

            if trial < MAX_TRIALS:
                pause("Retry this round with feedback. You can correct inventory.csv first.")

        if not round_succeeded:
            print(f"ROUND {round_number} FAILED -> SKIP ENTIRE PRODUCT")
            break  # Leave the rounds for this product.

        if completed:
            print("PRODUCT COMPLETED -> NEXT PRODUCT")
            break  # Two calls succeeded; no extra rounds.

    if not completed:
        if feedback == "None":
            feedback = f"Maximum {MAX_ROUNDS} rounds reached."
        skipped.append({
            "row": row_number + 1,
            "product_id": product_id,
            "reason": feedback,
            "trials": MAX_TRIALS,
        })
        transcript.append(f"Product {row_number}: SKIPPED - {feedback}")
        print("SKIPPED:", feedback)

    pause("Continue to next product.")


# STEP 6 - LET GROQ SELECT REPORTING TOOLS
print("\nREPORT PHASE - Groq selects print_report and save_report")
messages = [
    {"role": "system", "content": (
        "All products are finished. Call print_report and save_report, "
        "one at a time. Do not read or calculate more products."
    )},
    {"role": "user", "content": "Print and save the completed inventory report."},
]

printed = False
saved = False
for round_number in range(1, MAX_ROUNDS + 1):
    if printed and saved:
        break
    try:
        calls = ask_llm(messages)
        if not calls:
            break
        call = calls[0]
        name = call.function.name
        print("REPORT TOOL:", name)
        try:
            if name == "print_report":
                if not printed:
                    pause("EXECUTION - Print report.")
                    FUNCTIONS[name](report)
                    printed = True
                result = {"status": "printed"}
            elif name == "save_report":
                if not saved:
                    pause("EXECUTION - Save report.")
                    transcript.append("Report saved using Python")
                    FUNCTIONS[name]("03_graph_harness_inventory.csv", report, transcript)
                    saved = True
                result = {"status": "saved"}
            else:
                raise ValueError("Only reporting tools are allowed now.")
        except Exception as error:
            result = {"error": str(error)}
        send_result(messages, call, result)
    except Exception as error:
        print("Groq reporting error:", error)
        break


# STEP 7 - SAVE SKIPPED PRODUCTS
OUTDIR.mkdir(exist_ok=True)
skipped_file = OUTDIR / "03_graph_harness_inventory_skipped.csv"
with open(skipped_file, "w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=["row", "product_id", "reason", "trials"])
    writer.writeheader()
    writer.writerows(skipped)

print("\nDONE | Calculated:", len(report), "| Skipped:", len(skipped))
print("Printed:", printed, "| Saved:", saved)
print("Skipped rows saved to:", skipped_file)
