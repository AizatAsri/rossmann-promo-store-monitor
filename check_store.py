import duckdb
import pandas as pd

con = duckdb.connect("rossmann.db", read_only=True)
SID, CUT = 722, pd.Timestamp("2015-07-31")

df = con.execute(f"""
    SELECT Date, DayOfWeek, Promo, Sales FROM sales
    WHERE Store = {SID} AND Open = 1 AND Sales > 0
""").df()
df["Date"] = pd.to_datetime(df.Date)

ref = df[(df.Date >= CUT - pd.Timedelta(days=111)) & (df.Date < CUT - pd.Timedelta(days=27))]
rec = df[(df.Date > CUT - pd.Timedelta(days=28)) & (df.Date <= CUT)]

exp = ref.groupby(["DayOfWeek", "Promo"]).Sales.agg(["mean", "count"]).reset_index()
exp = exp[exp["count"] >= 3]
m = rec.merge(exp, on=["DayOfWeek", "Promo"])

print("Hari dipadan:", len(m), "daripada", len(rec))
print("Sebenar:", m.Sales.sum(), "| Jangkaan:", round(m["mean"].sum()))
print("vs_own_pct:", round(100 * (m.Sales.sum() / m["mean"].sum() - 1), 1))