"""Run the data tests in sql/tests/ on the warehouse built by run_sql.py and print OK / KO for each.
A test is a query returning the failing rows: zero rows = OK. Results are also written to data/marts/test_results.csv.
    python src/run_tests.py
"""
import csv
import re
import sys

from run_sql import ROOT, OUT, connect


def tests():
    for f in sorted((ROOT / "sql" / "tests").glob("*.sql")):
        for block in re.split(r"(?m)^-- test: ", f.read_text(encoding="utf-8"))[1:]:
            name, _, sql = block.partition("\n")
            yield name.strip(), sql.strip().rstrip(";")


def main():
    con = connect()
    rows, ko = [], 0
    for name, sql in tests():
        try:
            n = len(con.execute(sql).fetchall())
            status = "OK" if n == 0 else "KO"
        except Exception as e:          # a broken test is a failed test
            n, status = -1, f"KO (error: {e.__class__.__name__})"
        ko += status != "OK"
        rows.append({"test": name, "status": status, "failing_rows": n})
        print(f"{status:<3} {name}" + (f"  ({n} failing rows)" if n > 0 else ""))
    with open(OUT / "test_results.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["test", "status", "failing_rows"])
        w.writeheader()
        w.writerows(rows)
    con.execute(f"create or replace table test_results as select * from read_csv_auto('{(OUT / 'test_results.csv').as_posix()}', header = true)")
    print(f"\n{len(rows) - ko}/{len(rows)} tests OK")
    con.close()
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
