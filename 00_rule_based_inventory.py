"""Approach 0: Rule-Based Execution (no LLM).
Run: python 00_rule_based_inventory.py   --trace YES
"""
from common import load_inventory, restock_row, print_report, save_report
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--trace', choices=('YES', 'NO'), default='YES')
args = parser.parse_args()
trace = args.trace == 'YES' 
print('=' * 70)
print('APPROACH 0 - RULE-BASED INVENTORY (NO GROQ)')
print('=' * 70)
print('# STEP 1 - READ CSV LOCALLY')
if trace: input('Press <Enter> to load inventory.csv...')
products = load_inventory()
print('Loaded', len(products), 'products')

print('# STEP 2 - PYTHON RULE ENGINE')
print('Rule: quantity < minimum_stock => restock')
if trace: input('Press <Enter> to start local decisions...')
report = []
transcript = []
round_number=1
for product in products:
    print('#' * 70)
    print(f'# ROUND {round_number} - {product["product_id"]}: {product["name"]}')
    print('quantity=', product['quantity'], 'minimum_stock=', product['minimum_stock'])
    if trace: input('Press <Enter> to execute local restock function...')
    decision = restock_row(product)
    print('PYTHON RESULT:', decision)
    report.append(decision)
    transcript.append(f'Round {round_number}: {decision}')
    round_number=round_number+1
    if trace: input('Press <Enter> to continue...')

print('# STEP 3 - FINAL RESULT')
print_report(report)
if trace: input('Press <Enter> to save outputs...')
save_report('00_rule_based_inventory.csv', report, transcript)
