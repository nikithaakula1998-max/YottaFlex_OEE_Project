
"""Independently detect five intentional OEE data anomalies."""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DATA_FOLDER = Path(__file__).resolve().parent.parent / 'outputs' / 'starter'


def read_csv(name):
    with (DATA_FOLDER / name).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def overlap(a, b):
    return a['start'] < b['end'] and b['start'] < a['end']


def validate():
    counts = read_csv('production_count.csv')
    inspections = read_csv('quality_inspection.csv')
    events = read_csv('state_event.csv')
    orders = {r['order_id']: r for r in read_csv('production_order.csv')}
    ideals = {(r['machine_id'], r['product_id']): float(r['ideal_cycle_seconds'])
              for r in read_csv('machine_product.csv')}
    truth = read_csv('ground_truth.csv')
    found = set()
    details = []

    totals = defaultdict(int)
    for r in counts:
        value = int(r['delta_total'])
        if value < 0 and not r.get('correction_of', '').strip():
            found.add((r['count_id'], 'NEGATIVE_WITHOUT_CORRECTION'))
            details.append(f"Negative count: {r['count_id']}")
        else:
            totals[r['order_id']] += value

    # Flag the inspection that pushes scrap beyond production.
    scrap = defaultdict(int)
    for r in inspections:
        scrap[r['order_id']] += int(r['scrap_units'])
        if scrap[r['order_id']] > totals[r['order_id']]:
            found.add((r['inspection_id'], 'SCRAP_EXCEEDS_TOTAL'))
            details.append(f"Scrap exceeds total: {r['inspection_id']}")

    by_machine_shift = defaultdict(list)

    for r in events:
        try:
            start = datetime.fromisoformat(r['start_at'])
            end = datetime.fromisoformat(r['end_at'])
        except ValueError:
            details.append(f"Invalid timestamp: {r['event_id']}")
            continue

        if end <= start:
            details.append(f"Invalid interval: {r['event_id']}")
            continue

        event = {
            'id': r['event_id'],
            'start': start,
            'end': end,
            'state': r['state'],
            'row': r
        }

        by_machine_shift[
            (r['machine_id'], r['shift_id'])
        ].append(event)

        # Compare observed cycle time with machine-product master data.
        order = orders.get(r['order_id'])
        if order:
            expected = ideals.get(
                (r['machine_id'], order['product_id'])
            )
            observed = r.get('observed_ideal_cycle_seconds', '')

            if expected is not None and observed:
                if abs(float(observed) - expected) > 0.011:
                    found.add(
                        (r['event_id'], 'WRONG_IDEAL_CYCLE_TIME')
                    )
                    details.append(
                        f"Wrong ideal cycle: {r['event_id']} "
                        f"({observed} vs {expected})"
                    )

    overlap_count = 0

    for machine_shift, group in by_machine_shift.items():
        group.sort(key=lambda e: (e['start'], e['end']))

        # Detect actual overlapping intervals.
        for i, current in enumerate(group):
            for previous in group[:i]:
                if not overlap(previous, current):
                    continue

                overlap_count += 1

                found.add(
                    (current['id'], 'OVERLAPPING_STATE')
                )

                details.append(
                    f"State overlap: "
                    f"{current['id']} / {previous['id']}"
                )

                # Special case: downtime during a planned break.
                if (
                    current['state'] == 'DOWN'
                    and previous['state'] == 'BREAK'
                ):
                    found.add(
                        (
                            current['id'],
                            'DOWNTIME_OVERLAPS_BREAK'
                        )
                    )

                if (
                    previous['state'] == 'DOWN'
                    and current['state'] == 'BREAK'
                ):
                    found.add(
                        (
                            previous['id'],
                            'DOWNTIME_OVERLAPS_BREAK'
                        )
                    )

    print(
        '\nYOTTAFLEX OEE - INDEPENDENT ANOMALY VALIDATION'
    )
    print('=' * 55)

    print(f'Production records: {len(counts)}')
    print(f'Quality records: {len(inspections)}')
    print(f'State events: {len(events)}')
    print(
        f'Physical overlapping interval pairs: {overlap_count}'
    )

    print('\nFINDINGS')

    for item in details[:15]:
        print(' -', item)

    if len(details) > 15:
        print(f' ... plus {len(details) - 15} more')

    print('\nGROUND TRUTH COMPARISON')

    matches = 0

    for row in truth:
        key = (row['record_id'], row['issue_type'])
        ok = key in found

        matches += ok

        print(
            f"{'MATCH' if ok else 'NOT VERIFIED'}: "
            f"{row['issue_type']} [{row['record_id']}]"
        )

    print(
        f'\nGround-truth matches: {matches}/{len(truth)}'
    )

    print(
        'RESULT:',
        'PASS' if matches == len(truth) else 'INCOMPLETE'
    )

    return matches == len(truth)


if __name__ == '__main__':
    try:
        raise SystemExit(0 if validate() else 1)
    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        csv.Error
    ) as exc:
        print('VALIDATION ERROR:', exc)
        raise SystemExit(1)
