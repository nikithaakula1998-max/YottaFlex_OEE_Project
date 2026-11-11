
# YottaFlex OEE Manufacturing Analytics

## Project Overview

This project generates, validates, stores, and analyzes synthetic manufacturing data to calculate Overall Equipment Effectiveness (OEE).

The system includes:

- A deterministic manufacturing data generator
- Production-count correction history
- Anomaly detection and ground-truth validation
- OEE calculation and independent verification
- Machine-shift time reconciliation
- A FastAPI backend
- A Streamlit analytics dashboard
- SQLite database support
- Dataset integrity verification using SHA-256 checksums
- Automated unit tests

All manufacturing data is synthetic.

## Technologies Used

- Python
- FastAPI
- Streamlit
- SQLite
- CSV and JSON
- SHA-256 checksums
- Python unittest
- Git and GitHub

## Full Dataset

| Component | Records |
|---|---:|
| Plants | 1 |
| Production lines | 5 |
| Machines | 30 |
| Products | 20 |
| Shifts | 270 |
| Machine-product relationships | 600 |
| Production orders | 8,100 |
| Downtime reasons | 4 |
| State events | 100,000 |
| Production counts | 250,000 |
| Quality inspections | 250,000 |
| OEE aggregates | 8,100 |
| Ground-truth anomalies | 5 |

The full dataset represents 90 days of synthetic manufacturing activity.

Generated CSV files and SQLite databases are excluded from GitHub because of their size. They can be recreated using the generator and database loader.

## OEE Calculation

Overall Equipment Effectiveness is calculated using three components.

**Availability**

Availability = Run Time / Planned Production Time

**Performance**

Performance = (Total Units × Ideal Cycle Time) / Run Time

**Quality**

Quality = Good Units / Total Units

**Overall OEE**

OEE = Availability × Performance × Quality

Planned breaks are excluded from planned production time. The generator uses a 480-minute shift with a 30-minute planned break, resulting in 450 minutes of planned production time.

OEE aggregates are derived from the generated manufacturing records. The independent checker recomputes these values and reports mismatches.

## Production Count Correction History

The `production_count` dataset supports corrections using the `correction_of` field.

A correction:

- Has its own unique count ID
- References an existing original count
- Belongs to the same production order
- Has a timestamp later than the referenced count
- Uses a signed adjustment instead of deleting the original record

The full dataset contains one valid linked correction with an adjustment of `-1`.

The original and correction records are both retained in the generated dataset and imported into SQLite.

The generator also deliberately creates a separate invalid negative-count example without a correction reference. This is used to test anomaly detection.

The correction relationship is validated in the generated CSV data and has been verified after SQLite import.

## Anomaly Detection

The independent validator checks for five deliberately injected anomaly types:

1. Overlapping machine-state intervals
2. Negative production counts without corrections
3. Scrap quantities exceeding production totals
4. Incorrect ideal cycle times
5. Downtime overlapping planned breaks

The expected anomalies are documented in `ground_truth.csv`.

Ground-truth labels are kept separate from the operational SQLite tables.

The validator checks whether the expected anomalies are detected. A successful ground-truth match does not establish that every possible unexpected anomaly has been detected.

## Verified Validation Results

The following results were obtained from the updated full-scale dataset generated in `outputs/full_correction_test`.

| Validation | Verified result |
|---|---|
| Full-scale generation | PASS |
| Structural validation | PASS |
| Valid linked correction | 1 |
| Independent anomaly validation | 5/5 matched |
| Independent OEE verification | 8,100 checked, 0 mismatches |
| Time reconciliation | PASS |
| SQLite integrity check | ok |
| SQLite foreign-key check | 0 violations |
| Production-count rows in SQLite | 250,000 |
| Quality-inspection rows in SQLite | 250,000 |
| OEE aggregate rows in SQLite | 8,100 |
| Automated unit tests | 4/4 PASS |

### Time Reconciliation

- Expected machine-shifts: 8,100
- Clean reconciled machine-shifts: 8,097
- Flagged machine-shifts: 3
- Unexpected problematic shifts: 0

The three flagged machine-shifts contain deliberately injected anomalies.

The updated generator was also tested with a smaller starter dataset before the full-scale run.

## Project Structure

```text
YottaFlex_OEE_Project/
    backend/
        src/
            main.py
            validator.py
            oee_checker.py
            time_checker.py
            api.py
        tests/
            test_pipeline.py
        schema.sql
        load_sqlite.py
        requirements.txt
        outputs/
    frontend/
        app.py
        requirements.txt
    prompts/
        prompt_history.md
    DATA_DICTIONARY.md
    INTERVIEW_GUIDE.md
    README.md
    .gitignore
```

The `backend/outputs/` directory is used for generated datasets and SQLite databases.

## How to Run

### 1. Clone the Repository

Open Windows PowerShell or a terminal.

```powershell
git clone https://github.com/nikithaakula1998-max/YottaFlex_OEE_Project.git
cd YottaFlex_OEE_Project
```

### 2. Create a Virtual Environment

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment again.

### 3. Install Dependencies

From the project root:

```powershell
python -m pip install -r backend\requirements.txt
python -m pip install -r frontend\requirements.txt
```

### 4. Generate the Full Dataset

Enter the backend folder:

```powershell
cd backend
```

Run:

```powershell
python -m src.main --profile full --out outputs/full
```

The generator creates synthetic manufacturing CSV files, ground-truth labels, a manifest, and a validation summary.

To create a smaller dataset:

```powershell
python -m src.main --profile starter --out outputs/starter
```

### 5. Validate Anomalies

From the backend folder:

```powershell
python -c "from pathlib import Path; import src.validator as v; v.DATA_FOLDER = Path('outputs/full'); assert v.validate()"
```

Expected result:

```text
Ground-truth matches: 5/5
RESULT: PASS
```

### 6. Independently Verify OEE

```powershell
python src/oee_checker.py --folder outputs/full
```

Expected result:

```text
OEE aggregates checked: 8100
Calculation mismatches: 0
RESULT: PASS
```

### 7. Verify Time Reconciliation

```powershell
python src/time_checker.py --folder outputs/full
```

Expected result:

```text
Expected machine-shifts: 8100
Clean reconciled machine-shifts: 8097
Flagged machine-shifts: 3
Unexpected problematic shifts: 0
RESULT: PASS
```

### 8. Run Automated Tests

```powershell
python -m unittest discover -s tests -v
```

Expected result:

```text
Ran 4 tests
OK
```

The automated tests cover:

- Deterministic reproducibility
- Relationship integrity
- OEE arithmetic
- Independent anomaly validation

### 9. Create the SQLite Database

```powershell
python load_sqlite.py --folder outputs/full --db outputs/full/oee.sqlite
```

The loader imports the 12 operational CSV datasets into SQLite.

`ground_truth.csv` is intentionally excluded from the operational database.

The loader refuses to overwrite an existing database. To rebuild it, use a new database path or back up and remove the existing database first.

### 10. Verify SQLite Integrity

From the backend folder:

```powershell
python -c "import sqlite3; c=sqlite3.connect('outputs/full/oee.sqlite'); print('Integrity:',c.execute('PRAGMA integrity_check').fetchone()[0]); print('Foreign key violations:',len(c.execute('PRAGMA foreign_key_check').fetchall())); print('OEE records:',c.execute('SELECT COUNT(*) FROM oee_aggregate').fetchone()[0]); c.close()"
```

Expected output:

```text
Integrity: ok
Foreign key violations: 0
OEE records: 8100
```

The loader disables foreign-key enforcement during bulk import. A separate foreign-key check is therefore important.

A passing SQLite foreign-key check verifies declared relationships, but does not establish that every domain-specific business rule is satisfied.

### 11. Start the FastAPI Backend

From the backend folder:

```powershell
python -m uvicorn src.api:app --reload
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

The backend exposes endpoints for health, summary information, machines, OEE records, labelled anomalies, and dataset manifest information.

### 12. Start the Streamlit Dashboard

Open another terminal in the main project folder and activate the virtual environment.

Run:

```powershell
python -m streamlit run frontend/app.py
```

Open:

http://localhost:8501

Keep the FastAPI server running while using the dashboard.

## Reproducibility

The generator uses the fixed random seed:

```text
20261022
```

The manifest records generation parameters, row counts, provenance information, and SHA-256 checksums.

Earlier full-scale generation runs were checked for matching CSV checksums across repeated runs.

The automated reproducibility test also checks deterministic generation on a smaller dataset.

The updated full-scale dataset has passed independent anomaly, OEE, time-reconciliation, and SQLite checks. A separate repeated full-scale checksum comparison for this updated generator has not yet been documented.

## API and Dashboard

The previously verified full-scale API and dashboard displayed:

- Machines: 30
- Machine-shifts: 8,100
- Labelled anomalies: 5
- Average OEE: 81.46%

The dashboard includes OEE component charts, machine comparisons, shift trends, machine filtering, and anomaly information.

The dashboard displays known ground-truth anomaly labels; it should not be confused with a live anomaly-detection service.

## Data Dictionary

See `DATA_DICTIONARY.md` for dataset descriptions, fields, relationships, data types, allowed values, and validation rules.

## AI Assistance Disclosure

AI assistance was used during development for implementation guidance, debugging, testing, and documentation.

See `prompts/prompt_history.md` for the documented AI-assistance summary.

That file is a summary rather than a complete verbatim transcript of every prompt.

## Notes and Limitations

- All manufacturing data is synthetic.
- Generated CSV files and SQLite databases are excluded from GitHub.
- Five deliberately injected anomalies are included for evaluation.
- Ground-truth labels are stored separately from operational SQLite data.
- OEE calculations exclude or quarantine labelled anomalous records according to the generator's documented calculation rules.
- The generator represents production orders with final statuses; it does not provide a complete event-by-event history of transitions from planned to running to completed or cancelled.
- State events and production-count corrections provide partial event-history traceability, but not a complete append-only audit system for every entity.
- SQLite integrity and foreign-key checks have passed on the updated full-scale test database. Additional domain-rule validation would strengthen the project.
- The system is intended for synthetic manufacturing analytics, evaluation, and demonstration, not direct deployment to production manufacturing systems.

## Repository

https://github.com/nikithaakula1998-max/YottaFlex_OEE_Project
