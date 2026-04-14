import argparse
import os
import re
from datetime import UTC, date, datetime, time
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from openpyxl import Workbook


def normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgresql+asyncpg://"):
        return raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw_url


def make_output_dir(explicit_path: str | None) -> Path:
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    return Path.cwd() / f"zrk_export_{timestamp}"


def sheet_name(name: str) -> str:
    safe = re.sub(r"[\[\]\*\?/\\:]", "_", name).strip()
    return safe[:31] or "sheet"


def safe_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe or "table"


def excel_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
    if isinstance(value, time):
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value
    if isinstance(value, (datetime, date, time, int, float, bool)) or value is None:
        return value
    return str(value)


def fetch_table_names(cursor) -> list[str]:
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    )
    return [row[0] for row in cursor.fetchall()]


def fetch_table_rows(cursor, table_name: str):
    cursor.execute(f'SELECT * FROM "{table_name}" ORDER BY 1')
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    return columns, rows


def build_meta_rows(db_url: str, tables: list[tuple[str, int]]) -> list[list[str | int]]:
    parsed = urlparse(db_url)
    return [
        ["exported_at_utc", datetime.now(UTC).isoformat(timespec="seconds")],
        ["database", (parsed.path or "/").lstrip("/")],
        ["host", parsed.hostname or ""],
        ["port", parsed.port or ""],
        ["tables_exported", len(tables)],
        ["total_rows", sum(row_count for _, row_count in tables)],
        [],
        ["table_name", "row_count"],
        *[[name, row_count] for name, row_count in tables],
    ]


def save_table_workbook(table_name: str, columns, rows, output_dir: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name(table_name)
    sheet.append(columns)
    for row in rows:
        sheet.append([excel_value(value) for value in row])
    sheet.freeze_panes = "A2"

    file_path = output_dir / f"{safe_filename(table_name)}.xlsx"
    workbook.save(file_path)
    return file_path


def save_summary_workbook(database_url: str, tables: list[tuple[str, int]], output_dir: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "summary"
    for row in build_meta_rows(database_url, tables):
        sheet.append(row)

    file_path = output_dir / "summary.xlsx"
    workbook.save(file_path)
    return file_path


def export_database(database_url: str, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created_files: list[Path] = []

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cursor:
            table_names = fetch_table_names(cursor)
            exported_tables: list[tuple[str, int]] = []

            for table_name in table_names:
                columns, rows = fetch_table_rows(cursor, table_name)
                exported_tables.append((table_name, len(rows)))
                created_files.append(save_table_workbook(table_name, columns, rows, output_dir))

    created_files.append(save_summary_workbook(database_url, exported_tables, output_dir))
    return created_files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export all public PostgreSQL tables into separate XLSX files."
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to output directory. Default: ./zrk_export_<timestamp>/",
    )
    args = parser.parse_args()

    database_url = normalize_database_url((os.getenv("DATABASE_URL") or "").strip())
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    output_dir = make_output_dir(args.output)
    export_database(database_url, output_dir)
    print(output_dir)


if __name__ == "__main__":
    main()
