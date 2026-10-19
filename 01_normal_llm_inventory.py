"""Approach 1: Normal LLM (Groq), no exposed Python tools.
Run: python 01_normal_llm_inventory.py
"""
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from common import ROOT, load_inventory, print_report, save_report

load_dotenv(ROOT / '.env')
MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
if not os.getenv('GROQ_API_KEY'):
    raise SystemExit('Missing GROQ_API_KEY in .env')
client = OpenAI(api_key=os.environ['GROQ_API_KEY'], base_url='https://api.groq.com/openai/v1')

print('=' * 70)
print('APPROACH 1 - NORMAL LLM (GROQ), NO TOOLS')
print('=' * 70)
print('# STEP 1 - READ LOCAL CSV')
input('Press <Enter> to read inventory.csv...')
products = load_inventory()
# Decimal prices are converted to short strings before JSON serialization.
records = [{**p, 'price': str(p['price'])} for p in products]
#records = []
#for p in products:
#    record = p.copy()
#    record["price"] = str(p["price"])
#    records.append(record)
#products=records
print('Loaded', len(records), 'products')

print('# STEP 2 - SEND CSV RECORDS IN THE PROMPT')
input('Press <Enter> to send one prompt to Groq...')
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {'role': 'system', 'content': (
            'You are an inventory assistant. For EACH supplied product return one JSON item. '
            'needs_restock is true only when quantity < minimum_stock. '
            'units_to_order=max(0,minimum_stock-quantity). '
            'estimated_cost_egp=units_to_order*price, formatted to two decimals. '
            'Return ONLY a JSON array, in the same order. Each item must contain '
            'product_id, name, needs_restock (boolean), units_to_order (integer), '
            'estimated_cost_egp (string). Do not invent products. Do not use Markdown code fences.')},
        {'role': 'user', 'content': f'Analyze these {len(records)} local CSV records: ' +
                                  json.dumps(records, ensure_ascii=False)}
    ],
    temperature=0,
)
raw = (response.choices[0].message.content or '').strip()
print('# GROQ RAW REPLY:', raw)
print('# Groq usage:', response.usage)
input('Press <Enter> to parse response...')
# Strip optional Markdown ```json ... ``` around an otherwise valid JSON answer.
json_text = raw
lines = json_text.splitlines()
if lines and lines[0].strip().lower() in ('```json', '```'):
    if len(lines) < 3 or lines[-1].strip() != '```':
        raise SystemExit('Cannot save: JSON code fence is not properly closed.')
    json_text = '\n'.join(lines[1:-1]).strip()
    print('# Removed Markdown code fences before parsing.')

# Parsing is a local formatting operation; it is NOT a correctness verifier.
try:
    report = json.loads(json_text)
    if not isinstance(report, list) or len(report) != len(products):
        raise ValueError(f'Groq response must contain exactly {len(products)} JSON records.')
    expected_keys = {'product_id', 'name', 'needs_restock', 'units_to_order', 'estimated_cost_egp'}
    for record in report:
        if not isinstance(record, dict) or set(record) != expected_keys:
            raise ValueError('Groq response has an incorrect JSON schema.')
except (ValueError, TypeError) as exc:
    raise SystemExit(f'Cannot save invalid LLM JSON: {exc}')

print('# STEP 3 - DISPLAY MODEL ANSWER (NOT INDEPENDENTLY VERIFIED)')
print_report(report)
input('Press <Enter> to save output...')
save_report('01_normal_llm_inventory.csv', report, ['Model: ' + MODEL, raw])
