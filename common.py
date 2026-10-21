
"""Common functions for the Inventory Management examples."""

import csv
from pathlib import Path

# STEP 1 - FILE LOCATIONS

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "inventory.csv"
OUTDIR = ROOT / "OUTPUT"


# STEP 2 - READ INVENTORY

def load_inventory():
    products = []

    with open(DATA, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                row["quantity"] = int(row["quantity"])
                row["minimum_stock"] = int(row["minimum_stock"])
                row["price"] = float(row["price"])

                if row["quantity"] < 0 or row["minimum_stock"] < 0:
                    print("Skipping:", row["name"], "- negative stock")
                    continue

                if row["price"] < 0:
                    print("Skipping:", row["name"], "- negative price")
                    continue

                products.append(row)

            except (ValueError, TypeError, KeyError):
                print("Skipping invalid product:", row.get("name"))
                continue

    print("Products loaded:", len(products))
    return products


# STEP 3 - CALCULATE RESTOCKING

def restock_row(product):
    units = max(
        0,
        product["minimum_stock"] - product["quantity"]
    )

    cost = units * product["price"]

    return {
        "product_id": product["product_id"],
        "name": product["name"],
        "needs_restock": units > 0,
        "units_to_order": units,
        "estimated_cost_egp": f"{cost:.2f}"
    }


# STEP 4 - GENERATE COMPLETE REPORT

def trusted_report(products):
    report = []

    for product in products:
        report.append(restock_row(product))

    return report


# STEP 5 - PRINT REPORT

def print_report(report):
    print("\nINVENTORY RESTOCKING REPORT")
    print("-" * 60)

    total_cost = 0
    restock_count = 0

    for product in report:
        print(
            product["product_id"],
            product["name"],
            "Units:", product["units_to_order"],
            "Cost:", product["estimated_cost_egp"]
        )

        total_cost += float(product["estimated_cost_egp"])

        if product["needs_restock"]:
            restock_count += 1

    print("-" * 60)
    print("Products needing restock:", restock_count)
    print("Total cost:", f"{total_cost:.2f}", "EGP")


# STEP 6 - SAVE REPORT

def save_report(filename, report, transcript):
    OUTDIR.mkdir(exist_ok=True)

    # Save CSV report
    report_file = OUTDIR / filename

    columns = [
        "product_id",
        "name",
        "needs_restock",
        "units_to_order",
        "estimated_cost_egp"
    ]

    with open(report_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(report)

    # Save execution history
    trace_file = OUTDIR / filename.replace(".csv", "_trace.txt")

    with open(trace_file, "w", encoding="utf-8") as file:
        file.write("\n".join(transcript))

    print("Saved:", report_file)
    print("Saved:", trace_file)


# STEP 7 - READ ONE PRODUCT

def read_product(row_number):
    with open(DATA, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        number = 1
        for product in reader:
            if number == row_number:
                return product
            number = number + 1

    raise ValueError("Product not found")
