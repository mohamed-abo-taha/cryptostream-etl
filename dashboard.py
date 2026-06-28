"""Interactive Streamlit dashboard over the SQLite warehouse.

    streamlit run dashboard.py

Reads the same SQL warehouse the pipeline fills and turns the analytics into an
interactive web page: KPIs, dominance, movers, and a filterable coin table.
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import streamlit as st

import config
from src.analytics import Analytics


@st.cache_data(ttl=30)
def load_df() -> pd.DataFrame:
    with sqlite3.connect(config.DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM coins ORDER BY market_cap DESC", conn)


st.set_page_config(page_title="CryptoStream", page_icon="📈", layout="wide")
st.title("CryptoStream — market dashboard")
st.caption("Live view of the SQLite warehouse filled by the ETL pipeline.")

try:
    df = load_df()
except Exception:
    st.error("No data yet. Run `python run_pipeline.py --source mock` first.")
    st.stop()

a = Analytics(config.DB_PATH)
summary = a.summary()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Coins tracked", summary["coins_tracked"])
c2.metric("Total market cap", f"${summary['total_market_cap']/1e12:.2f}T")
c3.metric("Avg price", f"${summary['avg_price_usd']:,.0f}")
c4.metric("24h volume", f"${summary['total_volume_24h']/1e9:.0f}B")

left, right = st.columns(2)
with left:
    st.subheader("Market dominance")
    dom = pd.DataFrame(a.dominance(limit=8)).set_index("symbol")["dominance_pct"]
    st.bar_chart(dom)
with right:
    st.subheader("Top 24h movers")
    movers = pd.DataFrame(a.top_gainers() + a.top_losers()).set_index("symbol")
    st.bar_chart(movers["change_24h_pct"])

st.subheader("Explore coins")
tier = st.selectbox("Market-cap tier", ["all", ">= $100B", "$10B-100B", "$1B-10B", "< $1B"])
view = df.copy()
if tier == ">= $100B":
    view = view[view.market_cap >= 1e11]
elif tier == "$10B-100B":
    view = view[(view.market_cap >= 1e10) & (view.market_cap < 1e11)]
elif tier == "$1B-10B":
    view = view[(view.market_cap >= 1e9) & (view.market_cap < 1e10)]
elif tier == "< $1B":
    view = view[view.market_cap < 1e9]

st.dataframe(
    view[["rank", "symbol", "name", "price_usd", "market_cap", "change_24h_pct"]],
    use_container_width=True, hide_index=True,
)
