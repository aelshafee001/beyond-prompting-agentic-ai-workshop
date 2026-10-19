"""Shared CSV I/O and deterministic inventory rules.

Invalid inventory rows are SKIPPED with a warning instead of crashing the run.
Valid products are processed in their original CSV order.
"""
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'inventory.csv'
OUTDIR = ROOT / 'OUTPUT'


def load_inventory():
    """Return only valid inventory rows; print a reason for each skipped CSV row."""
    required = {'product_id', 'name', 'category', 'quantity', 'minimum_stock', 'price'}
    products = []
    skipped = 0

    with DATA.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or set(reader.fieldnames) != required:
            raise ValueError('inventory.csv must contain these columns: ' + ', '.join(sorted(required)))

        for csv_row_number, raw in enumerate(reader, start=2):
            # Every product is checked separately, so one invalid value
            # does not prevent later valid products from being processed.
            product_id = (raw.get('product_id') or '').strip()
            name = (raw.get('name') or '').strip()
            try:
                if not product_id or not name:
                    raise ValueError('missing product_id or name')
                quantity = int((raw.get('quantity') or '').strip())
                minimum_stock = int((raw.get('minimum_stock') or '').strip())
                price = Decimal((raw.get('price') or '').strip())
                if quantity < 0 or minimum_stock < 0:
                    raise ValueError('quantity and minimum_stock cannot be negative')
                if not price.is_finite() or price < 0:
                    raise ValueError('price must be a finite, nonnegative number')
            except (ValueError, TypeError, InvalidOperation) as exc:
                skipped += 1
                print(f'# SKIP CSV ROW {csv_row_number} | product {product_id or "(missing ID)"}: {exc}')
                continue

            item = dict(raw)
            item['product_id'] = product_id
            item['name'] = name
            item['quantity'] = quantity
            item['minimum_stock'] = minimum_stock
            item['price'] = price
            products.append(item)

    print(f'# CSV SUMMARY: {len(products)} valid products; {skipped} invalid rows skipped.')
    return products


def restock_row(product):
    """Trusted deterministic result for a single valid product."""
    units = max(0, product['minimum_stock'] - product['quantity'])
    return {
        'product_id': product['product_id'],
        'name': product['name'],
        'needs_restock': units > 0,
        'units_to_order': units,
        'estimated_cost_egp': f'{(product["price"] * units):.2f}',
    }


def trusted_report(products):
    return [restock_row(p) for p in products]


def print_report(report):
    print(f'{"ID":<7} {"PRODUCT":<24} {"RESTOCK":<9} {"UNITS":<7} COST (EGP)')
    print('-' * 70)
    for r in report:
        print(f'{r["product_id"]:<7} {r["name"]:<24} {str(r["needs_restock"]):<9} '
              f'{r["units_to_order"]:<7} {r["estimated_cost_egp"]}')
    print('Products needing restock:', sum(r['needs_restock'] for r in report))
    print('Total estimated cost (EGP):',
          f'{sum(Decimal(r["estimated_cost_egp"]) for r in report):.2f}')


def save_report(filename, report, transcript):
    """Write the CSV report and a plain-text teaching transcript."""
    OUTDIR.mkdir(exist_ok=True)
    path = OUTDIR / filename
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'product_id', 'name', 'needs_restock', 'units_to_order', 'estimated_cost_egp'])
        writer.writeheader()
        writer.writerows(report)
    trace_file = OUTDIR / filename.replace('.csv', '_trace.txt')
    trace_file.write_text('\n'.join(transcript) + '\n', encoding='utf-8')
    print('Saved:', path)
    print('Saved:', trace_file)


def read_product(row_number):
    """Read ONE CSV product by 1-based DATA row number (header not counted).

    Return the original CSV strings; input validation belongs to the caller.
    Duplicate IDs are permitted because this tool uses row position, not ID.
    """
    if type(row_number) is not int or row_number < 1:
        raise ValueError('row_number must be a positive integer')
    with DATA.open('r', encoding='utf-8-sig', newline='') as handle:
        for index, product in enumerate(csv.DictReader(handle), start=1):
            if index == row_number:
                return product
    raise IndexError(f'Product row {row_number} does not exist')
