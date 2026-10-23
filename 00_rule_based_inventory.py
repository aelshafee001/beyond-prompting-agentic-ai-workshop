"""Approach 0: Python rules select and execute the per-record tools.
Run: python 00_rule_based_inventory2.py   --trace NO
"""
import argparse
from common2 import InventoryTools, buildTotals, count_rows, new_output, pause

parser = argparse.ArgumentParser()
parser.add_argument('--trace', choices=['YES', 'NO'], default='YES')
args = parser.parse_args()
trace = args.trace == 'YES'
filename = '00_rule_based_inventory.csv'
new_output(filename)
report = {}
skipped = []

for number in range(1, count_rows() + 1):
    tools = InventoryTools(number, filename)
    print(f'\nPRODUCT {number} | Python chooses actions')
    try:
        for round_number, action in enumerate(['readProduct', 'restockProduct', 'buildReport', 'printReport', 'saveReport'], 1):
            pause(trace, f'ROUND {round_number}: {action}')
            if action == 'readProduct':
                row = tools.readProduct(number)
                product_id = row['product_id']
            else:
                result = getattr(tools, action)(product_id)
                print(result)
        report[number] = tools.report[product_id]
    except (ValueError, KeyError, TypeError) as error:
        print('SKIP PRODUCT:', error)
        skipped.append((number, str(error)))

print('\nTOTALS:', buildTotals(report))
print('SKIPPED:', skipped)
