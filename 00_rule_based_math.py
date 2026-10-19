
"""Approach 0: Rule-Based Execution ."""
# python 00_rule_based_math.py --expression "12 + 8 * 3 - 10 / 5"

import argparse
import re #built-in Regular Expressions (regex) module
from pathlib import Path

FOLDER = Path(__file__).resolve().parent
OUTDIR = FOLDER / "OUTPUT"
OUT = OUTDIR / "00_rule_based_result.txt"


# build local functions 
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
        raise ValueError("Division by zero")
    return a / b


FUNCTIONS = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
}

OPERATORS = {
    "+": "add",
    "-": "subtract",
    "*": "multiply",
    "/": "divide",
}


# PYTHON RULE-BASED DECISION

def decide_next_call(tokens):

    # Check high-priority operations first
    for operators in ["*/", "+-"]:

        for i in range(len(tokens)):

            if tokens[i] in operators:

                operator = tokens[i]

                a = float(tokens[i - 1])
                b = float(tokens[i + 1])

                name = OPERATORS[operator]

                return i, name, a, b

    return None

# Convert expression into numbers and operators
def parse_expression(expression):

    expression = expression.replace(" ", "")
    # Add spaces around every operator
    for op in ["+", "-", "*", "/"]:
        expression = expression.replace(op, f" {op} ")
    # breaks a string into separate pieces wherever whitespace appears.
    return expression.split()


parser = argparse.ArgumentParser()
parser.add_argument(
    "--expression",
    default="12 + 8 * 3 - 10 / 5"
)
parser.add_argument("--trace", choices=("YES", "NO"), default="YES")
args = parser.parse_args() #create object of user argsuments, user input accessed as object attribute 

tokens = parse_expression(args.expression)
#logbook records what happened during each round
transcript = []

print("=" * 70)
print("APPROACH 0 - RULE-BASED EXECUTION")
print("=" * 70)
print("Expression:", args.expression)


# Same round-based execution idea as Approach 2
for round_number in range(1, 13):
    print("#" * 100)
    print(f"#start round {round_number}")
    if args.trace == "YES": input("press <ret> to continue,..")
    # Python selects the next operation.
    print(f"#decide_next_call")
    call = decide_next_call(tokens)

    # No remaining operations means finished.
    if call is None:
        print(f"#Next call = none")
        final_text = str(tokens[0])
        print("#" * 100)
        print(f"\nFINAL ANSWER - ROUND {round_number}")
        print(final_text)

        transcript.append(
            "\nFINAL ANSWER:\n" + final_text
        )
        break

    position, name, a, b = call
    print(f"#Next call pos={position}, name={name}, a={a}, b={b}")
    if args.trace == "YES": input("#Press <ret> to execute...")

    # Execute the selected local function
    value = FUNCTIONS[name](a, b)
    result = {"result": value}

    print("#PYTHON RESULT:", result)
    print("#append step to transcript")
    transcript.append(
        f"Round {round_number}: {name}({a}, {b}) -> {result}"
    )

    # Replace the completed operation with its result
    print("#Replace the completed operation with its result")
    tokens[position - 1:position + 2] = [str(value)]

    print("#Remaining expression:", tokens)

    if args.trace == "YES": input("Press <ret> to continue...")

else:
    raise SystemExit("Maximum rounds reached.")


# Save transcript
OUTDIR.mkdir(parents=True, exist_ok=True)

OUT.write_text(
    "\n".join(transcript) + "\n",
    encoding="utf-8"
)

print("\nSaved:", OUT)
