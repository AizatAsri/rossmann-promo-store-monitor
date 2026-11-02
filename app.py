from datetime import timedelta

import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Store Monitor", layout="wide")
st.title("Store Monitor: kedai yang ketinggalan")
st.caption("Jualan 4 minggu terakhir dibandingkan dengan jangkaan kedai itu sendiri "
           "(hari dalam minggu dan status promo yang sama), selepas tolak perubahan "
           "umum seluruh rantaian.")


@st.cache_data
def date_range():
    con = duckdb.connect("rossmann.db", read_only=True)
    lo, hi = con.execute("SELECT MIN(Date), MAX(Date) FROM sales").fetchone()
    con.close()
    return lo, hi


@st.cache_data
def load(cutoff: str) -> pd.DataFrame:
    con = duckdb.connect("rossmann.db", read_only=True)
    q = f"""
    WITH ref AS (
      SELECT Store, DayOfWeek, Promo, AVG(Sales) AS exp_sales
      FROM sales
      WHERE Open = 1 AND Sales > 0
        AND Date >= DATE '{cutoff}' - INTERVAL 111 DAY
        AND Date <  DATE '{cutoff}' - INTERVAL 27 DAY
      GROUP BY Store, DayOfWeek, Promo
      HAVING COUNT(*) >= 3
    ), rec AS (
      SELECT Store, DayOfWeek, Promo, Sales
      FROM sales
      WHERE Open = 1 AND Sales > 0
        AND Date >  DATE '{cutoff}' - INTERVAL 28 DAY
        AND Date <= DATE '{cutoff}'
    )
    SELECT Store, COUNT(*) AS open_days,
           SUM(rec.Sales) AS actual, SUM(ref.exp_sales) AS expected
    FROM rec JOIN ref USING (Store, DayOfWeek, Promo)
    GROUP BY Store
    HAVING COUNT(*) >= 15
    """
    df = con.execute(q).df()
    stores = con.execute("SELECT Store, StoreType, Assortment FROM stores").df()
    con.close()
    return df.merge(stores, on="Store", how="left")


@st.cache_data
def weekly(store: int, cutoff: str) -> pd.DataFrame:
    con = duckdb.connect("rossmann.db", read_only=True)
    w = con.execute(f"""
        SELECT DATE_TRUNC('week', Date) AS week, ROUND(AVG(Sales)) AS avg_daily_sales
        FROM sales
        WHERE Store = {int(store)} AND Open = 1 AND Sales > 0
          AND Date >  DATE '{cutoff}' - INTERVAL 182 DAY
          AND Date <= DATE '{cutoff}'
        GROUP BY 1 ORDER BY 1
    """).df()
    con.close()
    return w


lo, hi = date_range()
st.sidebar.header("Tetapan")
cutoff = st.sidebar.date_input("Tarikh semakan (hari terakhir)", value=hi,
                               min_value=lo + timedelta(days=112), max_value=hi)
threshold = st.sidebar.slider("Flag jika ketinggalan sekurang-kurangnya (%)", 5, 40, 15)

df = load(str(cutoff))
df["ratio"] = df.actual / df.expected
chain = df.ratio.median()
df["vs_own_pct"] = ((df.ratio - 1) * 100).round(1)
df["vs_peers_pct"] = ((df.ratio / chain - 1) * 100).round(1)
df["shortfall"] = (df.expected * chain - df.actual).round(0)

flagged = df[df.vs_peers_pct <= -threshold].sort_values("shortfall", ascending=False)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Kedai dianalisis", len(df))
c2.metric("Kedai flagged", len(flagged))
c3.metric("Perubahan median rantaian", f"{(chain - 1) * 100:.1f}%")
c4.metric("Jumlah kekurangan jualan", f"{flagged.shortfall.sum():,.0f}")

st.subheader("Senarai kedai (susun ikut kekurangan jualan)")
cols = ["Store", "StoreType", "Assortment", "open_days",
        "vs_own_pct", "vs_peers_pct", "shortfall"]
st.dataframe(flagged[cols], hide_index=True)
st.download_button("Muat turun CSV", flagged[cols].to_csv(index=False),
                   file_name="stores_falling_behind.csv", mime="text/csv")

if len(flagged):
    st.subheader("Trend mingguan kedai terpilih (26 minggu)")
    pick = st.selectbox("Kedai", flagged.Store.tolist())
    w = weekly(pick, str(cutoff))
    st.line_chart(w.set_index("week")["avg_daily_sales"])

st.caption("vs_own_pct = berbanding jangkaan kedai sendiri. vs_peers_pct = berbanding "
           "perubahan median semua kedai. shortfall = jualan yang hilang berbanding "
           "jangkaan selepas laraskan perubahan rantaian.")