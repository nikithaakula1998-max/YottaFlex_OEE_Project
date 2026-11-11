
# YottaFlex OEE Manufacturing Analytics — Data Dictionary

## 1. Overview

This document describes the synthetic manufacturing datasets used by the YottaFlex OEE Manufacturing Analytics project.

It covers:

- Data entities and fields
- Data types and units
- Primary and foreign keys
- Required and optional values
- Allowed values and validation rules
- Relationships and cardinality
- Effective-dated machine-product relationships
- Production-count corrections
- Manufacturing lifecycle and validation limitations

All generated manufacturing data is synthetic.

Dates and timestamps use ISO 8601 representations. Identifiers are UTF-8 strings.

PK means Primary Key. FK means Foreign Key.

## 2. Manufacturing Data Entities

| Table | Fields and validation rules |
|---|---|
| `plant` | `plant_id` TEXT PK; `name` TEXT nonblank; `status` ENUM ACTIVE, INACTIVE |
| `line` | `line_id` TEXT PK; `plant_id` TEXT FK to plant; `name` TEXT nonblank; `status` ENUM ACTIVE, INACTIVE |
| `machine` | `machine_id` TEXT PK; `line_id` TEXT FK to line; `name` TEXT nonblank; `status` ENUM ACTIVE, INACTIVE |
| `shift` | `shift_id` TEXT PK; `plant_id` TEXT FK to plant; `shift_date` DATE; `code` ENUM A, B, C; `start_at`, `end_at` DATETIME with end later than start; `planned_break_minutes` INTEGER from 0 to 480 |
| `product` | `product_id` TEXT PK; `name` TEXT nonblank; `status` ENUM ACTIVE, INACTIVE |
| `machine_product` | `machine_id` TEXT FK; `product_id` TEXT FK; `ideal_cycle_seconds` REAL greater than 0; `effective_from` DATE; `effective_to` optional DATE, not earlier than `effective_from`; composite PK (`machine_id`, `product_id`, `effective_from`) |
| `production_order` | `order_id` TEXT PK; `machine_id`, `shift_id`, `product_id` FKs; `status` ENUM PLANNED, RUNNING, COMPLETED, CANCELLED; `planned_units` INTEGER greater than or equal to 0 |
| `downtime_reason` | `reason_id` TEXT PK; `description` TEXT nonblank; `category` ENUM BREAK, FAILURE, CHANGEOVER, MICRO_STOP; `planned` BOOLEAN |
| `state_event` | `event_id` TEXT PK; `machine_id`, `order_id`, `shift_id` FKs; `start_at`, `end_at` DATETIME with end later than start; `state` ENUM RUN, BREAK, CHANGEOVER, DOWN, MICRO_STOP; optional `reason_id` FK; optional `issue_type` |
| `production_count` | `count_id` TEXT PK; `order_id`, `machine_id`, `shift_id` FKs; `at` DATETIME; `delta_total` INTEGER signed units; optional `correction_of` self-referencing FK; optional `issue_type` |
| `quality_inspection` | `inspection_id` TEXT PK; `order_id`, `machine_id`, `shift_id` FKs; `at` DATETIME; `scrap_units`, `rework_units` INTEGER greater than or equal to 0; optional `issue_type` |
| `oee_aggregate` | `aggregate_id` TEXT PK; `machine_id`, `shift_id` FKs; `planned_minutes`, `run_minutes` REAL greater than or equal to 0; `total_units`, `good_units` INTEGER greater than or equal to 0; `availability`, `performance`, `quality`, `oee` REAL ratios; `status` ENUM OK, REVIEW |
| `ground_truth` | `issue_id` TEXT PK; `entity` TEXT target table name; `record_id` TEXT target identifier; `issue_type` ENUM OVERLAPPING_STATE, NEGATIVE_WITHOUT_CORRECTION, SCRAP_EXCEEDS_TOTAL, WRONG_IDEAL_CYCLE_TIME, DOWNTIME_OVERLAPS_BREAK; `expected_decision` ENUM FLAG_EXCLUDE, REVIEW_MASTER_DATA, REVIEW_SCHEDULE |

The operational SQLite database contains 12 tables.

`ground_truth.csv` is stored separately and is not imported into the operational SQLite database.

## 3. Identifier Rules

Identifiers are intended to be unique and stable.

Examples:

- Production order: `PO-2026-000001`
- Shift: `SHIFT-2026-01-01-A`
- State event: `EVT-MCH-001-000001`
- Production count: `CNT-PO-2026-000001-000001`
- Quality inspection: `QC-2026-000001`

The generator uses zero-padded identifiers for consistent sorting and traceability.

Primary-key uniqueness and selected structural relationships are checked during generation.

## 4. Entity Relationships and Cardinality

| Relationship | Cardinality |
|---|---|
| Plant to Line | One-to-many |
| Plant to Shift | One-to-many |
| Line to Machine | One-to-many |
| Machine to Product | Many-to-many through `machine_product` |
| Machine to Production Order | One-to-many |
| Shift to Production Order | One-to-many |
| Product to Production Order | One-to-many |
| Production Order to State Event | One-to-many |
| Production Order to Production Count | One-to-many |
| Production Order to Quality Inspection | One-to-many |
| Machine and Shift to OEE Aggregate | One aggregate per machine-shift in this simplified dataset |
| Production Count to Correction | Self-referencing relationship through `correction_of` |

The `machine_product` table is a bridge table representing which products can run on which machines.

The bridge also records ideal cycle times and effective dates.

## 5. Effective-Dated Machine-Product Relationships

The `machine_product` table contains:

- `machine_id`
- `product_id`
- `ideal_cycle_seconds`
- `effective_from`
- `effective_to`

`ideal_cycle_seconds` represents the ideal manufacturing time for one unit, measured in seconds.

`effective_from` indicates when the machine-product relationship becomes valid.

`effective_to` optionally indicates when that relationship stops being valid.

The intended business rule is to select the ideal cycle time applicable to the manufacturing event's date.

The generated datasets use one active ideal-cycle-time configuration per machine-product pair.

Complete historical cycle-time versioning and enforcement of every effective-date boundary are not demonstrated.

## 6. Production Count Correction History

The `production_count` table records signed production changes using `delta_total`.

A normal production increment generally has a positive `delta_total`.

A valid correction can have a negative adjustment and reference an earlier count through `correction_of`.

### Correction rules

A valid linked correction should:

1. Have a unique `count_id`.
2. Reference an existing original count.
3. Use `correction_of` to identify that original count.
4. Belong to the same production order as the original.
5. Have a timestamp later than the original count.
6. Retain both original and correction records in the generated dataset.

The updated full-scale generator creates one valid linked correction with a `delta_total` adjustment of `-1`.

The correction relationship was checked in both the CSV data and the imported SQLite database.

The dataset also includes a separate deliberately invalid negative production count without a correction reference.

That invalid record is labelled `NEGATIVE_WITHOUT_CORRECTION` for anomaly evaluation.

The generated records demonstrate correction traceability. They do not constitute a complete database-level immutable audit-log implementation.

## 7. Production Order Lifecycle

The documented production-order statuses are:

- `PLANNED`
- `RUNNING`
- `COMPLETED`
- `CANCELLED`

The intended lifecycle is:

`PLANNED → RUNNING → COMPLETED`

An order may also be cancelled according to business rules.

The current synthetic generator creates production orders with final statuses directly rather than recording every intermediate status transition.

Therefore, the dataset does not provide a complete event-by-event production-order lifecycle history.

This is a documented implementation limitation.

## 8. Machine-State Events

The `state_event` dataset represents machine activity over time.

Supported states include:

- `RUN`
- `BREAK`
- `CHANGEOVER`
- `DOWN`
- `MICRO_STOP`

Each event has a start timestamp and an end timestamp.

The intended rules require the end timestamp to be later than the start timestamp and normally prohibit conflicting machine-state intervals.

The generator deliberately injects overlapping events to test anomaly detection.

Downtime reasons provide additional context for machine stops and planned breaks.

The independent time-reconciliation checker distinguishes clean machine-shifts from shifts containing labelled anomalies.

## 9. Quality Inspection Rules

The `quality_inspection` dataset contains quality outcomes associated with production orders.

`scrap_units` represents rejected units.

`rework_units` represents units requiring rework.

Both fields use integer unit counts and should normally be nonnegative.

Scrap quantities should be consistent with the related production totals.

The generator deliberately creates one case where scrap exceeds production, labelled `SCRAP_EXCEEDS_TOTAL`.

## 10. OEE Aggregate Rules

The `oee_aggregate` dataset stores manufacturing effectiveness metrics.

### Availability

Availability = Run Time / Planned Production Time

### Performance

Performance = (Total Units × Ideal Cycle Time) / Run Time

### Quality

Quality = Good Units / Total Units

### Overall OEE

OEE = Availability × Performance × Quality

Time values are stored in minutes, while ideal cycle time is measured in seconds. Calculations must convert units consistently.

The generator uses a 480-minute shift with a 30-minute planned break, giving 450 minutes of planned production time.

The independent OEE checker recalculates stored aggregate values from source data.

On the updated full-scale dataset, all 8,100 OEE aggregates passed independent verification with zero mismatches.

## 11. Ground-Truth Anomalies

The generator includes five deliberately labelled anomaly types.

| Issue type | Meaning |
|---|---|
| `OVERLAPPING_STATE` | Machine-state intervals overlap |
| `NEGATIVE_WITHOUT_CORRECTION` | Negative production count without a valid correction reference |
| `SCRAP_EXCEEDS_TOTAL` | Scrap quantity exceeds production total |
| `WRONG_IDEAL_CYCLE_TIME` | Event contains an incorrect observed ideal cycle time |
| `DOWNTIME_OVERLAPS_BREAK` | Downtime overlaps a planned break |

The `ground_truth.csv` file records expected anomaly labels and decisions.

The independent validator checks whether these expected anomalies are detected.

A 5/5 match demonstrates successful detection of the labelled cases, but does not prove that all possible anomalies or false positives have been eliminated.

## 12. Validation and Integrity

The project includes multiple validation layers.

### Structural generation checks

The generator checks selected record counts, identifiers, and structural relationships.

### Automated unit tests

The automated test suite covers:

- Deterministic reproducibility
- Relationship integrity
- OEE arithmetic
- Independent anomaly validation

The relationship-integrity test checks that generated child records reference the correct machine and shift for their production order.

These tests cover the implemented scenarios; they do not enforce every possible business rule.

### Independent validation

The independent validator detects the five labelled anomaly types.

The OEE checker independently recalculates aggregate values.

The time checker verifies machine-shift reconciliation and identifies deliberately flagged shifts.

### SQLite checks

The updated full-scale test database produced:

- `PRAGMA integrity_check`: `ok`
- `PRAGMA foreign_key_check`: 0 violations
- Production counts: 250,000
- Quality inspections: 250,000
- OEE aggregates: 8,100

Foreign-key enforcement is disabled during bulk loading, so the separate foreign-key verification is important.

Passing these checks confirms the declared SQLite relationships in the tested database, but does not prove all lifecycle, temporal, or domain-specific constraints.

## 13. Known Limitations

- All records are synthetic.
- Complete production-order status-transition history is not implemented.
- The generated correction relationship demonstrates traceability but not a fully immutable database audit system.
- Effective-dated cycle-time history is simplified.
- The generator's structural validator does not enforce every cross-table business rule.
- Some deliberately anomalous records violate normal manufacturing expectations by design.
- Ground-truth detection is evaluated against five labelled cases rather than a comprehensive precision-and-recall benchmark.
- The system is designed for demonstration and evaluation, not direct production deployment.

## 14. Related Documentation

- `README.md` — Project overview, setup, and execution
- `backend/schema.sql` — SQLite table definitions and constraints
- `backend/tests/test_pipeline.py` — Automated tests
- `backend/src/validator.py` — Independent anomaly validation
- `backend/src/oee_checker.py` — Independent OEE verification
- `backend/src/time_checker.py` — Time reconciliation
- `INTERVIEW_GUIDE.md` — Project explanation and interview preparation
- `prompts/prompt_history.md` — AI-assistance summary
