
import argparse
import csv
import sqlite3
from pathlib import Path

TABLES = [
    "plant",
    "line",
    "machine",
    "shift",
    "product",
    "machine_product",
    "production_order",
    "downtime_reason",
    "state_event",
    "production_count",
    "quality_inspection",
    "oee_aggregate",
]

BATCH_SIZE = 5000


def import_table(connection, folder, table):
    csv_path = folder / f"{table}.csv"

    with csv_path.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames

        if not columns:
            raise ValueError(f"No columns found in {csv_path}")

        sql_columns = {
            row[1]
            for row in connection.execute(
                f'PRAGMA table_info("{table}")'
            )
        }

        missing = set(columns) - sql_columns

        if missing:
            raise ValueError(
                f"{table}: missing SQL columns {sorted(missing)}"
            )

        column_names = ", ".join(
            f'"{column}"' for column in columns
        )
        placeholders = ", ".join("?" for _ in columns)

        statement = (
            f'INSERT INTO "{table}" ({column_names}) '
            f"VALUES ({placeholders})"
        )

        batch = []
        total = 0

        for row in reader:
            values = tuple(
                None if row[column] == "" else row[column]
                for column in columns
            )

            batch.append(values)

            if len(batch) >= BATCH_SIZE:
                connection.executemany(statement, batch)
                total += len(batch)
                batch.clear()

        if batch:
            connection.executemany(statement, batch)
            total += len(batch)

        print(f"{table}: {total} rows imported")

        return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--folder",
        default="outputs/full",
        help="Folder containing generated CSV files",
    )
    parser.add_argument(
        "--db",
        default="outputs/full/oee.sqlite",
        help="SQLite database output path",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    database_path = Path(args.db)

    if not folder.is_dir():
        raise FileNotFoundError(folder)

    if database_path.exists():
        raise FileExistsError(
            f"Database already exists: {database_path}. "
            "Choose another --db path."
        )

    database_path.parent.mkdir(
        parents=True, exist_ok=True
    )

    schema_path = Path(__file__).resolve().parent / "schema.sql"

    connection = sqlite3.connect(database_path)

    try:
        connection.executescript(
            schema_path.read_text(encoding="utf-8")
        )

        # Generated data intentionally contains anomalies.
        # Preserve every record without filtering or repairing it.
        # Foreign-key constraints are not enforced during import.
        connection.execute("PRAGMA foreign_keys=OFF")

        for table in TABLES:
            import_table(connection, folder, table)

        connection.commit()

        print("\nRESULT: PASS")
        print("Database:", database_path)
        print("Ground truth excluded: YES")

    except Exception:
        connection.rollback()
        connection.close()
        database_path.unlink(missing_ok=True)
        raise

    finally:
        try:
            connection.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
