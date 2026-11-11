
"""Independent OEE calculation verification for generated CSV data."""

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def load_csv(folder, filename):
    with (folder / filename).open(
        "r", newline="", encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


def close_enough(actual, expected, tolerance=0.00001):
    return abs(actual - expected) <= tolerance


def check_oee(folder):
    orders = load_csv(folder, "production_order.csv")
    events = load_csv(folder, "state_event.csv")
    counts = load_csv(folder, "production_count.csv")
    inspections = load_csv(folder, "quality_inspection.csv")
    machine_products = load_csv(folder, "machine_product.csv")
    aggregates = load_csv(folder, "oee_aggregate.csv")

    ideals = {
        (row["machine_id"], row["product_id"]):
        float(row["ideal_cycle_seconds"])
        for row in machine_products
    }

    run_minutes = defaultdict(float)

    for row in events:
        if row["issue_type"] or row["state"] != "RUN":
            continue

        start = datetime.fromisoformat(row["start_at"])
        end = datetime.fromisoformat(row["end_at"])

        run_minutes[row["order_id"]] += (
            end - start
        ).total_seconds() / 60

    total_units = defaultdict(int)

    for row in counts:
        if not row["issue_type"]:
            total_units[row["order_id"]] += int(
                row["delta_total"]
            )

    scrap_units = defaultdict(int)

    for row in inspections:
        if not row["issue_type"]:
            scrap_units[row["order_id"]] += int(
                row["scrap_units"]
            )

    order_lookup = {
        row["order_id"]: row for row in orders
    }

    problems = []

    for row in aggregates:
        order_id = row["aggregate_id"].replace("OEE-", "", 1)
        order = order_lookup.get(order_id)

        if order is None:
            problems.append(f"Missing order: {order_id}")
            continue

        run = run_minutes[order_id]
        planned = float(row["planned_minutes"])
        total = total_units[order_id]
        good = max(0, total - scrap_units[order_id])

        ideal = ideals[
            (order["machine_id"], order["product_id"])
        ]

        availability = run / planned if planned else 0
        performance = (
            total * ideal / (run * 60)
            if run else 0
        )
        quality = good / total if total else 0
        oee = availability * performance * quality

        expected = {
            "run_minutes": run,
            "total_units": total,
            "good_units": good,
            "availability": availability,
            "performance": performance,
            "quality": quality,
            "oee": oee,
        }

        for field, value in expected.items():
            actual = float(row[field])

            if not close_enough(actual, value):
                problems.append(
                    f"{order_id}: {field} "
                    f"stored={actual:.6f} "
                    f"calculated={value:.6f}"
                )

    print("\nYOTTAFLEX OEE - INDEPENDENT CALCULATION CHECK")
    print("=" * 55)
    print(f"Dataset: {folder}")
    print(f"Orders: {len(orders)}")
    print(f"OEE aggregates checked: {len(aggregates)}")
    print(f"Calculation mismatches: {len(problems)}")

    if problems:
        print("\nFirst mismatches:")
        for problem in problems[:15]:
            print(" -", problem)
        print("\nRESULT: FAIL")
        return False

    print("\nRESULT: PASS")
    print("All stored OEE calculations match source data.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--folder",
        default="outputs/full"
    )
    args = parser.parse_args()

    try:
        passed = check_oee(Path(args.folder))
        raise SystemExit(0 if passed else 1)
    except (OSError, ValueError, KeyError) as error:
        print("ERROR:", error)
        raise SystemExit(1)
