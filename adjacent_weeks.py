import itertools
from collections import Counter

import duckdb
import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
con = duckdb.connect("rossmann.db", read_only=True)

w = con.execute("""
WITH d AS (
  SELECT Date, DATE_TRUNC('week', Date) AS wk,
         CASE WHEN AVG(Promo) > 0.5 THEN 1 ELSE 0 END AS promo
  FROM sales WHERE DayOfWeek <= 5
  GROUP BY Date
), wp AS (
  SELECT wk, SUM(promo) AS promo_days FROM d GROUP BY wk
), ws AS (
  SELECT DATE_TRUNC('week', Date) AS wk, AVG(Sales) AS avg_sales
  FROM sales WHERE Open = 1 AND Sales > 0 AND DayOfWeek <= 5
  GROUP BY wk
)
SELECT wp.wk, wp.promo_days, ws.avg_sales
FROM wp JOIN ws USING (wk) ORDER BY wp.wk
""").df()
w["wk"] = pd.to_datetime(w.wk)
w["promo"] = (w.promo_days >= 3).astype(int)

# 1) corak penuh
runs = [(k, len(list(g))) for k, g in itertools.groupby(w.promo)]
print("Jenis larian:", dict(Counter(f"{'P' if k else 'N'}{n}" for k, n in runs)))

# 2) bila minggu N datang selepas minggu N
w["gap_prev"] = (w.wk - w.wk.shift(1)).dt.days
w["gap_next"] = (w.wk.shift(-1) - w.wk).dt.days
w["prev_promo"] = w.promo.shift(1)
w["next_promo"] = w.promo.shift(-1)
nn = w[(w.promo == 0) & (w.prev_promo == 0) & (w.gap_prev == 7)]
print("\nMinggu N selepas minggu N:", [d.date().isoformat() for d in nn.wk])

# 3) reka bentuk minggu bersebelahan
w["prev_sales"] = w.avg_sales.shift(1)
w["next_sales"] = w.avg_sales.shift(-1)
ok = ((w.promo == 1) & (w.prev_promo == 0) & (w.next_promo == 0)
      & (w.gap_prev == 7) & (w.gap_next == 7))
e = w[ok].copy()
e["uplift"] = e.avg_sales / ((e.prev_sales + e.next_sales) / 2) - 1

rng = np.random.default_rng(42)
boot = [e.uplift.sample(len(e), replace=True,
        random_state=int(rng.integers(1e9))).mean() for _ in range(5000)]
lo, hi = np.percentile(boot, [2.5, 97.5])
print(f"\nMinggu promo yang sah: {len(e)}")
print(f"Kenaikan min: {100*e.uplift.mean():.1f}% (95% CI {100*lo:.1f} hingga {100*hi:.1f})")
print(f"Median: {100*e.uplift.median():.1f}% | min {100*e.uplift.min():.1f}% | maks {100*e.uplift.max():.1f}%")

e["tahun"] = e.wk.dt.year
print("\nIkut tahun:")
print(e.groupby("tahun").uplift.agg(minggu="count",
      min_pct=lambda x: round(100 * x.mean(), 1)).reset_index().to_string(index=False))