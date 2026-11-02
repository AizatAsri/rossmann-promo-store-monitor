import duckdb
from pathlib import Path

con = duckdb.connect("rossmann.db")

# types hanya untuk fail yang ada lajur tu
files = {
    "sales": ("train.csv", ", types={'StateHoliday': 'VARCHAR'}"),
    "stores": ("store.csv", ""),
}

for name, (file, extra) in files.items():
    matches = list(Path("data").rglob(file))
    if not matches:
        print("TIADA fail:", file)
        continue
    path = matches[0].as_posix()
    con.execute(f"""
        CREATE OR REPLACE TABLE {name} AS
        SELECT * FROM read_csv('{path}', header=true, sample_size=-1{extra})
    """)
    count = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(name, count)

con.close()