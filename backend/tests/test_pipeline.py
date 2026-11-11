
import csv
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

from src.main import build
import src.validator as validator


def read_rows(folder, name):
    with (folder / f"{name}.csv").open(
        newline="", encoding="utf-8"
    ) as file:
        return list(csv.DictReader(file))


class PipelineTest(unittest.TestCase):

    def test_reproducible(self):
        with tempfile.TemporaryDirectory() as a, \
             tempfile.TemporaryDirectory() as b:

            x, v = build(
                Path(a), days=1, machines=2,
                events=100, records=100, seed=42
            )
            y, w = build(
                Path(b), days=1, machines=2,
                events=100, records=100, seed=42
            )

            self.assertEqual(x["sha256"], y["sha256"])
            self.assertEqual(v["status"], "PASS")
            self.assertEqual(w["status"], "PASS")
            self.assertEqual(v["labelled_anomalies"], 5)

    def test_relationship_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            build(
                folder, days=1, machines=2,
                events=100, records=100, seed=42
            )

            orders = {
                row["order_id"]: row
                for row in read_rows(folder, "production_order")
            }

            for table in (
                "state_event",
                "production_count",
                "quality_inspection",
            ):
                for row in read_rows(folder, table):
                    order = orders[row["order_id"]]

                    self.assertEqual(
                        row["machine_id"],
                        order["machine_id"],
                    )
                    self.assertEqual(
                        row["shift_id"],
                        order["shift_id"],
                    )

    def test_oee_calculations(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            build(
                folder, days=1, machines=2,
                events=100, records=100, seed=42
            )

            orders = read_rows(folder, "production_order")
            aggregates = read_rows(folder, "oee_aggregate")
            counts = read_rows(folder, "production_count")
            inspections = read_rows(
                folder, "quality_inspection"
            )

            totals = Counter()
            scrap = Counter()

            for row in counts:
                if not row["issue_type"]:
                    totals[row["order_id"]] += int(
                        row["delta_total"]
                    )

            for row in inspections:
                if not row["issue_type"]:
                    scrap[row["order_id"]] += int(
                        row["scrap_units"]
                    )

            order_by_pair = {
                (row["machine_id"], row["shift_id"]): row
                for row in orders
            }

            for aggregate in aggregates:
                pair = (
                    aggregate["machine_id"],
                    aggregate["shift_id"],
                )
                order = order_by_pair[pair]
                order_id = order["order_id"]

                total = totals[order_id]
                good = max(0, total - scrap[order_id])

                self.assertEqual(
                    int(aggregate["total_units"]), total
                )
                self.assertEqual(
                    int(aggregate["good_units"]), good
                )

                availability = float(
                    aggregate["availability"]
                )
                performance = float(
                    aggregate["performance"]
                )
                quality = float(
                    aggregate["quality"]
                )
                oee = float(aggregate["oee"])

                self.assertAlmostEqual(
                    oee,
                    availability * performance * quality,
                    places=5,
                )

    def test_independent_anomaly_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            build(
                folder, days=1, machines=2,
                events=100, records=100, seed=42
            )

            original_folder = validator.DATA_FOLDER

            try:
                validator.DATA_FOLDER = folder
                self.assertTrue(validator.validate())
            finally:
                validator.DATA_FOLDER = original_folder


if __name__ == "__main__":
    unittest.main()
