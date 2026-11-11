
# YottaFlex OEE Manufacturing Analytics

## Project Overview

This project generates and analyzes synthetic manufacturing
data to calculate Overall Equipment Effectiveness (OEE).

The system includes:
- A deterministic manufacturing data generator
- Anomaly detection and validation
- OEE calculation and independent verification
- Machine-shift time reconciliation
- A FastAPI backend
- A Streamlit dashboard

## Technologies Used

- Python
- FastAPI
- Streamlit
- CSV and JSON
- SHA-256 checksums
- Python unittest

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

The dataset is fully synthetic.

## OEE Calculation

Availability = Run Time / Planned Production Time

Performance = (Total Units * Ideal Cycle Time) / Run Time

Quality = Good Units / Total Units

OEE = Availability * Performance * Quality

## Anomaly Detection

The validator independently detects five anomaly types:

1. Overlapping machine states
2. Negative production counts without corrections
3. Scrap quantities exceeding production totals
4. Incorrect ideal cycle times
5. Downtime overlapping planned breaks

## Validation Results

Full-scale dataset generation: PASS

Structural validation: PASS

Anomaly verification: 5/5 MATCH

Independent OEE verification: 8,100 aggregates checked,
0 calculation mismatches

Full-scale reproducibility: PASS
13 CSV files with matching SHA-256 checksums

Time reconciliation:
- Expected machine-shifts: 8,100
- Clean reconciled machine-shifts: 8,097
- Flagged machine-shifts: 3
- Unexpected problematic shifts: 0

## Project Structure

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
        outputs/
            starter/
            full/
    frontend/
        app.py
    README.md

## How to Run

Open a terminal inside the backend folder.

### Generate the full dataset

python -m src.main --profile full --out outputs/full

### Validate anomalies

python -c "from pathlib import Path; import src.validator as v; v.DATA_FOLDER = Path('outputs/full'); assert v.validate()"

### Verify OEE calculations

python src/oee_checker.py --folder outputs/full

### Verify time reconciliation

python src/time_checker.py --folder outputs/full

### Run unit tests

python -m unittest discover -s tests -v

### Start FastAPI

python -m uvicorn src.api:app --reload

API documentation:
http://127.0.0.1:8000/docs

### Start Streamlit

Open another terminal in the main project folder.

python -m streamlit run frontend/app.py

Dashboard:
http://localhost:8501

## Reproducibility

The generator uses the fixed random seed 20261022.

Running the full generator twice with the same configuration
produced identical SHA-256 checksums for all 13 CSV files.

## API Summary

The full-scale API returned:

- Machines: 30
- Machine-shifts: 8,100
- Labelled anomalies: 5
- Average OEE: 81.46%

## Notes

The three flagged machine-shifts contain intentionally
injected anomalies.

The OEE aggregates are computed from source records after
excluding labelled anomalous records.

The project uses synthetic manufacturing data only.
