
"""Deterministic synthetic OEE generator, analyzer, validator and exporter."""

import argparse
import collections
import csv
import hashlib
import heapq
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 20261022

FIELDS = {
    "plant": ["plant_id", "name", "status"],
    "line": ["line_id", "plant_id", "name", "status"],
    "machine": ["machine_id", "line_id", "name", "status"],
    "shift": [
        "shift_id", "plant_id", "shift_date", "code",
        "start_at", "end_at", "planned_break_minutes"
    ],
    "product": ["product_id", "name", "status"],
    "machine_product": [
        "machine_id", "product_id", "ideal_cycle_seconds",
        "effective_from", "effective_to"
    ],
    "production_order": [
        "order_id", "machine_id", "shift_id",
        "product_id", "status", "planned_units"
    ],
    "downtime_reason": [
        "reason_id", "description", "category", "planned"
    ],
    "state_event": [
        "event_id", "machine_id", "order_id", "shift_id",
        "start_at", "end_at", "state", "reason_id",
        "observed_ideal_cycle_seconds", "issue_type"
    ],
    "production_count": [
        "count_id", "order_id", "machine_id", "shift_id",
        "at", "delta_total", "correction_of", "issue_type"
    ],
    "quality_inspection": [
        "inspection_id", "order_id", "machine_id", "shift_id",
        "at", "scrap_units", "rework_units", "issue_type"
    ],
    "oee_aggregate": [
        "aggregate_id", "machine_id", "shift_id",
        "planned_minutes", "run_minutes", "total_units",
        "good_units", "availability", "performance",
        "quality", "oee", "status"
    ],
    "ground_truth": [
        "issue_id", "entity", "record_id",
        "issue_type", "expected_decision"
    ],
}


def stamp(d, hour, minute=0):
    return (
        datetime.combine(d, datetime.min.time())
        + timedelta(hours=hour, minutes=minute)
    ).isoformat(timespec="seconds")


def save(out, table, rows):
    with (out / f"{table}.csv").open(
        "w", newline="", encoding="utf8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=FIELDS[table]
        )
        writer.writeheader()
        writer.writerows(rows)


def build(
    out,
    days=2,
    machines=6,
    events=300,
    records=900,
    seed=SEED
):
    if min(days, machines, events, records) < 1:
        raise ValueError("All scales must be positive")

    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)

    data = {key: [] for key in FIELDS}
    truth = data["ground_truth"]

    data["plant"] = [
        dict(
            plant_id="PLANT-001",
            name="Demo Factory",
            status="ACTIVE"
        )
    ]

    data["line"] = [
        dict(
            line_id=f"LINE-{i:03}",
            plant_id="PLANT-001",
            name=f"Line {i}",
            status="ACTIVE"
        )
        for i in range(1, 6)
    ]

    data["machine"] = [
        dict(
            machine_id=f"MCH-{i:03}",
            line_id=f"LINE-{((i - 1) % 5) + 1:03}",
            name=f"Machine {i}",
            status="ACTIVE"
        )
        for i in range(1, machines + 1)
    ]

    data["product"] = [
        dict(
            product_id=f"PROD-{i:03}",
            name=f"Product {i}",
            status="ACTIVE"
        )
        for i in range(1, 21)
    ]

    start = date(2026, 1, 1)

    for machine in data["machine"]:
        for product in data["product"]:
            data["machine_product"].append(
                dict(
                    machine_id=machine["machine_id"],
                    product_id=product["product_id"],
                    ideal_cycle_seconds=round(
                        rng.uniform(12, 55), 2
                    ),
                    effective_from="2026-01-01",
                    effective_to=""
                )
            )

    for day in range(days):
        shift_date = start + timedelta(days=day)

        for code, hour in [
            ("A", 6),
            ("B", 14),
            ("C", 22)
        ]:
            shift_id = (
                f"SHIFT-{shift_date.isoformat()}-{code}"
            )

            data["shift"].append(
                dict(
                    shift_id=shift_id,
                    plant_id="PLANT-001",
                    shift_date=shift_date.isoformat(),
                    code=code,
                    start_at=stamp(shift_date, hour),
                    end_at=stamp(shift_date, hour + 8),
                    planned_break_minutes=30
                )
            )

    data["downtime_reason"] = [
        dict(
            reason_id="R-BREAK",
            description="Scheduled break",
            category="BREAK",
            planned="true"
        ),
        dict(
            reason_id="R-FAIL",
            description="Equipment fault",
            category="FAILURE",
            planned="false"
        ),
        dict(
            reason_id="R-CHANGE",
            description="Product changeover",
            category="CHANGEOVER",
            planned="false"
        ),
        dict(
            reason_id="R-MICRO",
            description="Micro-stop",
            category="MICRO_STOP",
            planned="false"
        )
    ]

    orders = []
    segments = []
    sequence = collections.Counter()

    for shift in data["shift"]:
        shift_start = datetime.fromisoformat(
            shift["start_at"]
        )

        for machine in data["machine"]:
            index = len(orders) + 1

            product_id = (
                f"PROD-{rng.randint(1, 20):03}"
            )
            order_id = f"PO-2026-{index:06}"

            order = dict(
                order_id=order_id,
                machine_id=machine["machine_id"],
                shift_id=shift["shift_id"],
                product_id=product_id,
                status="COMPLETED",
                planned_units=600
            )

            orders.append(order)

            # 480 minutes:
            # 30 break + 10 changeover + 5 downtime
            # + 3 micro-stop + 432 run.
            pattern = [
                ("RUN", 120, None),
                ("BREAK", 30, "R-BREAK"),
                ("RUN", 120, None),
                ("CHANGEOVER", 10, "R-CHANGE"),
                ("RUN", 100, None),
                ("DOWN", 5, "R-FAIL"),
                ("RUN", 60, None),
                ("MICRO_STOP", 3, "R-MICRO"),
                ("RUN", 32, None)
            ]

            minute = 0

            for state, duration, reason in pattern:
                machine_id = machine["machine_id"]

                sequence[machine_id] += 1

                event_id = (
                    f"EVT-{machine_id}-"
                    f"{sequence[machine_id]:06}"
                )

                begin = (
                    shift_start
                    + timedelta(minutes=minute)
                )
                end = (
                    begin
                    + timedelta(minutes=duration)
                )

                minute += duration

                segments.append(
                    dict(
                        event_id=event_id,
                        machine_id=machine_id,
                        order_id=order_id,
                        shift_id=shift["shift_id"],
                        start_at=begin.isoformat(
                            timespec="seconds"
                        ),
                        end_at=end.isoformat(
                            timespec="seconds"
                        ),
                        state=state,
                        reason_id=reason or "",
                        issue_type=""
                    )
                )

    data["production_order"] = orders

    # Subdivide RUN intervals to reach requested
    # event volume without changing time totals.
    base = len(segments)

    if events < base:
        events = base

    heap = []

    for index, event in enumerate(segments):
        if event["state"] != "RUN":
            continue

        duration = (
            datetime.fromisoformat(event["end_at"])
            - datetime.fromisoformat(event["start_at"])
        ).total_seconds()

        if duration >= 2:
            heapq.heappush(
                heap, (-duration, index)
            )

    while len(segments) < events and heap:
        _, index = heapq.heappop(heap)

        event = segments[index]

        begin = datetime.fromisoformat(
            event["start_at"]
        )
        end = datetime.fromisoformat(
            event["end_at"]
        )

        duration = (end - begin).total_seconds()

        if duration < 2:
            continue

        middle = begin + timedelta(
            seconds=int(duration // 2)
        )

        if middle <= begin or middle >= end:
            continue

        event["end_at"] = middle.isoformat(
            timespec="seconds"
        )

        machine_id = event["machine_id"]
        sequence[machine_id] += 1

        extra = dict(
            event,
            event_id=(
                f"EVT-{machine_id}-"
                f"{sequence[machine_id]:06}"
            ),
            start_at=middle.isoformat(
                timespec="seconds"
            ),
            end_at=end.isoformat(
                timespec="seconds"
            )
        )

        segments.append(extra)

        for part_index in (
            index,
            len(segments) - 1
        ):
            part = segments[part_index]

            part_duration = (
                datetime.fromisoformat(
                    part["end_at"]
                )
                - datetime.fromisoformat(
                    part["start_at"]
                )
            ).total_seconds()

            if part_duration >= 2:
                heapq.heappush(
                    heap,
                    (-part_duration, part_index)
                )

    order_by_id = {
        order["order_id"]: order
        for order in orders
    }

    ideal_by_pair = {
        (row["machine_id"], row["product_id"]):
        row["ideal_cycle_seconds"]
        for row in data["machine_product"]
    }

    for event in segments:
        order = order_by_id[
            event["order_id"]
        ]

        event["observed_ideal_cycle_seconds"] = (
            ideal_by_pair[
                (
                    event["machine_id"],
                    order["product_id"]
                )
            ]
        )

    data["state_event"] = segments

    # Generate counts from machine run time
    # and ideal cycle time.
    number_of_orders = len(orders)

    records = max(
        records,
        number_of_orders * 2
    )

    number_of_counts = records // 2
    number_of_inspections = (
        records - number_of_counts
    )

    count_sequence = collections.Counter()

    shift_lookup = {
        shift["shift_id"]: shift
        for shift in data["shift"]
    }

    ideals = {
        (
            row["machine_id"],
            row["product_id"]
        ): float(row["ideal_cycle_seconds"])
        for row in data["machine_product"]
    }

    run_seconds = 432 * 60
    targets = {}

    for order in orders:
        efficiency = rng.uniform(
            0.75, 0.98
        )

        ideal = ideals[
            (
                order["machine_id"],
                order["product_id"]
            )
        ]

        targets[order["order_id"]] = max(
            1,
            round(
                run_seconds / ideal
                * efficiency
            )
        )

    count_slots = collections.Counter(
        orders[i % number_of_orders]["order_id"]
        for i in range(number_of_counts)
    )

    remaining = dict(targets)

    for i in range(number_of_counts):
        order = orders[i % number_of_orders]

        order_id = order["order_id"]

        count_sequence[order_id] += 1

        number = count_sequence[order_id]
        slots = count_slots[order_id]

        delta = remaining[order_id] // slots

        if remaining[order_id] % slots:
            delta += 1

        remaining[order_id] -= delta
        count_slots[order_id] -= 1

        data["production_count"].append(
            dict(
                count_id=(
                    f"CNT-{order_id}-{number:06}"
                ),
                order_id=order_id,
                machine_id=order["machine_id"],
                shift_id=order["shift_id"],
                at=shift_lookup[
                    order["shift_id"]
                ]["start_at"],
                delta_total=delta,
                correction_of="",
                issue_type=""
            )
        )

    # VALID CORRECTION HISTORY
    #
    # Preserve the first original record.
    # Use a second existing count record for
    # the same order as a negative adjustment.
    #
    # The original count includes the units
    # previously carried by the second record
    # plus one excess unit.
    #
    # The correction removes that one unit.
    # The net total remains unchanged.
    #
    # This preserves the required number of
    # count records and their immutable IDs.

    counts_by_order = collections.defaultdict(
        list
    )

    for count in data["production_count"]:
        counts_by_order[
            count["order_id"]
        ].append(count)

    valid_correction_created = False

    for order in orders:
        group = counts_by_order[
            order["order_id"]
        ]

        if len(group) < 2:
            continue

        original = group[0]
        correction = group[1]

        original_amount = int(
            original["delta_total"]
        )

        second_amount = int(
            correction["delta_total"]
        )

        if original_amount <= 0:
            continue

        if second_amount <= 0:
            continue

        # Record an initial overcount while
        # preserving the original count row.
        original["delta_total"] = (
            original_amount
            + second_amount
            + 1
        )

        # A new, separately identified record
        # corrects the one excess unit.
        correction["delta_total"] = -1

        correction["correction_of"] = (
            original["count_id"]
        )

        correction["at"] = (
            datetime.fromisoformat(
                original["at"]
            )
            + timedelta(minutes=1)
        ).isoformat(timespec="seconds")

        valid_correction_created = True
        break

    if not valid_correction_created:
        raise ValueError(
            "Unable to create a valid correction "
            "from existing count records"
        )

    # Generate quality inspections.
    inspection_slots = collections.Counter(
        orders[i % number_of_orders]["order_id"]
        for i in range(number_of_inspections)
    )

    scrap_remaining = {
        order_id: round(
            quantity
            * rng.uniform(0.005, 0.035)
        )
        for order_id, quantity
        in targets.items()
    }

    for i in range(number_of_inspections):
        order = orders[i % number_of_orders]
        order_id = order["order_id"]

        slots = inspection_slots[
            order_id
        ]

        scrap_delta = (
            scrap_remaining[order_id]
            + slots - 1
        ) // slots

        scrap_remaining[order_id] -= (
            scrap_delta
        )

        inspection_slots[order_id] -= 1

        data["quality_inspection"].append(
            dict(
                inspection_id=(
                    f"QC-2026-{i + 1:06}"
                ),
                order_id=order_id,
                machine_id=order["machine_id"],
                shift_id=order["shift_id"],
                at=shift_lookup[
                    order["shift_id"]
                ]["start_at"],
                scrap_units=scrap_delta,
                rework_units=0,
                issue_type=""
            )
        )

    # Record five intentional anomalies.
    def mark(entity, row, issue, decision):
        row["issue_type"] = issue

        id_field = {
            "state_event": "event_id",
            "production_count": "count_id",
            "quality_inspection": "inspection_id"
        }[entity]

        truth.append(
            dict(
                issue_id=(
                    f"ISSUE-{len(truth) + 1:05}"
                ),
                entity=entity,
                record_id=row[id_field],
                issue_type=issue,
                expected_decision=decision
            )
        )

    if len(segments) > 2:
        target = segments[-1]

        predecessors = [
            event
            for event in segments[:-1]
            if (
                event["machine_id"]
                == target["machine_id"]
                and event["shift_id"]
                == target["shift_id"]
                and event["end_at"]
                <= target["start_at"]
            )
        ]

        if predecessors:
            previous = max(
                predecessors,
                key=lambda event: event["end_at"]
            )

            target["start_at"] = (
                datetime.fromisoformat(
                    previous["end_at"]
                )
                - timedelta(minutes=1)
            ).isoformat(timespec="seconds")

            mark(
                "state_event",
                target,
                "OVERLAPPING_STATE",
                "FLAG_EXCLUDE"
            )

    if data["production_count"]:
        count = data["production_count"][-1]

        count["delta_total"] = -99

        mark(
            "production_count",
            count,
            "NEGATIVE_WITHOUT_CORRECTION",
            "FLAG_EXCLUDE"
        )

    if data["quality_inspection"]:
        inspection = (
            data["quality_inspection"][-1]
        )

        inspection["scrap_units"] = 99999

        mark(
            "quality_inspection",
            inspection,
            "SCRAP_EXCEEDS_TOTAL",
            "FLAG_EXCLUDE"
        )

    if len(segments) > 5:
        cycle_target = segments[-5]

        cycle_target[
            "observed_ideal_cycle_seconds"
        ] = round(
            float(
                cycle_target[
                    "observed_ideal_cycle_seconds"
                ]
            ) * 1.5,
            2
        )

        mark(
            "state_event",
            cycle_target,
            "WRONG_IDEAL_CYCLE_TIME",
            "REVIEW_MASTER_DATA"
        )

    if len(segments) > 5:
        down_target = segments[-3]

        breaks = [
            event
            for event in segments
            if (
                event["machine_id"]
                == down_target["machine_id"]
                and event["shift_id"]
                == down_target["shift_id"]
                and event["state"] == "BREAK"
            )
        ]

        if breaks:
            planned_break = breaks[0]

            begin = (
                datetime.fromisoformat(
                    planned_break["start_at"]
                )
                + timedelta(minutes=5)
            )

            down_target["start_at"] = (
                begin.isoformat(
                    timespec="seconds"
                )
            )

            down_target["end_at"] = (
                begin
                + timedelta(minutes=10)
            ).isoformat(timespec="seconds")

            down_target["state"] = "DOWN"
            down_target["reason_id"] = (
                "R-FAIL"
            )

            mark(
                "state_event",
                down_target,
                "DOWNTIME_OVERLAPS_BREAK",
                "REVIEW_SCHEDULE"
            )

    # Calculate OEE from clean source records.
    clean_events = [
        event
        for event in segments
        if not event["issue_type"]
    ]

    counts = collections.Counter()
    scrap = collections.Counter()

    for count in data["production_count"]:
        if not count["issue_type"]:
            counts[
                count["order_id"]
            ] += int(count["delta_total"])

    for inspection in data[
        "quality_inspection"
    ]:
        if not inspection["issue_type"]:
            scrap[
                inspection["order_id"]
            ] += int(
                inspection["scrap_units"]
            )

    for order in orders:
        relevant = [
            event
            for event in clean_events
            if (
                event["order_id"]
                == order["order_id"]
            )
        ]

        run = sum(
            (
                datetime.fromisoformat(
                    event["end_at"]
                )
                - datetime.fromisoformat(
                    event["start_at"]
                )
            ).total_seconds() / 60
            for event in relevant
            if event["state"] == "RUN"
        )

        planned = 450.0

        total = counts[
            order["order_id"]
        ]

        good = max(
            0,
            total - scrap[order["order_id"]]
        )

        ideal = ideals[
            (
                order["machine_id"],
                order["product_id"]
            )
        ]

        availability = (
            run / planned
        )

        performance = (
            total * ideal / (run * 60)
            if run else 0
        )

        quality = (
            good / total
            if total else 0
        )

        has_anomaly = any(
            event["order_id"]
            == order["order_id"]
            for event in segments
            if event["issue_type"]
        )

        status = (
            "REVIEW"
            if (
                performance > 1
                or performance < 0
                or availability > 1
                or has_anomaly
            )
            else "OK"
        )

        data["oee_aggregate"].append(
            dict(
                aggregate_id=(
                    f"OEE-{order['order_id']}"
                ),
                machine_id=order["machine_id"],
                shift_id=order["shift_id"],
                planned_minutes=planned,
                run_minutes=round(run, 5),
                total_units=total,
                good_units=good,
                availability=round(
                    availability, 6
                ),
                performance=round(
                    performance, 6
                ),
                quality=round(quality, 6),
                oee=round(
                    availability
                    * performance
                    * quality,
                    6
                ),
                status=status
            )
        )

    for table, rows in data.items():
        save(out, table, rows)

    validation = validate(data)

    (
        out / "validation_summary.json"
    ).write_text(
        json.dumps(
            validation, indent=2
        ),
        encoding="utf-8"
    )

    manifest = {
        "seed": seed,
        "days": days,
        "machines": machines,
        "requested_events": events,
        "requested_count_inspection_records": records,
        "row_counts": {
            key: len(value)
            for key, value in data.items()
        },
        "sha256": {
            file.name: hashlib.sha256(
                file.read_bytes()
            ).hexdigest()
            for file in sorted(
                out.glob("*.csv")
            )
        },
        "provenance": (
            "Fully synthetic; no external source data"
        )
    }

    (
        out / "manifest.json"
    ).write_text(
        json.dumps(
            manifest, indent=2
        ),
        encoding="utf-8"
    )

    return manifest, validation


def validate(data):
    errors = []

    primary_keys = {
        "plant": "plant_id",
        "line": "line_id",
        "machine": "machine_id",
        "shift": "shift_id",
        "product": "product_id",
        "production_order": "order_id",
        "downtime_reason": "reason_id",
        "state_event": "event_id",
        "production_count": "count_id",
        "quality_inspection": "inspection_id",
        "oee_aggregate": "aggregate_id",
        "ground_truth": "issue_id"
    }

    for table, key in primary_keys.items():
        values = [
            row[key]
            for row in data[table]
        ]

        if len(values) != len(set(values)):
            errors.append(
                f"Duplicate PK in {table}"
            )

    lookup = {
        table: {
            row[key]
            for row in data[table]
        }
        for table, key
        in primary_keys.items()
    }

    relationships = {
        "line": {
            "plant_id": "plant"
        },
        "machine": {
            "line_id": "line"
        },
        "shift": {
            "plant_id": "plant"
        },
        "production_order": {
            "machine_id": "machine",
            "shift_id": "shift",
            "product_id": "product"
        },
        "state_event": {
            "machine_id": "machine",
            "order_id": "production_order",
            "shift_id": "shift"
        },
        "production_count": {
            "order_id": "production_order",
            "machine_id": "machine",
            "shift_id": "shift"
        },
        "quality_inspection": {
            "order_id": "production_order",
            "machine_id": "machine",
            "shift_id": "shift"
        }
    }

    for table, references in (
        relationships.items()
    ):
        for row in data[table]:
            for field, parent in (
                references.items()
            ):
                if row[field] not in (
                    lookup[parent]
                ):
                    errors.append(
                        f"Broken FK {table}.{field}"
                    )

    for event in data["state_event"]:
        if (
            not event["issue_type"]
            and event["start_at"]
            >= event["end_at"]
        ):
            errors.append(
                "Invalid state interval"
            )

    return {
        "status": (
            "PASS" if not errors else "FAIL"
        ),
        "structural_errors": errors,
        "labelled_anomalies": len(
            data["ground_truth"]
        ),
        "note": (
            "Structural checks only. "
            "Independently validate all five "
            "intentional anomalies using "
            "src/validator.py."
        )
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--out",
        default="outputs/starter"
    )

    parser.add_argument(
        "--profile",
        choices=["starter", "full"],
        default="starter"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=SEED
    )

    args = parser.parse_args()

    config = (
        dict(
            days=2,
            machines=6,
            events=300,
            records=900
        )
        if args.profile == "starter"
        else dict(
            days=90,
            machines=30,
            events=100000,
            records=500000
        )
    )

    manifest, validation = build(
        Path(args.out),
        seed=args.seed,
        **config
    )

    print(
        json.dumps(
            {
                "rows": manifest["row_counts"],
                "validation": validation
            },
            indent=2
        )
    )


if __name__ == "__main__":
    main()
