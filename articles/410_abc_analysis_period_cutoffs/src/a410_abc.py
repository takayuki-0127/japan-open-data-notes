"""410 売れ筋を A・B・C に分ける分析は、期間と区切りでどれだけ入れ替わるのか
架空の600商品・24か月の売上（季節の強い商品を含む）で、ABC 分析を期間と区切りを変えて行う。乱数の種は410。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 410
N = 600
CUT = {"70/90": (0.70, 0.90), "80/95": (0.80, 0.95)}


def make(seed, n=N, noise=0.30):
    """商品×月（2024年1月〜2025年12月）の売上。15%は季節の強い商品（夏型・冬型）"""
    r = np.random.default_rng(seed)
    base = r.lognormal(np.log(60_000), 1.5, n)                               # 1か月の売上の水準（円）
    kind = r.choice(["通年", "夏型", "冬型"], n, p=[0.85, 0.075, 0.075])
    m = np.arange(1, 13)
    prof = {"通年": np.ones(12), "夏型": 0.15 + 3.4 * np.exp(-0.5 * ((m - 7.5) / 1.1) ** 2), "冬型": 0.15 + 3.4 * np.exp(-0.5 * ((np.minimum(np.abs(m - 12.5), np.abs(m + 0.5))) / 1.1) ** 2)}
    for k in prof: prof[k] = prof[k] / prof[k].mean()                        # 年の合計は水準×12 にそろえる
    rows = []
    for y in (2024, 2025):
        gy = r.lognormal(0, 0.15, n)                                         # 年ごとの商品の勢い
        for mm in m:
            s = base * gy * np.array([prof[k][mm - 1] for k in kind]) * r.lognormal(0, noise, n)
            rows.append(pd.DataFrame({"商品ID": np.arange(1, n + 1), "種類": kind, "年": y, "月": mm, "売上": np.round(s).astype(int)}))
    return pd.concat(rows, ignore_index=True)


def abc(sales, cut):
    """売上の大きい順に並べ、累計の割合で A・B・C を付ける。累計が区切りに届く商品までを上のランクに入れる"""
    s = sales.sort_values(ascending=False, kind="mergesort")
    before = (s.cumsum() - s) / s.sum()                                      # その商品より上の商品の累計の割合
    a, b = cut
    return pd.Series(np.where(before < a, "A", np.where(before < b, "B", "C")), index=s.index).reindex(sales.index)


D = make(SEED); D.to_csv(DATA / "monthly_sales.csv", index=False)
kind = D.drop_duplicates("商品ID").set_index("商品ID")["種類"]
piv = D.pivot_table(index="商品ID", columns=["年", "月"], values="売上")
Y25 = piv[2025].sum(1); Y24 = piv[2024].sum(1)

# ---- SQL（DuckDB）：累計の割合でランクを付ける。pandas と一致するか ----
con = duckdb.connect(); con.register("sales", D)
q = """
WITH y AS (SELECT 商品ID, SUM(売上) AS 売上 FROM sales WHERE 年 = 2025 GROUP BY 商品ID),
c AS (
  SELECT 商品ID, 売上,
         SUM(売上) OVER (ORDER BY 売上 DESC, 商品ID ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) - 売上 AS 上の累計,
         SUM(売上) OVER () AS 全体
  FROM y
)
SELECT 商品ID, CASE WHEN 1.0 * 上の累計 / 全体 < 0.70 THEN 'A' WHEN 1.0 * 上の累計 / 全体 < 0.90 THEN 'B' ELSE 'C' END AS ランク
FROM c"""
sq = con.sql(q).df().set_index("商品ID")["ランク"].reindex(Y25.index)
R_year = {c: abc(Y25, CUT[c]) for c in CUT}
assert (sq == R_year["70/90"]).all()
sq.value_counts().to_csv(RES / "sql_check_duckdb.csv")

# ---- 1. 区切りを変える（2025年の1年分）----
cnt = pd.DataFrame({c: R_year[c].value_counts().reindex(["A", "B", "C"]) for c in CUT})
cross = pd.crosstab(R_year["70/90"], R_year["80/95"]); cross.to_csv(RES / "cutoff_crosstab.csv")
cut_changed = float((R_year["70/90"] != R_year["80/95"]).mean() * 100)

# ---- 2. 期間を変える ----
rows = []; mon_rank = {}; q_rank = {}
for c in CUT:
    for mm in range(1, 13):
        r_ = abc(piv[2025][mm], CUT[c]); mon_rank[(c, mm)] = r_
        rows.append({"区切り": c, "期間": "1か月", "どの期間": f"{mm}月", "1年分と違う(%)": 100 * (r_ != R_year[c]).mean(),
                     "Aの数": int((r_ == "A").sum()), "1年分でAなのにAでない": int(((R_year[c] == "A") & (r_ != "A")).sum()),
                     "1年分でAでないのにA": int(((R_year[c] != "A") & (r_ == "A")).sum())})
    for qq in range(4):
        r_ = abc(piv[2025][[3 * qq + 1, 3 * qq + 2, 3 * qq + 3]].sum(1), CUT[c]); q_rank[(c, qq)] = r_
        rows.append({"区切り": c, "期間": "3か月", "どの期間": f"{3 * qq + 1}〜{3 * qq + 3}月", "1年分と違う(%)": 100 * (r_ != R_year[c]).mean(),
                     "Aの数": int((r_ == "A").sum()), "1年分でAなのにAでない": int(((R_year[c] == "A") & (r_ != "A")).sum()),
                     "1年分でAでないのにA": int(((R_year[c] != "A") & (r_ == "A")).sum())})
    r24 = abc(Y24, CUT[c])
    rows.append({"区切り": c, "期間": "前の年の1年分", "どの期間": "2024年", "1年分と違う(%)": 100 * (r24 != R_year[c]).mean(), "Aの数": int((r24 == "A").sum()),
                 "1年分でAなのにAでない": int(((R_year[c] == "A") & (r24 != "A")).sum()), "1年分でAでないのにA": int(((R_year[c] != "A") & (r24 == "A")).sum())})
PER = pd.DataFrame(rows); PER.round(2).to_csv(RES / "period_vs_year.csv", index=False)

# 種類ごと（通年・季節）に、1年分と違う割合
rows = []
for c in CUT:
    for k in ("通年", "夏型", "冬型"):
        ix = kind.index[kind == k]
        rows.append({"区切り": c, "種類": k, "商品": len(ix),
                     "1か月で違う(%)": np.mean([100 * (mon_rank[(c, mm)][ix] != R_year[c][ix]).mean() for mm in range(1, 13)]),
                     "3か月で違う(%)": np.mean([100 * (q_rank[(c, qq)][ix] != R_year[c][ix]).mean() for qq in range(4)])})
KIND = pd.DataFrame(rows); KIND.round(1).to_csv(RES / "changed_by_kind.csv", index=False)

# ---- 3. 季節の商品：1年分では A か B なのに、月の分析で C に落ちる月の数 ----
c = "70/90"
M = pd.DataFrame({mm: mon_rank[(c, mm)] for mm in range(1, 13)})
seas = kind.index[(kind != "通年") & (R_year[c] != "C")]; allyr = kind.index[(kind == "通年") & (R_year[c] != "C")]
c_months = (M == "C").sum(1)
SE = pd.DataFrame({"種類": kind, "1年分のランク": R_year[c], "Cになった月の数": c_months, "Aになった月の数": (M == "A").sum(1)})
SE.to_csv(RES / "months_in_c_by_item.csv")
seas_c = {"季節の商品（1年分でAかB）": int(len(seas)), "Cに落ちた月の数の平均": round(float(c_months[seas].mean()), 1),
          "6か月以上Cの商品(%)": round(100 * float((c_months[seas] >= 6).mean()), 1),
          "通年の商品（1年分でAかB）": int(len(allyr)), "通年_Cに落ちた月の数の平均": round(float(c_months[allyr].mean()), 2)}
# 月ごと：季節の商品が A に入っている数
A_by_month = pd.DataFrame({"月": range(1, 13), "夏型でA": [(M.loc[kind.index[kind == "夏型"], mm] == "A").sum() for mm in range(1, 13)],
                           "冬型でA": [(M.loc[kind.index[kind == "冬型"], mm] == "A").sum() for mm in range(1, 13)],
                           "夏型でC": [(M.loc[kind.index[kind == "夏型"], mm] == "C").sum() for mm in range(1, 13)],
                           "冬型でC": [(M.loc[kind.index[kind == "冬型"], mm] == "C").sum() for mm in range(1, 13)]})
A_by_month.to_csv(RES / "seasonal_rank_by_month.csv", index=False)

# 月から次の月へ：A の入れ替わり
churn = [100 * ((M[mm] == "A") & (M[mm + 1] != "A")).sum() / (M[mm] == "A").sum() for mm in range(1, 12)]

# ---- 4. 月ごとの揺れの大きさを変える（季節の商品なしでも入れ替わるか）----
rows = []
for nz in (0.0, 0.1, 0.3, 0.5):
    d = make(SEED + 7, noise=nz); pv = d.pivot_table(index="商品ID", columns=["年", "月"], values="売上"); kd = d.drop_duplicates("商品ID").set_index("商品ID")["種類"]
    ry = abc(pv[2025].sum(1), CUT["70/90"]); ix = kd.index[kd == "通年"]
    rows.append({"月ごとの揺れ（対数の標準偏差）": nz,
                 "1か月で違う_全商品(%)": np.mean([100 * (abc(pv[2025][mm], CUT["70/90"]) != ry).mean() for mm in range(1, 13)]),
                 "1か月で違う_通年の商品(%)": np.mean([100 * (abc(pv[2025][mm], CUT["70/90"])[ix] != ry[ix]).mean() for mm in range(1, 13)]),
                 "3か月で違う_全商品(%)": np.mean([100 * (abc(pv[2025][[3 * q_ + 1, 3 * q_ + 2, 3 * q_ + 3]].sum(1), CUT["70/90"]) != ry).mean() for q_ in range(4)])})
NZ = pd.DataFrame(rows); NZ.round(1).to_csv(RES / "by_noise.csv", index=False)

g = lambda c_, p: PER[(PER["区切り"] == c_) & (PER["期間"] == p)]["1年分と違う(%)"]
main = {"商品": N, "季節の商品": int((kind != "通年").sum()), "2025年の売上の合計": int(Y25.sum()),
        "ランクの数（1年分）": cnt.to_dict(), "区切りを70/90から80/95に変えるとランクが変わる商品(%)": round(cut_changed, 1),
        "上位何%の商品で売上の7割・8割": [round(100 * (R_year["70/90"] == "A").mean(), 1), round(100 * (R_year["80/95"] == "A").mean(), 1)],
        "1年分と違う(%)": {c_: {"1か月（12か月の平均）": round(float(g(c_, "1か月").mean()), 1), "1か月の最小・最大": [round(float(g(c_, "1か月").min()), 1), round(float(g(c_, "1か月").max()), 1)],
                             "3か月（4回の平均）": round(float(g(c_, "3か月").mean()), 1), "前の年の1年分": round(float(g(c_, "前の年の1年分").iloc[0]), 1)} for c_ in CUT},
        "種類ごと": KIND.round(1).to_dict("records"), "季節の商品": seas_c,
        "月から次の月へ、Aから外れる割合(%)": {"平均": round(float(np.mean(churn)), 1), "最小": round(float(np.min(churn)), 1), "最大": round(float(np.max(churn)), 1)},
        "Aの数（月ごと、70/90）": [int((M[mm] == "A").sum()) for mm in range(1, 13)], "揺れを変える": NZ.round(1).to_dict("records")}
json.dump(main, open(RES / "a410_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図 ----
SRC = "架空の商品別売上（作成者が乱数で作成、seed 410）"
fig, ax = plt.subplots(figsize=(8.6, 4.3))
labs = ["1か月\n（12か月の平均）", "3か月\n（4回の平均）", "前の年の1年分\n（2024年）"]; x = np.arange(3); w = 0.38
for k, (c_, col) in enumerate(zip(CUT, [BLUE, ORANGE])):
    v = [g(c_, "1か月").mean(), g(c_, "3か月").mean(), g(c_, "前の年の1年分").iloc[0]]
    ax.bar(x + (k - 0.5) * w, v, w, color=col, label=f"区切り {c_}")
    for i, vv in enumerate(v): ax.text(i + (k - 0.5) * w, vv + 0.6, f"{vv:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylim(0, 19); ax.set_ylabel("2025年の1年分とランクが違う商品（%）"); ax.legend(frameon=False)
ax.set_title("分析する期間で、ランクが変わる商品の割合（600商品）")
save(fig, "a410_changed_by_period.png", SRC, y=-0.03)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.1))
ax = axes[0]
ax.plot(A_by_month["月"], A_by_month["夏型でC"], marker="o", color=ORANGE, label="夏型の商品のうち C の数"); ax.plot(A_by_month["月"], A_by_month["冬型でC"], marker="o", color=BLUE, label="冬型の商品のうち C の数")
ax.set_xticks(range(1, 13)); ax.set_ylim(0, 52); ax.set_xlabel("月（その1か月の売上で分析）"); ax.set_ylabel("商品の数"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title(f"季節の商品が C になる月（夏型{int((kind == '夏型').sum())}・冬型{int((kind == '冬型').sum())}商品）", fontsize=11)
ax = axes[1]
b = np.arange(0, 14) - 0.5
ax.hist([c_months[allyr], c_months[seas]], bins=b, color=[GRAY, ORANGE], label=[f"通年の商品（{len(allyr)}）", f"季節の商品（{len(seas)}）"], density=True)
ax.set_xticks(range(0, 13)); ax.set_xlabel("12か月のうち、月の分析で C になった月の数"); ax.set_ylabel("商品の割合"); ax.legend(frameon=False, fontsize=9)
ax.set_title("1年分では A か B の商品が、C に落ちた月の数", fontsize=11)
save(fig, "a410_seasonal_in_c.png", SRC + "。区切りは70/90", y=-0.03)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
ax = axes[0]; x = np.arange(3); w = 0.38
for k, (c_, col) in enumerate(zip(CUT, [BLUE, ORANGE])):
    ax.bar(x + (k - 0.5) * w, cnt[c_], w, color=col, label=f"区切り {c_}")
    for i, vv in enumerate(cnt[c_]): ax.text(i + (k - 0.5) * w, vv + 5, f"{vv}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(["A", "B", "C"]); ax.set_ylabel("商品の数"); ax.legend(frameon=False); ax.set_title("区切りを変えたときのランクの数（1年分）", fontsize=11)
ax = axes[1]
ax.plot(NZ["月ごとの揺れ（対数の標準偏差）"], NZ["1か月で違う_通年の商品(%)"], marker="o", color=BLUE, label="1か月（通年の商品だけ）")
ax.plot(NZ["月ごとの揺れ（対数の標準偏差）"], NZ["1か月で違う_全商品(%)"], marker="o", color=ORANGE, label="1か月（全商品）")
ax.plot(NZ["月ごとの揺れ（対数の標準偏差）"], NZ["3か月で違う_全商品(%)"], marker="o", color=GRAY, label="3か月（全商品）")
ax.set_xlabel("月ごとの売上の揺れの大きさ（対数の標準偏差）"); ax.set_ylabel("1年分とランクが違う商品（%）"); ax.legend(frameon=False, fontsize=9); ax.set_ylim(0, None)
ax.set_title("月ごとの揺れが大きいほど、入れ替わる", fontsize=11)
save(fig, "a410_cutoff_and_noise.png", SRC, y=-0.03)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(PER.round(1).to_string()); print(cross)
