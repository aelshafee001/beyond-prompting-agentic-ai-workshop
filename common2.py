"""Shared per-record inventory tools. No Groq dependency.

Each InventoryTools object owns the state for ONE CSV row. A product ID
identifies the active record after readProduct(row_number) has succeeded.
"""
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'inventory.csv'
OUTDIR = ROOT / 'OUTPUT'
COLUMNS = ['product_id', 'name', 'needs_restock', 'units_to_order', 'estimated_cost_egp']


def count_rows():
    with DATA.open(encoding='utf-8-sig', newline='') as file:
        return sum(1 for _ in csv.DictReader(file))


class InventoryTools:
    def __init__(self, row_number, output_name):
        self.row_number = row_number
        self.output_name = output_name
        self.product = None
        self.restock = None
        self.report = {}          # product_id -> report row dictionary
        self.saved = False
        self.history = []

    def readProduct(self, row_number):
        """Read a raw CSV row; rereading is allowed after failed validation."""
        if row_number != self.row_number:
            raise ValueError(f'Current CSV data row is {self.row_number}')
        with DATA.open(encoding='utf-8-sig', newline='') as file:
            for number, row in enumerate(csv.DictReader(file), start=1):
                if number == row_number:
                    self.product = row
                    self.restock = None
                    return dict(row)
        raise ValueError(f'CSV row {row_number} not found')

    def validateProduct(self):
        """Check essential CSV inputs before calculating. Throws on bad data."""
        if self.product is None:
            raise ValueError('Read the product first')
        row = self.product
        if not row.get('product_id') or not row.get('name'):
            raise ValueError('Missing product ID or name')
        try:
            # int('2.5') fails, as it should: inventory counts are whole numbers.
            quantity = int(row['quantity'])
            minimum = int(row['minimum_stock'])
            price = float(row['price'])
        except (KeyError, TypeError, ValueError):
            raise ValueError('quantity, minimum_stock, and price must be numbers')
        if quantity < 0 or minimum < 0 or not math.isfinite(price) or price < 0:
            raise ValueError('quantity, minimum_stock, and price must be finite and nonnegative')
        row['quantity'], row['minimum_stock'], row['price'] = quantity, minimum, price
        return True

    def restockProduct(self, product_id):
        """Calculate one product, using the original CSV data."""
        if self.product is None or self.product.get('product_id') != product_id:
            raise ValueError('Product ID does not match the active record')
        self.validateProduct()
        units = max(0, self.product['minimum_stock'] - self.product['quantity'])
        self.restock = {'units_to_order': units,
                        'needs_restock': units > 0,
                        'estimated_cost_egp': f"{units * self.product['price']:.2f}"}
        return dict(self.restock)

    def buildReport(self, product_id):
        """Create ONE report row from Python's restocking result."""
        if self.product is None or self.product['product_id'] != product_id or self.restock is None:
            raise ValueError('Run readProduct and restockProduct first')
        row = {'product_id': product_id, 'name': self.product['name'], **self.restock}
        self.report[product_id] = row
        return dict(row)

    def printReport(self, product_id):
        """Display only the current product's completed report row."""
        if product_id not in self.report:
            raise ValueError('Build the report row first')
        print('REPORT ROW:', self.report[product_id])
        return {'status': 'printed', 'product_id': product_id}

    def saveReport(self, product_id):
        """Append ONE product to output CSV (header added once)."""
        if product_id not in self.report:
            raise ValueError('Build the report row first')
        if self.saved:
            return {'status': 'already_saved', 'product_id': product_id}
        OUTDIR.mkdir(exist_ok=True)
        path = OUTDIR / self.output_name
        with path.open('a', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=COLUMNS)
            if path.stat().st_size == 0:
                writer.writeheader()
            writer.writerow(self.report[product_id])
        self.saved = True
        return {'status': 'saved', 'product_id': product_id}


def buildTotals(restock_dict):
    """Combine all completed report rows, keyed by CSV row number."""
    rows = list(restock_dict.values())
    return {'processed_products': len(rows),
            'products_needing_restock': sum(int(row['needs_restock']) for row in rows),
            'total_units_to_order': sum(int(row['units_to_order']) for row in rows),
            'total_cost_egp': f"{sum(float(row['estimated_cost_egp']) for row in rows):.2f}"}


def new_output(filename):
    OUTDIR.mkdir(exist_ok=True)
    path = OUTDIR / filename
    if path.exists():
        path.unlink()
    return path


def pause(trace, text):
    if trace:
        input(text + ' Press Enter...')
    else:
        print(text)
