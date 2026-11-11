
# YottaFlex OEE Manufacturing Analytics

## Project Overview

This project generates and analyzes synthetic manufacturing data to calculate Overall Equipment Effectiveness (OEE).

The system includes:

- A deterministic manufacturing data generator
- Anomaly detection and validation
- OEE calculation and independent verification
- Machine-shift time reconciliation
- A FastAPI backend
- A Streamlit dashboard
- SQLite database support
- Dataset integrity verification using SHA-256 checksums

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
| Production orders | 8,100 |
| State events | 100,000 |
| Production counts | 250,000 |
| Quality inspections | 250,000 |
| OEE aggregates | 8,100 |
| Ground-truth anomalies | 5 |

The dataset is fully synthetic and does not contain real manufacturing or personal data.

## OEE Calculation

Overall Equipment Effectiveness is calculated using three factors.

**Availability**

Availability = Run Time / Planned Production Time

**Performance**

Performance = (Total Units * Ideal Cycle Time) / Run Time

**Quality**

Quality = Good Units / Total Units

**Overall OEE**

OEE = Availability * Performance * Quality

## Anomaly Detection

The validator independently detects five anomaly types:

1. Overlapping machine states
2. Negative production counts without corrections
3. Scrap quantities exceeding production totals
4. Incorrect ideal cycle times
5. Downtime overlapping planned breaks

The dataset includes five labelled ground-truth anomalies for verification.

## Validation Results

The following checks passed on the generated full-scale dataset:

| Validation | Result |
|---|---|
| Full-scale dataset generation | PASS |
| Structural validation | PASS |
| Anomaly verification | 5/5 MATCH |
| Independent OEE verification | 8,100 checked, 0 mismatches |
| Time reconciliation | PASS |
| CSV SHA-256 integrity | 13/13 matching |
| SQLite database integrity | PASS |
| SQLite row-count verification | 12/12 tables matching |

### Time Reconciliation Results

- Expected machine-shifts: 8,100
- Clean reconciled machine-shifts: 8,097
- Flagged machine-shifts: 3
- Unexpected problematic shifts: 0

The three flagged machine-shifts contain intentionally injected anomalies.

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
            starter/
            full/
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

Generated datasets and the SQLite database are stored locally under `backend/outputs/`.

They are excluded from GitHub because of their size.

## How to Run

### 1. Clone the Repository

Open Windows PowerShell or the VS Code terminal.

```powershell
git clone https://github.com/nikithaakula1998-max/YottaFlex_OEE_Project.git
```

Enter the project directory:

```powershell
cd YottaFlex_OEE_Project
```

### 2. Create a Virtual Environment

```powershell
py -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment again.

### 3. Install Dependencies

From the project root, run:

```powershell
python -m pip install -r backend\requirements.txt
```

```powershell
python -m pip install -r frontend\requirements.txt
```

### 4. Generate the Full Dataset

Enter the backend folder:

```powershell
cd backend
```

Run the generator:

```powershell
python -m src.main --profile full --out outputs/full
```

The generator creates the synthetic manufacturing CSV files, ground-truth labels, manifest, and validation summary.

### 5. Validate Anomalies

From the backend folder, run:

```powershell
python -c "from pathlib import Path; import src.validator as v; v.DATA_FOLDER = Path('outputs/full'); assert v.validate()"
```

Expected result:

```text
Ground-truth matches: 5/5
RESULT: PASS
```

### 6. Verify OEE Calculations

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

### 8. Run Unit Tests

```powershell
python -m unittest discover -s tests -v
```

Expected result:

```text
Ran 1 test
OK
```

### 9. Create the SQLite Database

After generating the full dataset, run:

```powershell
python load_sqlite.py --folder outputs/full --db outputs/full/oee.sqlite
```

The loader imports all 12 operational CSV datasets into SQLite.

The `ground_truth.csv` file is intentionally excluded to keep the anomaly answers separate from operational data.

The SQLite database is generated locally and is not committed to GitHub.

**Note:** The loader does not overwrite an existing database. If you need to rebuild it, first back up or remove the old `outputs/full/oee.sqlite` file.

### 10. Verify the SQLite Database

From the backend folder, run:

```powershell
python -c "import sqlite3; c=sqlite3.connect('outputs/full/oee.sqlite'); print('OEE records:',c.execute('SELECT COUNT(*) FROM oee_aggregate').fetchone()[0]); print('Integrity:',c.execute('PRAGMA integrity_check').fetchone()[0]); c.close()"
```

Expected output:

```text
OEE records: 8100
Integrity: ok
```

The database contains the operational manufacturing records, including the intentionally anomalous records.

Ground-truth labels are kept separately.

### 11. Start the FastAPI Backend

From the backend folder, run:

```powershell
python -m uvicorn src.api:app --reload
```

Open the API documentation:

http://127.0.0.1:8000/docs

### 12. Start the Streamlit Dashboard

Open another terminal in the main project folder.

Activate the virtual environment if needed.

Run:

```powershell
python -m streamlit run frontend/app.py
```

Open the dashboard:

http://localhost:8501

Keep the FastAPI server running while using the dashboard.

## Reproducibility

The generator uses the fixed random seed:

```text
20261022
```

The full dataset covers 90 days of synthetic manufacturing operations across 30 machines.

Running the full generator twice with the same configuration previously produced identical SHA-256 checksums for all 13 CSV files.

The generated `manifest.json` includes:

- Random seed
- Generation parameters
- Dataset row counts
- SHA-256 checksums
- Synthetic data provenance

The manifest checksums were independently compared with the generated CSV files, with zero mismatches.

## API Summary

The full-scale API returned:

- Machines: 30
- Machine-shifts: 8,100
- Labelled anomalies: 5
- Average OEE: 81.46%

## Data Dictionary

See `DATA_DICTIONARY.md` for information about the manufacturing datasets and their fields.

## AI Assistance Disclosure

AI assistance was used during project development for implementation guidance, debugging, testing, and documentation.

See `prompts/prompt_history.md` for the currently documented AI-assistance information.

The existing file is a summary of AI use; it should not be treated as a complete transcript of all original prompts.

## Notes and Limitations

- All manufacturing data is synthetic.
- The generated CSV and SQLite files are excluded from version control.
- The dataset contains intentionally injected anomalies.
- Ground-truth labels are stored separately from the operational SQLite database.
- OEE aggregates are computed from source records after excluding labelled anomalous records.
- SQLite foreign-key enforcement is disabled during bulk import to preserve generated records. Database integrity checking and row-count verification have passed, but those checks do not establish full referential integrity.
- The project is intended for synthetic manufacturing analytics and validation demonstrations.

## Repository

GitHub:

https://github.com/nikithaakula1998-max/YottaFlex_OEE_Project
