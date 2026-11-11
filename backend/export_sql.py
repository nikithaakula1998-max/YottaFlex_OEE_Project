
import argparse
import sqlite3
from pathlib import Path


def export_sql(database_path: Path, output_path: Path) -> None:
    if not database_path.is_file():
        raise FileNotFoundError(
            f"SQLite database not found: {database_path}"
        )

    if output_path.exists():
        raise FileExistsError(
            f"SQL export already exists: {output_path}. "
            "Choose a different output path."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        database_path.resolve().as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        if integrity != "ok":
            raise ValueError(
                f"Database integrity check failed: {integrity}"
            )

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise ValueError(
                f"Found {len(violations)} foreign-key violations"
            )

        statement_count = 0

        try:
            with output_path.open(
                "x", encoding="utf-8", newline="\n"
            ) as output:
                for statement in connection.iterdump():
                    output.write(statement)
                    output.write("\n")
                    statement_count += 1

        except Exception:
            output_path.unlink(missing_ok=True)
            raise

    finally:
        connection.close()

    size_mb = output_path.stat().st_size / (1024 * 1024)

    print("SQL export:", output_path.resolve())
    print("SQL statements:", statement_count)
    print("Size MB:", round(size_mb, 2))
    print("Integrity: ok")
    print("Foreign key violations: 0")
    print("RESULT: PASS")


def main():
    parser = argparse.ArgumentParser(
        description="Export a SQLite database as a portable SQL seed file."
    )

    parser.add_argument(
        "--db",
        required=True,
        help="Path to the existing SQLite database",
    )

    parser.add_argument(
        "--out",
        required=True,
        help="Path for the new SQL export",
    )

    args = parser.parse_args()

    export_sql(Path(args.db), Path(args.out))


if __name__ == "__main__":
    main()
