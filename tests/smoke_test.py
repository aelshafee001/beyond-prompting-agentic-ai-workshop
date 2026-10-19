"""Offline repository checks; does not use an API key. Run: python tests/smoke_test.py"""
from pathlib import Path
import csv, sys, tempfile, subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import common

rows = common.load_inventory()
assert len(rows) == 14, f"Expected 14 valid rows with intentional P003 price=X; got {len(rows)}"
assert len(common.trusted_report(rows)) == 14
p3 = common.read_product(3)
assert p3['product_id'] == 'P003' and p3['price'] == 'X'
assert common.restock_row(common.read_product(1) | {'quantity': 4, 'minimum_stock': 10, 'price': rows[0]['price']})['units_to_order'] == 6
cmd = [sys.executable, str(ROOT / '00_rule_based_math.py'), '--expression', '12 + 8 * 3 - 10 / 5', '--trace', 'NO']
process = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=25)
assert process.returncode == 0, process.stderr
assert '34.0' in process.stdout, process.stdout
print('PASS: shared inventory loader skips invalid row and read_product sees raw row.')
print('PASS: local restock calculation and offline rule-based math.')
