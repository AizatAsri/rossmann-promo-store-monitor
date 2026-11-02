import duckdb
import pandas as pd

pd.set_option("display.width", 200)
con = duckdb.connect("rossmann.db", read_only=True)

d = con.execute("""
    SELECT Date, ROUND(100 * AVG(Promo)) AS pct_stores_on_promo
    FROM sales WHERE DayOfWeek BETWEEN 1 AND 5 AND Open = 1
    GROUP BY Date
""").df()

print(d.pct_stores_on_promo.describe())
print("\nTarikh dengan <10% kedai promo:", (d.pct_stores_on_promo < 10).sum())
print("Tarikh dengan >90% kedai promo:", (d.pct_stores_on_promo > 90).sum())
print("Tarikh dengan 10-90% kedai promo:",
      d.pct_stores_on_promo.between(10, 90).sum())