"""くらしの指標ダッシュボード（Streamlit）
data/stats.duckdb の mart_indicators_monthly を読むだけ。DB がなければ results/mart_indicators_monthly.csv を読む
起動：streamlit run app/app.py
"""
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]


@st.cache_data
def load():
    db = ROOT / "data" / "stats.duckdb"
    if db.exists():
        import duckdb
        with duckdb.connect(str(db), read_only=True) as con:
            df = con.execute("select * from mart_indicators_monthly order by month").fetchdf()
    else:
        df = pd.read_csv(ROOT / "results" / "mart_indicators_monthly.csv", parse_dates=["month"])
    df["month"] = pd.to_datetime(df["month"])
    return df


df = load()
st.set_page_config(page_title="くらしの指標", layout="wide")
st.title("くらしの指標（物価・雇用・賃金）")
start = st.slider("表示する期間（開始年）", 1990, int(df.month.dt.year.max()), 2015)
d = df[df.month.dt.year >= start].set_index("month")

last = lambda c: d[c].dropna().index.max()
c1, c2, c3, c4 = st.columns(4)
c1.metric(f"物価（総合）前年比 {last('cpi_all_yoy'):%Y年%m月}", f"{d['cpi_all_yoy'].dropna().iloc[-1]:.1f}%",
          f"{d['cpi_all_yoy'].dropna().iloc[-1]-d['cpi_all_yoy'].dropna().iloc[-2]:+.1f}pt")
c2.metric(f"完全失業率 {last('unemp_rate_sa'):%Y年%m月}", f"{d['unemp_rate_sa'].dropna().iloc[-1]:.1f}%",
          f"{d['unemp_rate_sa'].dropna().iloc[-1]-d['unemp_rate_sa'].dropna().iloc[-2]:+.1f}pt", delta_color="inverse")
c3.metric(f"有効求人倍率 {last('jobs_ratio_sa'):%Y年%m月}", f"{d['jobs_ratio_sa'].dropna().iloc[-1]:.2f}倍",
          f"{d['jobs_ratio_sa'].dropna().iloc[-1]-d['jobs_ratio_sa'].dropna().iloc[-2]:+.2f}")
c4.metric(f"実質賃金 前年比 {last('real_wage_total_yoy'):%Y年%m月}", f"{d['real_wage_total_yoy'].dropna().iloc[-1]:.1f}%",
          f"{d['real_wage_total_yoy'].dropna().iloc[-1]-d['real_wage_total_yoy'].dropna().iloc[-2]:+.1f}pt")

st.subheader("物価の前年同月比（%）")
st.line_chart(d[["cpi_all_yoy", "cpi_core_yoy", "cpi_core_core_yoy"]].rename(columns={
    "cpi_all_yoy": "総合", "cpi_core_yoy": "生鮮食品を除く総合", "cpi_core_core_yoy": "生鮮食品及びエネルギーを除く総合"}))
a, b = st.columns(2)
with a:
    st.subheader("賃金の前年同月比（%）")
    st.line_chart(d[["wage_total_yoy", "real_wage_total_yoy"]].rename(columns={"wage_total_yoy": "名目", "real_wage_total_yoy": "実質"}))
with b:
    st.subheader("完全失業率（%）と有効求人倍率（倍）")
    st.line_chart(d[["unemp_rate_sa", "jobs_ratio_sa"]].rename(columns={"unemp_rate_sa": "完全失業率", "jobs_ratio_sa": "有効求人倍率"}))
st.caption("出典：総務省統計局「消費者物価指数」「労働力調査」、厚生労働省「一般職業紹介状況」「毎月勤労統計調査」（e-Stat）を加工して作成。")
