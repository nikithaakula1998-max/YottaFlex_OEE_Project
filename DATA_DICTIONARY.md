# Data dictionary

All identifiers are UTF-8 strings, required and unique where marked PK. All FK fields are required unless stated. Dates are ISO 8601; numeric units are explicit. Blank `effective_to`, `reason_id`, `correction_of`, and `issue_type` are allowed.

| Table | Fields (type / validation) |
|---|---|
| plant | plant_id TEXT PK; name TEXT nonblank; status ENUM ACTIVE,INACTIVE |
| line | line_id TEXT PK; plant_id TEXT FK plant; name TEXT nonblank; status ENUM ACTIVE,INACTIVE |
| machine | machine_id TEXT PK; line_id TEXT FK line; name TEXT nonblank; status ENUM ACTIVE,INACTIVE |
| shift | shift_id TEXT PK SHIFT-YYYY-MM-DD-A/B/C; plant_id TEXT FK plant; shift_date DATE; code ENUM A,B,C; start_at,end_at DATETIME end>start; planned_break_minutes INTEGER 0..480 |
| product | product_id TEXT PK; name TEXT nonblank; status ENUM ACTIVE,INACTIVE |
| machine_product | machine_id TEXT FK; product_id TEXT FK; ideal_cycle_seconds REAL >0 seconds; effective_from DATE; effective_to DATE optional and >= from; composite PK machine_id,product_id,effective_from |
| production_order | order_id TEXT PK PO-2026-######; machine_id FK; shift_id FK; product_id FK; status ENUM PLANNED,RUNNING,COMPLETED,CANCELLED; planned_units INTEGER >=0 |
| downtime_reason | reason_id TEXT PK; description TEXT nonblank; category ENUM BREAK,FAILURE,CHANGEOVER,MICRO_STOP; planned BOOLEAN |
| state_event | event_id TEXT PK EVT-machine-seq; machine_id/order_id/shift_id FKs; start_at,end_at DATETIME end>start; state ENUM RUN,BREAK,CHANGEOVER,DOWN,MICRO_STOP; reason_id optional FK; issue_type optional label |
| production_count | count_id TEXT PK CNT-order-seq; order_id/machine_id/shift_id FKs; at DATETIME; delta_total INTEGER signed units; correction_of optional FK production_count; issue_type optional label |
| quality_inspection | inspection_id TEXT PK QC-2026-######; order_id/machine_id/shift_id FKs; at DATETIME; scrap_units,rework_units INTEGER >=0 units; issue_type optional label |
| oee_aggregate | aggregate_id TEXT PK; machine_id/shift_id FKs; planned_minutes,run_minutes REAL >=0 minutes; total_units,good_units INTEGER >=0; availability,performance,quality,oee REAL ratios; status ENUM OK,REVIEW |
| ground_truth | issue_id TEXT PK; entity TEXT table name; record_id TEXT target ID; issue_type ENUM OVERLAPPING_STATE,NEGATIVE_WITHOUT_CORRECTION,SCRAP_EXCEEDS_TOTAL,WRONG_IDEAL_CYCLE_TIME,DOWNTIME_OVERLAPS_BREAK; expected_decision ENUM FLAG_EXCLUDE,REVIEW_MASTER_DATA,REVIEW_SCHEDULE |

Cardinality: plant 1:N lines/shifts; line 1:N machines; machine N:M products through machine_product (effective dated); machine/shift/product 1:N production orders; order 1:N state events/counts/inspections; machine+shift 1:1 aggregate in this simplified model. A machine_product cycle time should be selected by event effective date. In the starter there is one active cycle time per pair.

Production-order lifecycle: PLANNED -> RUNNING -> COMPLETED or CANCELLED (simplified generator creates completed orders directly). Event histories are append-only; the starter does not simulate all intermediate order transitions. For each child event, the machine and shift should match its referenced order; stricter validation is a future enhancement.
