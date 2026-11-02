import duckdb
import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
con = duckdb.connect("rossmann.db", read_only=True)


def ratios(rs, re, ws, we):
    q = f"""
    WITH ref AS (
      SELECT Store, DayOfWeek, Promo, AVG(Sales) AS exp_sales
      FROM sales WHERE Open = 1 AND Sales > 0
        AND Date >= DATE '{rs}' AND Date < DATE '{re}'
      GROUP BY Store, DayOfWeek, Promo HAVING COUNT(*) >= 3
    ), rec AS (
      SELECT Store, DayOfWeek, Promo, Sales FROM sales
      WHERE Open = 1 AND Sales > 0
        AND Date >= DATE '{ws}' AND Date <= DATE '{we}'
    )
    SELECT Store, SUM(rec.Sales) / SUM(ref.exp_sales) AS ratio
    FROM rec JOIN ref USING (Store, DayOfWeek, Promo)
    GROUP BY Store HAVING COUNT(*) >= 15
    """
    return con.execute(q).df()


THR = 0.15
rows = []
for c in pd.date_range("2013-06-02", "2015-07-03", freq="28D"):
    d = lambda k: (c + pd.Timedelta(days=k)).date().isoformat()
    now = ratios(d(-111), d(-27), d(-27), d(0))
    fut = ratios(d(-111), d(-27), d(1), d(28))
    now["peer_now"] = now.ratio / now.ratio.median() - 1
    fut["peer_fut"] = fut.ratio / fut.ratio.median() - 1
    m = now[["Store", "peer_now"]].merge(fut[["Store", "peer_fut"]], on="Store")
    m["flagged"] = m.peer_now <= -THR
    m["still"] = m.peer_fut <= -THR
    m["cutoff"] = c.date()
    rows.append(m)

allm = pd.concat(rows)
per = (allm.groupby(["cutoff", "flagged"])
       .agg(n=("Store", "count"), still=("still", "mean")).reset_index())
pv = per.pivot(index="cutoff", columns="flagged", values=["n", "still"]).dropna()
print((pv * [1, 1, 100, 100]).round(1).to_string())

g = allm.groupby("flagged").agg(
    store_periods=("Store", "count"),
    now_pct=("peer_now", lambda x: round(100 * x.mean(), 1)),
    next4w_pct=("peer_fut", lambda x: round(100 * x.mean(), 1)),
    still_behind_pct=("still", lambda x: round(100 * x.mean(), 1)))
print("\nGabungan semua tarikh:\n", g)

rng = np.random.default_rng(42)
cuts = allm.cutoff.unique()
diffs = []
for _ in range(2000):
    s = rng.choice(cuts, len(cuts))
    b = pd.concat([allm[allm.cutoff == x] for x in s])
    f, u = b[b.flagged], b[~b.flagged]
    if len(f) and len(u):
        diffs.append(100 * (f.still.mean() - u.still.mean()))
lo, hi = np.percentile(diffs, [2.5, 97.5])
print(f"\nBeza % terus ketinggalan (flagged - bukan flagged): "
      f"{np.mean(diffs):.1f} mata peratus (95% CI {lo:.1f} hingga {hi:.1f}, bootstrap atas tarikh)")