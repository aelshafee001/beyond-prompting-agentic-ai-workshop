"""Approach 3: LLM chooses each action; graph/harness validates and retries.
Run: python 03_graph_harness_inventory.py --trace NO
PRODUCT -> ROUND (one successful tool call) -> TRIAL (up to 3 attempts).
An invalid quantity / minimum_stock / price is retryable: the CSV is
reread on the next trial, so an instructor can correct it during the pause.
After 3 failed trials in ANY round, skip the entire product.
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
MAX_ROUNDS, MAX_TRIALS = 8, 3
filename = '03_graph_harness_inventory.csv'
new_output(filename)
report, skipped = {}, []

for number in range(1, count_rows() + 1):
    tools = InventoryTools(number, filename)
    print(f'\nPRODUCT {number}')
    history = []
    feedback = 'None'
    messages = [
        {'role': 'system', 'content': (
            'You are an inventory agent. Freely choose the next useful Python tool. '
            'The tools read products, calculate restocking, build, print and save report rows. '
            'Make exactly one tool call per response. Read tool results and feedback carefully. '
            'Do not calculate any restock values yourself.')},
        {'role': 'user', 'content': f'Process CSV data row {number} completely.'},
    ]
    for round_number in range(1, MAX_ROUNDS + 1):
        print(f'\nROUND {round_number}/{MAX_ROUNDS}')
        round_ok = False
        for trial in range(1, MAX_TRIALS + 1):
            print(f'TRIAL {trial}/{MAX_TRIALS} | STATUS: {feedback}')
            pause(trace, 'DECISION NODE - Request one tool')
            call = None
            try:
                # LLM selects; Python never includes an expected tool name.
                assistant, calls = ask_LLM(client, MODEL, messages)
                if len(calls) != 1:
                    raise ValueError('Select exactly one tool')
                call = calls[0]
                name = call.function.name
                values = json.loads(call.function.arguments or '{}')
                messages.append(assistant.model_dump(exclude_none=True))
                print('DECISION:', name, values)
                print('VALIDATION NODE')
                if name not in ('readProduct', 'restockProduct', 'buildReport', 'printReport', 'saveReport'):
                    raise ValueError('Unknown or disallowed tool')
                # Minimal sequence validation is a guard, not a forced decision.
                if name != 'readProduct' and tools.product is None:
                    raise ValueError('Product must be read before using this action')
                if name == 'readProduct' and values.get('row_number') != number:
                    raise ValueError(f'Only row number {number} belongs to this product')
                pause(trace, 'EXECUTION NODE - Run local tool')
                result = getattr(tools, name)(**values)
                if name == 'readProduct':
                    tools.validateProduct()  # retryable numeric-input failure
                round_ok = True
                feedback = 'None'
                history.append(f'Round {round_number}, trial {trial}: {name} -> SUCCESS')
                print('STATE UPDATE:', result)
            except Exception as exc:
                feedback = str(exc)
                result = {'error': feedback}
                history.append(f'Round {round_number}, trial {trial}: FAILED -> {feedback}')
                print('FEEDBACK EDGE:', feedback)
                # On a later readProduct trial, the tool rereads the changed CSV.
                if trial < MAX_TRIALS:
                    pause(trace, 'RETRY EDGE - Correct CSV if necessary, then retry')
            if call is not None:
                send_result(messages, call, result)
            else:
                messages.append({'role': 'user', 'content': 'Harness feedback: ' + feedback})
            if round_ok:
                break
        if not round_ok:
            print('SKIP EDGE: Three failed trials -> next product')
            break
        if tools.saved:
            print('DONE EDGE: Current product report saved')
            report[number] = next(iter(tools.report.values()))
            break
    if not tools.saved:
        skipped.append((number, feedback if feedback != 'None' else 'Maximum rounds reached'))
    print('HISTORY:', *history, sep='\n  ')

print('\nTOTALS:', buildTotals(report))
print('SKIPPED:', skipped)
