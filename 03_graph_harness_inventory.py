"""Approach 3: Graph / Harness / Loop with four Groq-selectable local tools.

Run: python 03_graph_harness_inventory_FUNCTIONS.py --trace YES
Requires common.py, inventory.csv, and .env containing GROQ_API_KEY.

Python counts CSV rows. Each row gets up to THREE trials. In a trial, Groq
selects read_product, receives its result, and selects restock_row. Python
performs every operation. Invalid input or tool choices produce feedback.
After three failed trials, skip that row and continue. At the end, Groq may
select print_report and save_report. There is no independent verification of
model-generated arithmetic: restock_row itself performs the calculation.
"""
import argparse
import csv
import json
import os
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from openai import OpenAI
from common import ROOT, DATA, OUTDIR, read_product, restock_row, print_report, save_report

# Same function dictionary used in Approach 2.
# Groq selects a NAME. Python executes the actual function from common.py.
FUNCTIONS = {
    "read_product": read_product,
    "restock_row": restock_row,
    "print_report": print_report,
    "save_report": save_report,
}

# STEP 1 - CONFIGURATION
load_dotenv(ROOT / '.env')
parser = argparse.ArgumentParser()
parser.add_argument('--trace', choices=('YES', 'NO'), default='YES')
args = parser.parse_args()
trace = args.trace == 'YES'
MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
MAX_TRIALS = 3
MAX_TOOL_DECISIONS = 8  # Prevent an endless model tool-selection loop.

if not os.getenv('GROQ_API_KEY'):
    raise SystemExit('GROQ_API_KEY missing from .env')
client = OpenAI(api_key=os.environ['GROQ_API_KEY'], base_url='https://api.groq.com/openai/v1')

# STEP 2 - DESCRIBE THE SAME FOUR TOOLS AS APPROACH 2
TOOL_DESCRIPTIONS = {
    'read_product': 'Read one product from inventory.csv by its 1-based data row number.',
    'restock_row': 'Calculate restocking for the product already read, using local Python.',
    'print_report': 'Print the accumulated inventory report after all products.',
    'save_report': 'Save the accumulated report after all products.',
}


def build_tool(name, description, properties=None):
    if properties is None:
        properties = {}
    return {
        'type': 'function',
        'function': {
            'name': name,
            'description': description,
            'parameters': {
                'type': 'object',
                'properties': properties,
                'required': list(properties.keys()),
                'additionalProperties': False,
            },
        },
    }


TOOLS = []
for name, description in TOOL_DESCRIPTIONS.items():
    properties = {}
    if name == 'read_product':
        properties = {
            'row_number': {
                'type': 'integer',
                'description': 'Product data row number starting from 1',
            }
        }
    TOOLS.append(build_tool(name, description, properties))

print('=' * 70)
print('APPROACH 3 - GRAPH / HARNESS / LOOP: FOUR LOCAL TOOLS')
print('Available tools:', ', '.join(TOOL_DESCRIPTIONS))
print('Maximum trials per product:', MAX_TRIALS)
print('=' * 70)

# STEP 3 - PYTHON COUNTS CSV ROWS (NO FIXED COUNT, DUPLICATES ALLOWED)
if trace: input('Press <Enter> to count CSV products...')
with DATA.open('r', encoding='utf-8-sig', newline='') as handle:
    total_products = sum(1 for row in csv.DictReader(handle))
print('Number of CSV products:', total_products)

report = []
transcript = []
skipped = []

# STEP 4 - ONE GRAPH ROUND PER PRODUCT
for row_number in range(1, total_products + 1):
    print('\n' + '#' * 70)
    print(f'# PRODUCT ROUND {row_number}/{total_products}')
    accepted = False
    feedback = 'None'
    last_code = ''

    # NODE A: LOOP - THREE COMPLETE ATTEMPTS FOR THIS ROW
    for trial in range(1, MAX_TRIALS + 1):
        print(f'\n# TRIAL {trial}/{MAX_TRIALS} FOR PRODUCT ROW {row_number}')
        print('# Feedback from previous trial:', feedback)
        print('# The CSV will be reread when Groq calls read_product.')
        if trace: input('Press <Enter> to start this trial...')

        current_product = None
        calculated = False
        error = ''
        tool_decisions = 0

        # Fresh conversation for each trial. Previous feedback is included.
        messages = [
            {'role': 'system', 'content': (
                'You control four Python tools: read_product, restock_row, '
                'print_report and save_report. Select your next tool yourself. '
                'For this product first call read_product with the requested row_number. '
                'After its successful tool result, call restock_row. '
                'Never calculate inventory quantities or costs yourself. '
                'Do not print or save reports while processing a product. '
                'If you receive an error, read the feedback and act appropriately.')},
            {'role': 'user', 'content': (
                f'Process inventory.csv data row {row_number}. '
                'Use local Python tools to read and calculate this one product. '
                f'Feedback from previous trial: {feedback}')},
        ]

        # NODE B: DECISION -> VALIDATION -> EXECUTION -> STATE UPDATE
        while not calculated and not error:
            tool_decisions += 1
            if tool_decisions > MAX_TOOL_DECISIONS:
                error = 'Maximum tool-selection decisions reached for this trial'
                break

            print(f'# DECISION NODE - Groq selects a tool (decision {tool_decisions})')
            if trace: input('Press <Enter> to ask Groq for its next tool...')
            try:
                response = client.chat.completions.create(
                    model=MODEL, messages=messages, tools=TOOLS,
                    tool_choice='auto', parallel_tool_calls=False,
                )
                assistant = response.choices[0].message
                calls = assistant.tool_calls or []
                print('# GROQ SELECTED:', [c.function.name for c in calls] or 'No tool')
                if not calls:
                    error = 'Groq finished without selecting the required tool'
                    break

                # The assistant tool call must be recorded before sending tool results.
                messages.append(assistant.model_dump(exclude_none=True))
                for call in calls:
                    name = call.function.name
                    print('# VALIDATION NODE - Requested tool:', name)
                    print('# FUNCTION LOOKUP:', 'FUNCTIONS[' + repr(name) + ']')
                    try:
                        parameters = json.loads(call.function.arguments or '{}')
                        if not isinstance(parameters, dict):
                            raise ValueError('Tool arguments must be a JSON object')
                        if name not in FUNCTIONS:
                            raise ValueError('Unknown tool: ' + name)

                        if name == 'read_product':
                            if parameters != {'row_number': row_number}:
                                raise ValueError(f'Only row_number={row_number} is allowed in this round')
                            if current_product is not None:
                                raise ValueError('This row was already read in this trial')

                            print('# EXECUTION NODE - common.read_product')
                            if trace: input('Press <Enter> to read the CSV row locally...')
                            raw = FUNCTIONS[name](**parameters)  # CSV reread on each trial.
                            last_code = raw.get('product_id', '')
                            print('# PYTHON READ:', raw)

                            # Check CSV numeric inputs, not a second restock calculation.
                            quantity_text = (raw.get('quantity') or '').strip()
                            minimum_text = (raw.get('minimum_stock') or '').strip()
                            if not quantity_text.isdecimal() or not minimum_text.isdecimal():
                                raise ValueError('quantity and minimum_stock must be nonnegative whole numbers')
                            quantity = int(quantity_text)
                            minimum_stock = int(minimum_text)
                            price = Decimal((raw.get('price') or '').strip())
                            if not price.is_finite() or price < 0:
                                raise ValueError('price must be finite and nonnegative')

                            current_product = raw.copy()
                            current_product['quantity'] = quantity
                            current_product['minimum_stock'] = minimum_stock
                            current_product['price'] = price
                            result = {
                                'status': 'product_read',
                                'product': {
                                    'product_id': last_code,
                                    'name': raw.get('name', ''),
                                    'quantity': quantity,
                                    'minimum_stock': minimum_stock,
                                    'price': str(price),
                                },
                            }

                        elif name == 'restock_row':
                            if parameters:
                                raise ValueError('restock_row takes no LLM arguments')
                            if current_product is None:
                                raise ValueError('Call read_product successfully first')
                            print('# EXECUTION NODE - common.restock_row')
                            if trace: input('Press <Enter> to calculate restocking locally...')
                            decision = FUNCTIONS[name](product=current_product)
                            report.append(decision)
                            calculated = True
                            accepted = True
                            result = decision
                            print('# PYTHON CALCULATED:', decision)

                        else:
                            raise ValueError(f'{name} is only available after all product rounds')

                    except (ValueError, InvalidOperation, TypeError, AttributeError, IndexError, OSError) as exc:
                        error = str(exc)
                        result = {'error': error}
                        print('# INVALID EDGE -> FEEDBACK:', error)

                    print('# STATE UPDATE - Returning Python result to Groq:', result)
                    transcript.append(f'Product {row_number}, trial {trial}: {name} -> {result}')
                    messages.append({
                        'role': 'tool',
                        'tool_call_id': call.id,
                        'content': json.dumps(result),
                    })
                    if calculated or error:
                        break

            except Exception as exc:
                error = f'Groq API error: {exc}'
                print('# DECISION ERROR:', error)

        # NODE C: ACCEPT / FEEDBACK / RETRY
        if accepted:
            transcript.append(f'Product {row_number}: ACCEPTED on trial {trial}')
            print(f'# ACCEPTED PRODUCT ROW {row_number} ON TRIAL {trial}')
            if trace: input('Press <Enter> to move to the next product...')
            break

        feedback = error or 'Trial finished without a successful restock_row call'
        print(f'# FAILED TRIAL {trial}/{MAX_TRIALS}: {feedback}')
        transcript.append(f'Product {row_number}, trial {trial}: FAILED: {feedback}')
        if trial < MAX_TRIALS:
            print('# FEEDBACK -> LOOP BACK TO THE SAME CSV ROW')
            print('# You may correct inventory.csv before the next trial.')
            if trace: input('Press <Enter> to retry the SAME product...')

    # NODE D: SKIP AFTER THREE FAILED TRIALS
    if not accepted:
        print(f'# THREE FAILED TRIALS -> SKIP PRODUCT ROW {row_number}')
        skipped.append({
            'row': row_number + 1,
            'product_id': last_code,
            'reason': feedback,
            'trials': MAX_TRIALS,
        })
        transcript.append(f'Product {row_number}: SKIPPED after {MAX_TRIALS} trials')

# STEP 5 - REPORT PHASE: GROQ SELECTS PRINT AND SAVE TOOLS
print('\n# STEP 5 - REPORT PHASE (GROQ SELECTS LOCAL REPORT TOOLS)')
printed = False
saved = False
report_decisions = 0
report_messages = [
    {'role': 'system', 'content': (
        'All product rounds have finished. Four Python tools are available. '
        'Choose print_report and save_report, one at a time. '
        'These functions use the report stored by Python. '
        'Do not read or calculate any more products.')},
    {'role': 'user', 'content': (
        f'{len(report)} products calculated; {len(skipped)} products skipped. '
        'Print and save the complete inventory report using the local tools.')},
]

while not (printed and saved):
    report_decisions += 1
    if report_decisions > MAX_TOOL_DECISIONS:
        print('# Reporting stopped: tool-selection safety limit reached')
        break
    print(f'\n# REPORT DECISION {report_decisions}')
    if trace: input('Press <Enter> to let Groq choose a reporting tool...')
    try:
        response = client.chat.completions.create(
            model=MODEL, messages=report_messages, tools=TOOLS,
            tool_choice='auto', parallel_tool_calls=False,
        )
        assistant = response.choices[0].message
        calls = assistant.tool_calls or []
        print('# GROQ SELECTED:', [c.function.name for c in calls] or 'No tool')
        if not calls:
            print('# Groq finished without another reporting tool')
            break
        report_messages.append(assistant.model_dump(exclude_none=True))
        for call in calls:
            name = call.function.name
            try:
                parameters = json.loads(call.function.arguments or '{}')
                if parameters != {}:
                    raise ValueError('Reporting tools take no arguments')
                if name not in FUNCTIONS:
                    raise ValueError('Unknown tool: ' + name)
                if name == 'print_report':
                    if not printed:
                        print('# EXECUTION NODE - common.print_report')
                        if trace: input('Press <Enter> to print the report...')
                        FUNCTIONS[name](report=report)
                        printed = True
                        transcript.append('Python print_report executed')
                    result = {'status': 'printed'}
                elif name == 'save_report':
                    if not saved:
                        print('# EXECUTION NODE - common.save_report')
                        if trace: input('Press <Enter> to save the report...')
                        transcript.append('Python save_report executed')
                        FUNCTIONS[name](filename='03_graph_harness_inventory.csv', report=report, transcript=transcript)
                        saved = True
                    result = {'status': 'saved'}
                else:
                    raise ValueError(f'{name} cannot be used during reporting')
            except Exception as exc:
                result = {'error': str(exc)}
            print('# PYTHON TOOL RESULT:', result)
            report_messages.append({
                'role': 'tool', 'tool_call_id': call.id,
                'content': json.dumps(result),
            })
    except Exception as exc:
        print('# Groq reporting error:', exc)
        break

# STEP 6 - SAVE SKIPPED-ROW DETAILS EVEN IF REPORT TOOL WAS NOT CHOSEN
OUTDIR.mkdir(parents=True, exist_ok=True)
with (OUTDIR / '03_graph_harness_inventory_skipped.csv').open(
    'w', newline='', encoding='utf-8'
) as handle:
    writer = csv.DictWriter(handle, fieldnames=['row', 'product_id', 'reason', 'trials'])
    writer.writeheader()
    writer.writerows(skipped)
print('\n# FINISHED | Calculated:', len(report), '| Skipped:', len(skipped))
print('# Report printed:', printed, '| Report saved:', saved)
print('# Skipped report:', OUTDIR / '03_graph_harness_inventory_skipped.csv')
