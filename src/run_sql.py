"""Build the DuckDB warehouse: sql/staging (views) -> sql/intermediate -> sql/marts, then export every fct_* table
to data/marts/*.csv (the files read by the notebook, the workbook, the dashboard and the PDF).
    python src/run_sql.py
"""
from pathlib import Path
import os

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "finance.duckdb"
OUT = ROOT / "data" / "marts"


def connect():
    os.chdir(ROOT)                      # the SQL reads data/... with relative paths
    return duckdb.connect(str(DB))


def run_layer(con, layer):
    for f in sorted((ROOT / "sql" / layer).glob("*.sql")):
        con.execute(f.read_text(encoding="utf-8"))
        print(f"  {layer}/{f.name}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = connect()
    for layer in ("staging", "intermediate", "marts"):
        run_layer(con, layer)
    tables = [r[0] for r in con.execute("select table_name from information_schema.tables where table_name like 'fct_%' order by 1").fetchall()]
    for t in tables:
        con.execute(f"copy (select * from {t}) to '{(OUT / (t + '.csv')).as_posix()}' (header, delimiter ',')")
    print(f"exported {len(tables)} marts to data/marts/")
    con.close()


if __name__ == "__main__":
    main()
