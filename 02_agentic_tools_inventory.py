"""Approach 2: Groq selects per-product tools, Python executes them.

Run: python 02_agentic_tools_inventory.py --trace NO
No graph trials here: invalid numeric CSV inputs cause the product to be skipped.
"""
import argparse
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from common2 import ROOT, InventoryTools, buildTotals, count_rows, new_output, pause
from agent_tools import ask_LLM, send_result

load_dotenv(ROOT / '.env')
parser = argparse.ArgumentParser()
parser.add_argument('--trace', choices=['YES', 'NO'], default='YES')
args = parser.parse_args()
trace = args.trace == 'YES'
MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
client = OpenAI(api_key=os.environ['GROQ_API_KEY'], base_url='https://api.groq.com/openai/v1')
MAX_ROUNDS = 8
filename = '02_agentic_tools_inventory.csv'
new_output(filename)
report, skipped = {}, []

for number in range(1, count_rows() + 1):
    tools = InventoryTools(number, filename)
    print(f'\nPRODUCT {number}')
    messages = [
        {'role': 'system', 'content': (
            'You are an inventory agent. Select the most useful next tool. '
            'Read the CSV record, calculate its restock requirements, build its report row, '
            'print it and save it. Call one tool at a time; use tool results to decide. '
            'Never do arithmetic yourself.')},
        {'role': 'user', 'content': f'Process CSV data row {number} completely.'},
    ]
    error = ''
    for round_number in range(1, MAX_ROUNDS + 1):
        print(f'ROUND {round_number}/{MAX_ROUNDS}')
        pause(trace, 'Ask LLM to choose one tool')
        try:
            assistant, calls = ask_LLM(client, MODEL, messages)
            if len(calls) != 1:
                raise ValueError('LLM did not choose exactly one tool')
            call = calls[0]
            name = call.function.name
            values = json.loads(call.function.arguments or '{}')
            messages.append(assistant.model_dump(exclude_none=True))
            print('LLM SELECTED:', name, values)
            pause(trace, 'Execute selected local Python function')
            if name not in ('readProduct', 'restockProduct', 'buildReport', 'printReport', 'saveReport'):
                raise ValueError('Unknown tool')
            result = getattr(tools, name)(**values)
            if name == 'readProduct':
                tools.validateProduct()
            send_result(messages, call, result)
            print('PYTHON RESULT:', result)
            if tools.saved:
                report[number] = next(iter(tools.report.values()))
                break
        except Exception as exc:
            error = str(exc)
            print('SKIP PRODUCT:', error)
            break
    else:
        error = 'Maximum tool rounds reached'
    if not tools.saved:
        skipped.append((number, error or 'Incomplete workflow'))

print('\nTOTALS:', buildTotals(report))
print('SKIPPED:', skipped)
