import duckdb
import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", None)
con = duckdb.connect("rossmann.db", read_only=True)

df = con.execute("""
WITH g AS (
  SELECT Store, DayOfWeek,
    AVG(Sales) FILTER (WHERE Promo = 1) AS p_sales,
    AVG(Sales) FILTER (WHERE Promo = 0) AS n_sales,
    AVG(Customers) FILTER (WHERE Promo = 1) AS p_cust,
    AVG(Customers) FILTER (WHERE Promo = 0) AS n_cust
  FROM sales WHERE Open = 1 AND Sales > 0
  GROUP BY Store, DayOfWeek
), s AS (
  SELECT Store,
         AVG(p_sales / n_sales) - 1 AS sales_uplift,
         AVG(p_cust / n_cust) - 1 AS cust_uplift
  FROM g
  WHERE p_sales IS NOT NULL AND n_sales > 0 AND n_cust > 0
  GROUP BY Store
)
SELECT s.*, st.StoreType, st.Assortment
FROM s JOIN stores st USING (Store)
""").df()

rng = np.random.default_rng(42)
boot = [df.sales_uplift.sample(len(df), replace=True,
        random_state=int(rng.integers(1e9))).mean() for _ in range(2000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"Kedai: {len(df)} | Kenaikan jualan min: {100*df.sales_uplift.mean():.1f}% "
      f"(95% CI {100*lo:.1f} hingga {100*hi:.1f})")
print(f"Kenaikan pelanggan min: {100*df.cust_uplift.mean():.1f}%")
basket = (1 + df.sales_uplift.mean()) / (1 + df.cust_uplift.mean()) - 1
print(f"Anggaran kenaikan belanja per pelanggan: {100*basket:.1f}%")

for col in ["StoreType", "Assortment"]:
    out = (df.groupby(col)
             .agg(kedai=("Store", "count"),
                  sales_uplift_pct=("sales_uplift", lambda x: round(100 * x.mean(), 1)),
                  cust_uplift_pct=("cust_uplift", lambda x: round(100 * x.mean(), 1)))
             .reset_index())
    print("\n", out.to_string(index=False))