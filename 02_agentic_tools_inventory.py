"""Approach 2: Groq selects FOUR real Python inventory tools.

Run: python 02_agentic_tools_inventory_FUNCTIONS.py --trace YES
Requires common.py, inventory.csv and .env with GROQ_API_KEY.

Python counts CSV rows and loops once per row. In each round Groq chooses
read_product first, then restock_row. At the end Groq can choose print_report
and save_report. Python executes the functions, never the LLM itself.
Invalid quantity / minimum_stock / price -> skip only that product.
"""
import argparse
import csv
import json
import os
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from openai import OpenAI
from common import ROOT, DATA, OUTDIR, read_product, restock_row, print_report, save_report

# Python function registry: Groq chooses a name; Python calls the matching function.
FUNCTIONS = {
    "read_product": read_product,
    "restock_row": restock_row,
    "print_report": print_report,
    "save_report": save_report,
}

# STEP 1 - SETUP
load_dotenv(ROOT / '.env')
parser = argparse.ArgumentParser()
parser.add_argument('--trace', choices=('YES', 'NO'), default='YES')
args = parser.parse_args()
trace = args.trace == 'YES'
MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
if not os.getenv('GROQ_API_KEY'):
    raise SystemExit('GROQ_API_KEY missing from .env')
client = OpenAI(api_key=os.environ['GROQ_API_KEY'], base_url='https://api.groq.com/openai/v1')

# STEP 2 - SHOW FOUR TOOLS TO THE LLM
# read_product needs the CSV row number (1 means first DATA row, not header).
# Other tools need no arguments because Python retains the current product/report.

# STEP 1 - DEFINE TOOL NAMES AND DESCRIPTIONS

TOOL_DESCRIPTIONS = {
    "read_product": "Read one product from inventory.csv by row number.",
    "restock_row": "Calculate restocking for the current product.",
    "print_report": "Print the complete inventory report.",
    "save_report": "Save the complete inventory report."
}

# STEP 2 - FUNCTION TO BUILD A TOOL DEFINITION
def build_tool(name, description, properties=None):
    if properties is None:
        properties = {}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties.keys()),
                "additionalProperties": False
            }
        }
    }


# STEP 3 - BUILD THE FOUR TOOLS
TOOLS = []
for name, description in TOOL_DESCRIPTIONS.items():
    if name == "read_product":
        properties = {
            "row_number": {
                "type": "integer",
                "description": "Product row number starting from 1"
            }
        }
    else:
        properties = {}
    TOOLS.append(build_tool(name, description, properties))


# STEP 4 - DISPLAY AVAILABLE TOOLS
for tool in TOOLS:
    print("AVAILABLE TOOL:", tool["function"]["name"])

print('=' * 70)
print('APPROACH 2 - AGENTIC INVENTORY: FOUR LOCAL TOOLS')
print('Tools: read_product, restock_row, print_report, save_report')
print('=' * 70)

# STEP 3 - PYTHON COUNTS CSV ROWS (no fixed count or duplicate-ID restriction)
if trace: input('Press <Enter> to count CSV products...')
with DATA.open('r', encoding='utf-8-sig', newline='') as handle:
    total_products = sum(1 for row in csv.DictReader(handle))
print('# Number of CSV products:', total_products)

report = []
transcript = []
skipped = []

# STEP 4 - ONE ROUND FOR EACH CSV ROW
for round_number in range(1, total_products + 1):
    print('\n' + '#' * 70)
    print(f'# PRODUCT ROUND {round_number} / {total_products}')
    current_product = None
    messages = [
        {'role': 'system', 'content': (
            'You operate an inventory system with four available Python tools: '
            'read_product, restock_row, print_report and save_report. '
            'Choose tools yourself. First read the requested CSV row with read_product. '
            'After receiving the row, choose restock_row to calculate it. '
            'Never calculate restocking yourself. Do not print or save the full report '
            'while individual products are being processed.')},
        {'role': 'user', 'content': f'Process inventory.csv product row number {round_number}. Read it, then calculate restocking using Python tools.'},
    ]

    # The agent keeps choosing tools until this product is calculated or skipped.
    calculated = False
    skip_reason = ''
    decision_number = 0
    MAX_TOOL_DECISIONS = 12  # Safety limit, not the number of tools or products.
    while not calculated and not skip_reason:
        decision_number += 1
        if decision_number > MAX_TOOL_DECISIONS:
            skip_reason = 'Maximum LLM tool decisions reached for this product'
            break
        print(f'\n# LLM TOOL DECISION {decision_number} (product {round_number})')
        if trace: input('Press <Enter> to ask Groq to choose a tool...')
        try:
            response = client.chat.completions.create(
                model=MODEL, messages=messages, tools=TOOLS,
                tool_choice='auto', parallel_tool_calls=False,
            )
            assistant = response.choices[0].message
            calls = assistant.tool_calls or []
            #print('# LLM SELECTED:', [c.function.name for c in calls] or 'No tool')
            if not calls:
                skip_reason = 'Groq answered without choosing the required tool'
                break
            messages.append(assistant.model_dump(exclude_none=True))
            for call in calls:
                name = call.function.name
                print('# TOOL REQUEST:', name, call.function.arguments)
                try:
                    parameters = json.loads(call.function.arguments or '{}')
                    if not isinstance(parameters, dict):
                        raise ValueError('Tool parameters must be an object')
                    if name not in FUNCTIONS:
                        raise ValueError('Unknown local tool: ' + name)
                    if name == 'read_product':
                        if parameters != {'row_number': round_number}:
                            raise ValueError(f'Use row_number={round_number} for this round')
                        if current_product is not None:
                            raise ValueError('This product has already been read')
                        if trace: input('Press <Enter> to execute common.read_product...')
                        # One dispatch line: Python executes the function Groq selected.
                        raw = FUNCTIONS[name](**parameters)
                        print('# PYTHON READ CSV ROW:', raw)
                        # Check numeric INPUTS only, never recalculate restock results.
                        try:
                            quantity_text = (raw.get('quantity') or '').strip()
                            minimum_text = (raw.get('minimum_stock') or '').strip()
                            if not quantity_text.isdecimal() or not minimum_text.isdecimal():
                                raise ValueError('quantity and minimum_stock must be nonnegative whole numbers')
                            quantity = int(quantity_text)
                            minimum_stock = int(minimum_text)
                            price = Decimal((raw.get('price') or '').strip())
                            if not price.is_finite() or price < 0:
                                raise ValueError('price must be finite and nonnegative')
                        except (ValueError, InvalidOperation, TypeError, AttributeError) as exc:
                            skip_reason = f'Invalid CSV number: {exc}'
                            result = {'error': skip_reason, 'status': 'skip_product'}
                        else:
                            current_product = raw.copy()
                            current_product['quantity'] = quantity
                            current_product['minimum_stock'] = minimum_stock
                            current_product['price'] = price
                            result = {'status': 'product_read', 'product': {
                                'product_id': raw.get('product_id', ''),
                                'name': raw.get('name', ''),
                                'quantity': quantity,
                                'minimum_stock': minimum_stock,
                                'price': str(price),
                            }}
                    elif name == 'restock_row':
                        if parameters:
                            raise ValueError('restock_row needs no LLM arguments')
                        if current_product is None:
                            raise ValueError('Call read_product successfully before restock_row')
                        if trace: input('Press <Enter> to execute common.restock_row...')
                        decision = FUNCTIONS[name](product=current_product)
                        report.append(decision)
                        calculated = True
                        result = decision
                        print('# PYTHON CALCULATED:', decision)
                    else:
                        result = {'error': f'{name} is available only after the product loop'}
                        print('# BLOCKED:', result['error'])
                except Exception as exc:
                    result = {'error': str(exc)}
                    print('# LOCAL TOOL ERROR:', exc)
                transcript.append(f'Product {round_number}: {name} -> {result}')
                messages.append({'role': 'tool', 'tool_call_id': call.id, 'content': json.dumps(result)})
            if skip_reason or calculated:
                break
        except Exception as exc:
            skip_reason = f'Groq API error: {exc}'
            break

    if not calculated:
        if not skip_reason:
            skip_reason = 'No successful restock_row tool request'
        print('# SKIP PRODUCT:', skip_reason)
        skipped.append({'row': round_number + 1,
                        'product_id': current_product.get('product_id', '') if current_product else '',
                        'reason': skip_reason})
        transcript.append(f'Product {round_number}: SKIPPED: {skip_reason}')
    if trace: input('Press <Enter> for next product...')

# STEP 5 - GROQ CHOOSES THE REPORT TOOLS
print('\n# STEP 5 - PRINT / SAVE REPORT VIA LLM-SELECTED TOOLS')
report_messages = [
    {'role': 'system', 'content': (
        'All products have now been processed. Four tools are available. '
        'Choose print_report and save_report to finish the user request. '
        'Use one tool at a time, and do not read or recalculate any product.')},
    {'role': 'user', 'content': (
        f'Processing complete. {len(report)} results and {len(skipped)} skipped products. '
        'Please print the inventory report and save it.')},
]
printed = False
saved = False
report_decisions = 0
MAX_REPORT_DECISIONS = 12  # Safety limit if the model keeps choosing tools.
while not (printed and saved):
    report_decisions += 1
    if report_decisions > MAX_REPORT_DECISIONS:
        print('# Stopped reporting: maximum LLM decisions reached')
        break
    print(f'\n# REPORT TOOL DECISION {report_decisions}')
    if trace: input('Press <Enter> to let Groq select a reporting tool...')
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=report_messages, tools=TOOLS,
            tool_choice='auto', parallel_tool_calls=False,
        )
        assistant = response.choices[0].message
        calls = assistant.tool_calls or []
        print('# LLM SELECTED:', [c.function.name for c in calls] or 'No tool')
        if not calls:
            print('# LLM finished without another tool request')
            break
        report_messages.append(assistant.model_dump(exclude_none=True))
        for call in calls:
            name = call.function.name
            try:
                parameters = json.loads(call.function.arguments or '{}')
                if parameters != {}:
                    raise ValueError('Reporting tools take no arguments')
                if name not in FUNCTIONS:
                    raise ValueError('Unknown local tool: ' + name)
                if name == 'print_report':
                    if not printed:
                        if trace: input('Press <Enter> to execute common.print_report...')
                        FUNCTIONS[name](report=report)
                        printed = True
                        transcript.append('Python print_report executed')
                    result = {'status': 'printed'}
                elif name == 'save_report':
                    if not saved:
                        if trace: input('Press <Enter> to execute common.save_report...')
                        transcript.append('Python save_report executed')
                        FUNCTIONS[name](filename='02_agentic_tools_inventory.csv', report=report, transcript=transcript)
                        saved = True
                    result = {'status': 'saved'}
                else:
                    result = {'error': f'{name} cannot be used during reporting'}
            except Exception as exc:
                result = {'error': str(exc)}
            print('# PYTHON TOOL RESULT:', result)
            report_messages.append({'role': 'tool', 'tool_call_id': call.id,
                                    'content': json.dumps(result)})
    except Exception as exc:
        print('# Groq reporting error:', exc)
        break

# STEP 6 - SAVE SKIPPED-ROW DIAGNOSTIC AS BEFORE
OUTDIR.mkdir(exist_ok=True)
with (OUTDIR / '02_agentic_tools_inventory_skipped.csv').open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=['row', 'product_id', 'reason'])
    writer.writeheader()
    writer.writerows(skipped)
print('# Finished. Calculated:', len(report), '| Skipped:', len(skipped))
print('# Printed:', printed, '| Saved:', saved)
