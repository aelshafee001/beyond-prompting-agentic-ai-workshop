
"""
Approach 2: Agentic LLM with local Python tools using Groq.

Run:
python 02_agentic_math_tools.py --expression "12 + 8 * 3 - 10 / 5"
"""

import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

FOLDER = Path(__file__).resolve().parent
load_dotenv(FOLDER / ".env")

OUTDIR = FOLDER / "OUTPUT"
OUT = OUTDIR / "02_agentic_tools_result.txt"


# ============================================================
# STEP 1 - LOCAL PYTHON FUNCTIONS
# These functions execute on the user's computer.
# ============================================================

def add(a, b):
    print(f"LOCAL PYTHON FUNCTION: add({a}, {b})")
    return a + b


def subtract(a, b):
    print(f"LOCAL PYTHON FUNCTION: subtract({a}, {b})")
    return a - b


def multiply(a, b):
    print(f"LOCAL PYTHON FUNCTION: multiply({a}, {b})")
    return a * b


def divide(a, b):
    print(f"LOCAL PYTHON FUNCTION: divide({a}, {b})")
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
# STEP 2 - DEFINE TOOLS FOR THE LLM
# The LLM sees descriptions, not Python implementations.
# ============================================================

def binary_tool(name, description):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
                "additionalProperties": False,
            },
        },
    }


TOOLS = [
    binary_tool("add", "Return a + b."),
    binary_tool("subtract", "Return a - b."),
    binary_tool("multiply", "Return a * b."),
    binary_tool("divide", "Return a / b; b must not be zero."),
]


# ============================================================
# STEP 3 - COMMAND-LINE ARGUMENTS
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

args = parser.parse_args()


# ============================================================
# STEP 4 - CREATE GROQ CLIENT
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
# STEP 5 - SYSTEM INSTRUCTIONS AND MESSAGES
# ============================================================

instructions = (
    "You are an agentic calculator. "
    "You MUST use the supplied tools for every arithmetic operation. "
    "Do not calculate arithmetic mentally. "
    "Follow standard arithmetic precedence: multiplication and "
    "division before addition and subtraction, left to right "
    "for operators with equal precedence. "
    "Use returned results as inputs to later calls. "
    "If a tool returns an error such as division by zero, "
    "explain the error and do not invent a numeric result."
)

# Groq Chat Completions uses messages to preserve context.
messages = [
    {
        "role": "system",
        "content": instructions
    },
    {
        "role": "user",
        "content": (
            f"Calculate using only the tools: {args.expression}"
        )
    }
]


print("=" * 70)
print("APPROACH 2 - AGENTIC LLM WITH LOCAL TOOLS (GROQ)")
print("=" * 70)
print("Expression:", args.expression)
print("Model:", args.model)

print("#" * 100)
print("# Sending initial prompt and tool definitions to Groq")

input("Press <Enter> to start execution...")


# ============================================================
# STEP 6 - INITIAL LLM REQUEST
# ============================================================

response = client.chat.completions.create(
    model=args.model,
    messages=messages,
    tools=TOOLS,
    tool_choice="auto"
)


# Logbook for recording all tool executions
transcript = []
final_text = ""


# ============================================================
# STEP 7 - AGENTIC EXECUTION LOOP
# Maximum 12 rounds
# ============================================================

for round_number in range(1, 13):

    print("#" * 100)
    print(f"# Starting round number = {round_number}")

    # Retrieve the assistant's response
    assistant_message = response.choices[0].message

    # Extract requested function calls
    calls = assistant_message.tool_calls or []

    # --------------------------------------------------------
    # Case A - LLM finishes without requesting more tools
    # --------------------------------------------------------

    if not calls:

        final_text = (assistant_message.content or "").strip()

        print(
            f"# No tool calls. LLM finished in round "
            f"{round_number}"
        )

        print(f"\nFINAL ANSWER:\n{final_text}")

        transcript.append(
            "\nFINAL ANSWER:\n" + final_text
        )

        break

    # --------------------------------------------------------
    # Case B - LLM requests one or more local tools
    # --------------------------------------------------------

    # Save assistant message containing tool requests
    messages.append(
        assistant_message.model_dump(exclude_none=True) 
        #Converts the response object into a Python dictionary
    )

    for call in calls:

        function_name = call.function.name
        arguments = call.function.arguments

        try:
            values = json.loads(arguments)

            if function_name not in FUNCTIONS:

                result = {"error": "Tool not allowed"}

            else:

                # Validate arguments before executing Python
                a = values["a"]
                b = values["b"]

                #if (
                #    isinstance(a, bool)
                #    or isinstance(b, bool)
                #    or not isinstance(a, (int, float))
                #    or not isinstance(b, (int, float))
                #):
                #    raise ValueError(
                #        "Tool arguments must be numeric."
                #    )

                print(
                    f"# ROUND {round_number}: "
                    f"LLM DECIDED TO CALL -> "
                    f"{function_name}({a}, {b})"
                )

                input("Press <Enter> to execute the tool...")

                # Actual execution takes place locally
                value = FUNCTIONS[function_name](a, b)

                result = {"result": value}

                print(f"# Local Python result = {result}")

        except Exception as exc:

            result = {"error": str(exc)}

            print(f"# Tool execution error: {exc}")

        # Record execution in transcript
        transcript.append(
            f"Round {round_number}: "
            f"{function_name}({arguments}) -> {result}"
        )

        # Send the result back to the LLM as a tool message
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(result),
        })

    # --------------------------------------------------------
    # STEP 8 - SEND TOOL RESULTS BACK TO GROQ
    # --------------------------------------------------------

    print("# Preparing next LLM request...")
    print("# Sending local tool results to Groq")

    input("Press <Enter> to continue to the next LLM call...")

    response = client.chat.completions.create(
        model=args.model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )

else:

    transcript.append(
        "\nSTOPPED: Maximum tool rounds reached."
    )

    print("Stopped: maximum tool rounds reached.")


# ============================================================
# STEP 9 - SAVE EXECUTION TRANSCRIPT
# ============================================================

OUTDIR.mkdir(parents=True, exist_ok=True)

OUT.write_text(
    "\n".join(transcript) + "\n",
    encoding="utf-8"
)

print("\nSaved:", OUT)
