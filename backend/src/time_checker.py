
"""Check machine-shift time reconciliation and report anomalous shifts."""

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def read_csv(folder, filename):
    with (folder / filename).open(
        "r", encoding="utf-8", newline=""
    ) as file:
        return list(csv.DictReader(file))


def check_time(folder):
    shifts = {
        row["shift_id"]: row
        for row in read_csv(folder, "shift.csv")
    }

    machines = read_csv(folder, "machine.csv")
    events = read_csv(folder, "state_event.csv")
    truth = read_csv(folder, "ground_truth.csv")

    groups = defaultdict(list)

    for row in events:
        start = datetime.fromisoformat(row["start_at"])
        end = datetime.fromisoformat(row["end_at"])

        groups[
            (row["machine_id"], row["shift_id"])
        ].append({
            "id": row["event_id"],
            "start": start,
            "end": end,
            "state": row["state"],
            "issue": row["issue_type"],
        })

    expected_groups = {
        (machine["machine_id"], shift_id)
        for machine in machines
        for shift_id in shifts
    }

    problematic = set()
    unexpected = []
    clean_count = 0

    # Shifts containing deliberately corrupted state events.
    labelled_event_ids = {
        row["record_id"]
        for row in truth
        if row["entity"] == "state_event"
    }

    for key in sorted(expected_groups):
        machine_id, shift_id = key
        shift = shifts[shift_id]

        shift_start = datetime.fromisoformat(
            shift["start_at"]
        )
        shift_end = datetime.fromisoformat(
            shift["end_at"]
        )

        intervals = sorted(
            groups.get(key, []),
            key=lambda item: (
                item["start"], item["end"]
            )
        )

        has_labelled_event = any(
            event["id"] in labelled_event_ids
            for event in intervals
        )

        # All physical event intervals must cover the shift
        # exactly once, with no gaps or overlaps.
        cursor = shift_start
        problems = []

        for event in intervals:
            if event["start"] < cursor:
                problems.append("overlap")
            elif event["start"] > cursor:
                problems.append("gap")

            if event["end"] <= event["start"]:
                problems.append("invalid duration")

            if (
                event["start"] < shift_start
                or event["end"] > shift_end
            ):
                problems.append("outside shift")

            cursor = max(cursor, event["end"])

        if cursor != shift_end:
            problems.append("incomplete shift coverage")

        if not intervals:
            problems.append("no events")

        if problems or has_labelled_event:
            problematic.add(key)

            if not has_labelled_event:
                unexpected.append(
                    (machine_id, shift_id, sorted(set(problems)))
                )
        else:
            clean_count += 1

    print("\nYOTTAFLEX OEE - TIME RECONCILIATION")
    print("=" * 55)
    print(f"Dataset: {folder}")
    print(f"Expected machine-shifts: {len(expected_groups)}")
    print(f"Clean reconciled machine-shifts: {clean_count}")
    print(f"Flagged machine-shifts: {len(problematic)}")
    print(f"Unexpected problematic shifts: {len(unexpected)}")

    if unexpected:
        print("\nUnexpected problems:")
        for machine, shift, problems in unexpected[:15]:
            print(
                f" - {machine} / {shift}: "
                f"{', '.join(problems)}"
            )

        print("\nRESULT: FAIL")
        return False

    print("\nRESULT: PASS")
    print(
        "All unlabelled machine-shifts reconcile. "
        "Labelled anomalies are quarantined."
    )
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--folder", default="outputs/full"
    )
    args = parser.parse_args()

    try:
        passed = check_time(Path(args.folder))
        raise SystemExit(0 if passed else 1)
    except (OSError, ValueError, KeyError) as error:
        print("ERROR:", error)
        raise SystemExit(1)
