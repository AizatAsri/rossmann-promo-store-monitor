import duckdb
import pandas as pd

con = duckdb.connect("rossmann.db", read_only=True)

w = con.execute("""
WITH d AS (
  SELECT Date, DATE_TRUNC('week', Date) AS wk,
         CASE WHEN AVG(Promo) > 0.5 THEN 1 ELSE 0 END AS promo
  FROM sales WHERE DayOfWeek <= 5
  GROUP BY Date
)
SELECT wk, SUM(promo) AS promo_days, COUNT(*) AS days
FROM d GROUP BY wk ORDER BY wk
""").df()

w["label"] = w.promo_days.apply(lambda x: "P" if x >= 3 else ("N" if x == 0 else "M"))
print("Minggu ikut label (P=promo, N=tiada, M=campur):")
print(w.label.value_counts())

# ringkaskan kepada larian berturut-turut
runs, cur, n = [], w.label.iloc[0], 0
for lab in w.label:
    if lab == cur:
        n += 1
    else:
        runs.append(f"{cur}{n}")
        cur, n = lab, 1
runs.append(f"{cur}{n}")
print("\nCorak (huruf+bilangan minggu berturut):")
print(" ".join(runs[:40]))
print("\nTarikh pertama dan terakhir:", w.wk.min().date(), "hingga", w.wk.max().date())