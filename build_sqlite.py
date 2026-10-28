"""Build a constrained SQLite read model from the canonical fictional CSV input pack."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SCHEMA_PATH = ROOT / "database" / "schema.sql"
DATABASE_PATH = ROOT / "gulftrade.db"

TABLES = (
    "sku_master",
    "inventory",
    "safety_stock",
    "sales_history",
    "stock_age",
    "inbound_orders",
    "transfer_costs",
    "holding_costs",
    "events",
    "answer_key",
)

INTEGER_COLUMNS = {
    "semiconductor_dependent",
    "available",
    "reserved",
    "safety_stock",
    "units",
    "age_days",
    "quantity",
    "supplier_lead_days",
    "lead_days",
    "was_stockout",
    "delay_days",
}
REAL_COLUMNS = {
    "unit_margin_aed",
    "unit_value_aed",
    "variable_cost_aed",
    "fixed_cost_aed",
    "per_unit_day_aed",
    "ageing_penalty_aed",
    "demand_multiplier",
}
BOOLEAN_COLUMNS = {"semiconductor_dependent", "was_stockout"}
COLUMN_MAPS = {
    "sales_history": {"date": "sale_date", "stockout": "was_stockout"},
}
NULLABLE_COLUMNS = {("answer_key", column) for column in ("sku", "location", "start_date", "end_date", "expected")}


def parse_value(table: str, column: str, value: str):
    if value == "" and (table, column) in NULLABLE_COLUMNS:
        return None
    if value == "":
        return ""
    if column in BOOLEAN_COLUMNS:
        if value not in {"True", "False"}:
            raise ValueError(f"{column} must be True or False, received {value!r}")
        return int(value == "True")
    if column in INTEGER_COLUMNS:
        return int(value)
    if column in REAL_COLUMNS:
        return float(value)
    return value


def load_csv(table: str) -> tuple[list[str], list[tuple]]:
    path = DATA_DIR / f"{table}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing canonical source file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"{path.name} has no header")
        source_columns = reader.fieldnames
        rename = COLUMN_MAPS.get(table, {})
        columns = [rename.get(column, column) for column in source_columns]
        rows = [
            tuple(parse_value(table, column, record[source_column]) for source_column, column in zip(source_columns, columns))
            for record in reader
        ]
    return columns, rows


def insert_table(connection: sqlite3.Connection, table: str) -> int:
    columns, rows = load_csv(table)
    placeholders = ", ".join("?" for _ in columns)
    column_list = ", ".join(columns)
    connection.executemany(f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})", rows)
    return len(rows)


def build(database_path: Path = DATABASE_PATH) -> dict[str, int]:
    if database_path.exists():
        database_path.unlink()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        locations = load_csv("inventory")[1]
        location_index = load_csv("inventory")[0].index("location")
        connection.executemany(
            "INSERT INTO locations (location) VALUES (?)",
            [(location,) for location in sorted({row[location_index] for row in locations})],
        )
        counts = {table: insert_table(connection, table) for table in TABLES}
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ValueError(f"Foreign-key validation failed: {violations}")
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"SQLite integrity check failed: {integrity}")
        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    counts = build()
    print(f"Created {DATABASE_PATH.name}: " + ", ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
