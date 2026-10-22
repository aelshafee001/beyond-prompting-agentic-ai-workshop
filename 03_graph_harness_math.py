
"""
Approach 3: Graph / Harness / Loop using Groq.

Run:
python 03_graph_harness_math.py --expression "12 + 8 * 3 - 10 / 5"
"""

import argparse
import json
import math
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

FOLDER = Path(__file__).resolve().parent
load_dotenv(FOLDER / ".env")

OUTDIR = FOLDER / "OUTPUT"
OUT = OUTDIR / "03_graph_harness_result.txt"


# ============================================================
# STEP 1 - LOCAL PYTHON FUNCTIONS
# ============================================================

def add(a, b):
    print(f"# EXECUTE NODE -> add({a}, {b})")
    return a + b


def subtract(a, b):
    print(f"# EXECUTE NODE -> subtract({a}, {b})")
    return a - b


def multiply(a, b):
    print(f"# EXECUTE NODE -> multiply({a}, {b})")
    return a * b


def divide(a, b):
    print(f"# EXECUTE NODE -> divide({a}, {b})")
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


FUNCTIONS = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
}


# ============================================================
# STEP 2 - COMMAND-LINE ARGUMENTS
# ============================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--expression",
    default="12 + 8 * 3 - 10 / 5"
)

parser.add_argument(
    "--model",
    default=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
)

parser.add_argument("--max-steps", type=int, default=10)
parser.add_argument("--max-retries", type=int, default=3)

args = parser.parse_args()

if args.max_steps < 1 or args.max_retries < 1:
    parser.error("max-steps and max-retries must be positive.")


# ============================================================
# STEP 3 - CREATE GROQ CLIENT
# ============================================================

if not os.getenv("GROQ_API_KEY"):
    raise SystemExit(
        "GROQ_API_KEY missing. "
        "Copy .env.example to .env and add your key."
    )

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


# ============================================================
# STEP 4 - GRAPH STATE
# ============================================================

history = []
feedback = "None."

retries = 0
step = 0
final_value = None

# Store successful operation records separately
operations = []

# The graph validates each proposed tool call, but does not independently
# calculate or certify the final numeric answer.


print("=" * 70)
print("APPROACH 3 - GRAPH / HARNESS / LOOP (GROQ)")
print("=" * 70)

print("Expression:", args.expression)
print("Model:", args.model)
print("Allowed functions:", ", ".join(FUNCTIONS))
print(
    "Max steps:", args.max_steps,
    "| Max retries:", args.max_retries
)

input("Press <Enter> to start...")


# ============================================================
# STEP 5 - DECISION NODE
# LLM proposes exactly one next action.
# ============================================================

def propose_next_action():

    print("\n**** DECISION NODE ****")
    print("# Building prompt and sending it to Groq...")

    input("Press <Enter> to send prompt...")

    history_text = (
        "\n".join(history)
        if history else "No operations yet."
    )

    prompt = f"""
    Original expression:
    {args.expression}

    Executed local operations:
    {history_text}

    Harness feedback from previous attempt:
    {feedback}
    """
    instructons="""
    You are a decision node,
    not the arithmetic executor.
    Return only valid JSON.
    You are the DECISION NODE.

    Propose exactly ONE next action.

    Allowed operations:
    add, subtract, multiply, divide.

    Rules:
    1. Follow standard arithmetic precedence.
    2. Multiplication (*), and division (/) have equal precedence,  before addition (+) and subtraction (-).
    3. Evaluate equal-precedence operators left to right.
    4. Do not execute arithmetic yourself.
    5. Use recorded local results in subsequent operations.
    6. Do not repeat already completed operations.
    7. Do not report completion before all operations finish.
    8. Return ONLY a valid JSON object.

    If another operation is needed, return:
    {{"done": false, "tool": "add", "a": 45, "b": 43}}

    If all operations are finished, return:
    {{"done": true, "final": 10}}
    """
    response = client.chat.completions.create(
        model=args.model,
        messages=[
            {
                "role": "system",
                "content": instructons
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={"type": "json_object"}
    )

    raw = (
        response.choices[0].message.content or ""
    ).strip()

    print("\n# LLM responded:")
    print(raw)

    input("Press <Enter> to continue...")

    try:
        return json.loads(raw), None

    except Exception as exc:
        return None, f"Invalid JSON: {exc}"


# ============================================================
# STEP 6 - VALIDATION NODE
# Harness checks LLM proposal before execution.
# ============================================================

def is_number(value):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
    )


def validate_action(action):

    print("\n**** VALIDATION NODE ****")
    input("Press <Enter> to validate action...")

    if not isinstance(action, dict):
        return False, "Action must be a JSON object."

    # --------------------------------------------------------
    # Case A - LLM reports completion
    # --------------------------------------------------------

    if action.get("done") is True:

        print("# Received DONE request.")

        final = action.get("final")

        if not is_number(final):
            return False, "Final result must be numeric."

        if not history:
            return False, (
                "Cannot finish before executing local operations."
            )

        # This demonstration trusts the LLM to identify the final result.
        # No independent arithmetic calculator or final-result comparison.
        return True, "Completion accepted (not independently verified)."

    # --------------------------------------------------------
    # Case B - LLM proposes a tool operation
    # --------------------------------------------------------

    print("# Received tool request.")

    if action.get("done") is not False:
        return False, "done must be true or false."

    if action.get("tool") not in FUNCTIONS:
        return False, "Unknown tool."

    a = action.get("a")
    b = action.get("b")

    if not is_number(a) or not is_number(b):
        return False, "a and b must be finite numbers."

    if action["tool"] == "divide" and b == 0:
        return False, (
            "Division by zero blocked by harness."
        )

    if step >= args.max_steps:
        return False, "Maximum execution steps reached."

    # Prevent repeated operations
    for previous in operations:
        if (
            previous["tool"] == action["tool"]
            and previous["a"] == a
            and previous["b"] == b
        ):
            return False, (
                "Operation already executed. "
                "Use previous result."
            )

    return True, "Action accepted."


# ============================================================
# STEP 7 - SIMPLE GRAPH LOOP (same idea as Approach 2)
# Each round: PROPOSE -> VALIDATE -> EXECUTE -> SAVE STATE.
# An invalid proposal goes back to PROPOSE, at most 3 attempts.
# ============================================================

while True:
    print("\n" + "#" * 80)
    print(f"GRAPH STEP {step + 1} | ATTEMPT {retries + 1}/{args.max_retries}")
    input("Press <Enter> to start this round...")

    # 1. DECISION: Ask Groq for ONE action (or a final answer).
    print("\n# 1. DECISION: Request next action from LLM")
    action, parse_error = propose_next_action()
    print("# Proposed action:", action)

    # 2. VALIDATION: Let the original validator check the proposal.
    print("\n# 2. VALIDATION: Check proposed action")
    if parse_error:
        valid, reason = False, parse_error
    else:
        valid, reason = validate_action(action)
    print("# Valid:", valid, "| Reason:", reason)

    # 3. INVALID: Save feedback and ask Groq again for this graph step.
    if not valid:
        retries += 1
        feedback = reason
        print(f"# INVALID -> FEEDBACK -> RETRY ({retries}/{args.max_retries})")
        if retries >= args.max_retries:
            raise SystemExit("Harness stopped: retry limit reached. No final report saved.")
        input("Press <Enter> to request another proposal...")
        continue

    # 4. DONE: No more tools; accept the reported result.
    if action["done"] is True:
        final_value = action["final"]
        print("# DONE -> FINAL REPORT (answer is not independently checked)")
        break

    # 5. EXECUTE: Run the existing local Python function.
    tool = action["tool"]
    a, b = action["a"], action["b"]
    print(f"\n# 3. EXECUTION: {tool}({a}, {b})")
    input("Press <Enter> to execute the local function...")
    try:
        result = FUNCTIONS[tool](a, b)
    except Exception as exc:
        retries += 1
        feedback = f"Execution error: {exc}"
        print(f"# EXECUTION ERROR -> RETRY ({retries}/{args.max_retries}): {feedback}")
        if retries >= args.max_retries:
            raise SystemExit("Harness stopped: retry limit reached. No final report saved.")
        input("Press <Enter> to request another proposal...")
        continue

    # 6. STATE UPDATE: Only successful operations change graph state.
    step += 1
    history.append(f"{step}. {tool}({a}, {b}) = {result}")
    operations.append({"tool": tool, "a": a, "b": b, "result": result})
    retries = 0
    feedback = "None."
    print(f"# 4. STATE UPDATE: {history[-1]}")
    print("# SUCCESS -> LOOP BACK TO DECISION")
    input("Press <Enter> for the next graph step...")


# ============================================================
# STEP 8 - FINAL OUTPUT
# ============================================================

print("=" * 100)
print("# FINAL RESULT")
print("# Expression:", args.expression)
print("# Final value reported by decision node:", final_value)

print("# Execution history:")

for line in history:
    print(" ", line)


# ============================================================
# STEP 9 - SAVE REPORT
# ============================================================

OUTDIR.mkdir(parents=True, exist_ok=True)

report = [
    f"Expression: {args.expression}",
    f"Model: {args.model}",
    "",
    "Execution history:",
    *history,
    "",
    f"Final value: {final_value}",
    "Harness status: COMPLETED (final answer not independently verified)"
]

OUT.write_text(
    "\n".join(report) + "\n",
    encoding="utf-8"
)

print("\nSaved:", OUT)
