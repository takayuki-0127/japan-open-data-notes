"""574 部署の統廃合があったとき、過去の部署別の数字を今の組織に組み替えると、推移はどう変わるのか（架空の会社、seed 574）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

rng = np.random.default_rng(574)
SRC = "架空の会社の部署マスタと月次実績（作成者が乱数で作成、seed 574）"
months = pd.date_range("2022-04-01", "2026-03-01", freq="MS")
# 見えない「チーム」単位の売上（百万円）。チームごとに伸び方が違う
TEAM = {"T1": (40, .02), "T2": (35, .00), "T3": (30, .05), "T4": (20, -.03), "T5": (18, .01), "T6": (6, .35),
        "T7": (25, .12), "T8": (30, -.02), "T9": (22, .03), "T10": (10, .06)}
season = 1 + .08 * np.sin((months.month - 4) / 12 * 2 * np.pi) + np.where(months.month == 3, .15, 0)
tm = []
for t, (base, g) in TEAM.items():
    yrs = (np.arange(len(months))) / 12
    v = base * (1 + g) ** yrs * season * rng.normal(1, .04, len(months))
    tm += [(t, m, round(x, 1)) for m, x in zip(months, v)]
team = pd.DataFrame(tm, columns=["team", "month", "sales"])

def dept_of(t, m):
    if m < pd.Timestamp("2024-04-01"):
        return {"T1": "営業1課", "T2": "営業1課", "T3": "営業2課", "T4": "営業2課", "T5": "企画部", "T6": "企画部", "T7": "開発事業部", "T8": "開発事業部"}.get(t, "サービス部")
    if m < pd.Timestamp("2025-04-01"):
        return {"T1": "営業部", "T2": "営業部", "T3": "営業部", "T4": "営業部", "T5": "企画部", "T6": "企画部", "T7": "開発事業部", "T8": "開発事業部"}.get(t, "サービス部")
    return {"T1": "営業部", "T2": "営業部", "T3": "営業部", "T4": "営業部", "T5": "企画部", "T6": "デジタル企画部", "T8": "開発事業部"}.get(t, "サービス部")
NOW = {"T1": "営業部", "T2": "営業部", "T3": "営業部", "T4": "営業部", "T5": "企画部", "T6": "デジタル企画部", "T7": "サービス部", "T8": "開発事業部", "T9": "サービス部", "T10": "サービス部"}
team["dept_then"] = [dept_of(t, m) for t, m in zip(team.team, team.month)]
team["dept_now"] = team.team.map(NOW)
# 会社に残っているのは「当時の部署」単位の月次実績だけ
rec = team.groupby(["month", "dept_then"], as_index=False).sales.sum().rename(columns={"dept_then": "dept"})
rec["sales"] = rec.sales.round(1)
rec.to_csv(DATA / "monthly_by_dept.csv", index=False, date_format="%Y-%m")
truth = team.groupby(["month", "dept_now"]).sales.sum().unstack()

# 新旧対応表：分割・移管は、変わった直後 k か月の構成比で過去を割り振る
def mapping(k):
    after = rec[(rec.month >= "2025-04-01") & (rec.month < pd.Timestamp("2025-04-01") + pd.DateOffset(months=k))].groupby("dept").sales.sum()
    r_dig = after["デジタル企画部"] / (after["デジタル企画部"] + after["企画部"])
    # 製品X（T7）の移管：移管後のサービス部の増加分を、開発事業部との合計で割る比率は分からないので、
    # 移管された事業の直後 k か月の実績（事業別の報告があったとする）と開発事業部の実績の比を使う
    t7 = team[(team.team == "T7") & (team.month >= "2025-04-01") & (team.month < pd.Timestamp("2025-04-01") + pd.DateOffset(months=k))].sales.sum()
    r_x = t7 / (t7 + after["開発事業部"])
    rows = [("営業1課", "営業部", 1.0), ("営業2課", "営業部", 1.0), ("営業部", "営業部", 1.0),
            ("企画部", "企画部", 1 - r_dig), ("企画部", "デジタル企画部", r_dig),
            ("開発事業部", "開発事業部", 1 - r_x), ("開発事業部", "サービス部", r_x), ("サービス部", "サービス部", 1.0)]
    return pd.DataFrame(rows, columns=["old_dept", "new_dept", "ratio"]), r_dig, r_x

def restate(mp):
    pre = rec[rec.month < "2025-04-01"].merge(mp, left_on="dept", right_on="old_dept")
    pre["sales"] = pre.sales * pre.ratio
    post = rec[rec.month >= "2025-04-01"].assign(new_dept=lambda d: d.dept)
    return pd.concat([pre[["month", "new_dept", "sales"]], post[["month", "new_dept", "sales"]]]).groupby(["month", "new_dept"]).sales.sum().unstack()

mp3, r_dig3, r_x3 = mapping(3); mp3.to_csv(DATA / "dept_mapping.csv", index=False)
re3 = restate(mp3)
asis = rec.pivot(index="month", columns="dept", values="sales")
FY = lambda df, y: df[(df.index >= f"{y}-04-01") & (df.index < f"{y+1}-04-01")].sum()
DEPTS = ["営業部", "企画部", "デジタル企画部", "開発事業部", "サービス部"]
def growth(df):
    a, b = FY(df, 2024), FY(df, 2025)
    return {d: (round(float(b[d] / a[d] - 1) * 100, 1) if d in a.index and a.get(d, 0) > 0 else None) for d in DEPTS}
G = pd.DataFrame({"そのまま（当時の部署名）": growth(asis), "対応表で組み替え（直後3か月の比率）": growth(re3), "正解（チーム単位で組み替え）": growth(truth)})
G.to_csv(RES / "growth_fy2025.csv")
# 比率をどの期間で決めるかで、デジタル企画部の過去がどれだけずれるか
true_share = (team[(team.team == "T6") & (team.month < "2025-04-01")].groupby(team.month.dt.year.where(team.month.dt.month >= 4, team.month.dt.year - 1)).sales.sum()
              / team[team.team.isin(["T5", "T6"]) & (team.month < "2025-04-01")].groupby(team.month.dt.year.where(team.month.dt.month >= 4, team.month.dt.year - 1)).sales.sum())
K = []
for k in [1, 3, 6, 12]:
    mp, rd, rx = mapping(k); re = restate(mp)
    K.append({"months_used": k, "ratio_digital": round(rd, 3), "ratio_productX": round(rx, 3),
              "digital_fy2024_restated": round(float(FY(re, 2024)["デジタル企画部"]), 1), "digital_growth": growth(re)["デジタル企画部"],
              "service_growth": growth(re)["サービス部"], "dev_growth": growth(re)["開発事業部"]})
KT = pd.DataFrame(K); KT.to_csv(RES / "ratio_window.csv", index=False)

# SQL（DuckDB、1スレッド）：対応表で組み替えた年度合計を Python と突き合わせる
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE monthly_by_dept AS SELECT strptime(month, '%Y-%m')::DATE AS month, dept, sales FROM read_csv_auto('{DATA/'monthly_by_dept.csv'}', types={{'month':'VARCHAR'}})")
con.execute(f"CREATE TABLE dept_mapping AS SELECT * FROM read_csv_auto('{DATA/'dept_mapping.csv'}')")
sq = con.execute((SQL / "02_restate_duckdb.sql").read_text()).df().set_index("new_dept")
fy24 = FY(re3, 2024)
chk = bool(all(abs(sq.loc[d, "fy2024"] - fy24[d]) < 0.05 for d in DEPTS))
sq.to_csv(RES / "sql_fy2024_restated.csv")

res = {"ratio_digital_3m": round(r_dig3, 3), "ratio_productX_3m": round(r_x3, 3),
       "true_digital_share_by_fy": {int(k): round(float(v), 3) for k, v in true_share.items()},
       "growth_fy2025": G.to_dict(), "ratio_window": KT.to_dict(orient="records"),
       "company_total_fy2025_growth": round(float(FY(asis, 2025).sum() / FY(asis, 2024).sum() - 1) * 100, 2), "sql_match": chk}
json.dump(res, open(RES / "a574_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=0)[:3000]); print(G); print(KT)

# 図1：サービス部と開発事業部の月次（そのまま vs 組み替え）
fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
for ax, d in zip(axs, ["サービス部", "開発事業部"]):
    ax.plot(asis.index, asis[d], color=ORANGE, lw=1.5, label="そのまま（当時の部署）")
    ax.plot(re3.index, re3[d], color=BLUE, lw=1.5, label="対応表で組み替え")
    ax.plot(truth.index, truth[d], color=INK, lw=1, ls=":", label="正解")
    ax.axvline(pd.Timestamp("2025-04-01"), color=GRAY, lw=.8); ax.set_title(d); ax.set_ylabel("月の売上（百万円）")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=4)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y年%-m月")); ax.tick_params(axis="x", labelsize=8, rotation=30)
axs[0].legend(frameon=False, fontsize=8)
fig.suptitle("製品Xの移管（2025年4月）で、そのままだと段差ができる", y=1.02)
save(fig, "a574_monthly.png", "出典：" + SRC + "。縦線は組織変更の月")
# 図2：2025年度の前年比（部署別）
fig, ax = plt.subplots(figsize=(8, 4))
x = np.arange(len(DEPTS)); cols = [ORANGE, BLUE, INK]
for k, (c, col) in enumerate(zip(G.columns, cols)):
    v = [G.loc[d, c] if pd.notna(G.loc[d, c]) else 0 for d in DEPTS]
    b = ax.bar(x + (k - 1) * .27, v, .27, color=col, label=c)
    for xx, d in zip(x + (k - 1) * .27, DEPTS):
        vv = G.loc[d, c]; ax.text(xx, (vv if pd.notna(vv) else 0) + (1 if (pd.isna(vv) or vv >= 0) else -4), "比べられない" if pd.isna(vv) else f"{vv:.0f}", ha="center", fontsize=7, rotation=0 if pd.notna(vv) else 90)
ax.axhline(0, color=INK, lw=.6); ax.set_xticks(x); ax.set_xticklabels(DEPTS); ax.set_ylabel("2025年度の前年比（%）"); ax.legend(frameon=False, fontsize=8)
ax.set_title("組み替えないと、伸び率がまるで違って見える")
save(fig, "a574_growth.png", "出典：" + SRC + "。対応表の分割比率は、変わった直後3か月の構成比")
# 図3：分割比率を決める期間と、デジタル企画部の伸び率
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(KT.months_used.astype(str), KT.digital_growth, color=BLUE, marker="o", label="対応表で組み替えた伸び率")
tv = G.loc["デジタル企画部", "正解（チーム単位で組み替え）"]; ax.axhline(tv, color=INK, ls=":", label=f"正解 {tv:.1f}%")
for xx, v in zip(KT.months_used.astype(str), KT.digital_growth): ax.text(xx, v + 1, f"{v:.1f}%", ha="center", fontsize=9, color=BLUE)
ax.set_xlabel("分割の比率を、変わった直後の何か月の構成比で決めるか"); ax.set_ylabel("デジタル企画部の2025年度の前年比（%）"); ax.legend(frameon=False)
ax.set_title("伸びている部署は、分割後の比率で過去を割ると伸び率が小さく出る")
save(fig, "a574_ratio_window.png", "出典：" + SRC)
