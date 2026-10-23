"""K2：公的データの「段差」を見つける。駅別乗降客数の前年比を、同じ事業者の動きと比べて、数字の定義が変わったとみられる年を自動で探す"""
from common import *
d = load(); f = flag_breaks(d); d = d.join(f)
x = d[(d.p2019 >= 1000) & (d.p2024 > 0)]
# 1) 事業者全体の前年比（主な公営・私鉄）
P = d[[f"p{y}" for y in YEARS]].where(lambda v: v > 0); P.columns = YEARS
def op_ratio(op):
    out = {}
    for y in range(2016, 2025):
        b = (d.op == op) & P[y].notna() & P[y - 1].notna()
        out[y] = P.loc[b, y].sum() / P.loc[b, y - 1].sum() if b.sum() else np.nan
    return pd.Series(out)
OPS = ["東京都", "横浜市", "仙台市", "神戸市", "東京地下鉄", "東日本旅客鉄道", "東急電鉄", "東武鉄道", "西日本旅客鉄道", "京王電鉄"]
R = pd.DataFrame({op: op_ratio(op) for op in OPS}).T
R.round(3).to_csv(RES / "k2_operator_yoy.csv", encoding="utf-8-sig"); print(R.round(2))
# 2) 段差の数
cnt = {"rows_2019_2024": len(x), "flagged": int((x.n_break > 0).sum()), "flagged_operator_level": int(x.op_break.sum()), "flagged_station_only": int(((x.n_break > 0) & ~x.op_break).sum())}
yrs = x[x.n_break > 0].break_years.str.split(",").explode().value_counts().sort_index()
yrs.to_csv(RES / "k2_break_years.csv", header=["n"], encoding="utf-8-sig"); print(cnt, yrs)
ops = x[x.n_break > 0].groupby("op").size().sort_values(ascending=False).head(12); ops.to_csv(RES / "k2_break_ops.csv", header=["n"], encoding="utf-8-sig")
# 3) 段差を除く前と後で、結論がどう変わるか（2024年度 ÷ 2019年度）
def rec(g): return g.p2024.sum() / g.p2019.sum() * 100
cmp = pd.DataFrame({"all": x.groupby("optype").apply(rec), "clean": x[x.n_break == 0].groupby("optype").apply(rec)})
cmp.loc["全体"] = [rec(x), rec(x[x.n_break == 0])]
cmp.round(1).to_csv(RES / "k2_before_after.csv", encoding="utf-8-sig"); print(cmp.round(1))
# 4) 例：駅の推移
EX = [("中目黒", "東急電鉄"), ("北千住", "東武鉄道"), ("横浜", "横浜市"), ("泉岳寺", "東京都")]
ex = {f"{n}（{o}）": d[(d.name == n) & (d.op == o)][[f"p{y}" for y in YEARS]].dropna(how="all").iloc[0].values for n, o in EX}
ex = pd.DataFrame(ex, index=YEARS); ex.to_csv(RES / "k2_examples.csv", encoding="utf-8-sig"); print(ex)
s = dict(cnt); s.update({"tokyo_to_2024": R.loc["東京都", 2024], "yokohama_2024": R.loc["横浜市", 2024], "sendai_2024": R.loc["仙台市", 2024], "kobe_2024": R.loc["神戸市", 2024],
          "metro_2024": R.loc["東京地下鉄", 2024], "jre_2024": R.loc["東日本旅客鉄道", 2024], "all_before": cmp.loc["全体", "all"], "all_after": cmp.loc["全体", "clean"],
          "public_before": cmp.loc["公営鉄道", "all"], "public_after": cmp.loc["公営鉄道", "clean"]})
pd.Series(s).to_csv(RES / "k2_summary.csv", header=["value"]); print(pd.Series(s))

fig, ax = plt.subplots(figsize=(9.5, 4.6)); im = ax.imshow(np.log(R.values.astype(float)), cmap="RdBu", vmin=-0.7, vmax=0.7, aspect="auto")
ax.set_xticks(range(R.shape[1]), [f"{y}" for y in R.columns], fontsize=8.5); ax.set_yticks(range(len(R)), R.index, fontsize=9)
for i in range(R.shape[0]):
    for j in range(R.shape[1]):
        v = R.iat[i, j]
        if pd.notna(v): ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7.5, color="white" if abs(np.log(v)) > 0.35 else INK)
ax.set_xlabel("年度（前年度との比）"); ax.set_title("事業者全体の前年比：2024年度、公営の地下鉄だけが大きく減っている", loc="left", fontsize=12)
fig.text(0.01, -0.04, SOURCE + "（両方の年に数字がある駅の合計）", fontsize=7, color="#8a8984"); fig.savefig(FIG / "k2_operator_yoy.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4.2))
for (c, col) in zip(ex.columns, [ORANGE, PURPLE, BLUE, GREEN]): ax.plot(YEARS, ex[c] / 10000, marker="o", ms=3.5, color=col, label=c)
ax.set_ylabel("1日の乗降客数（万人）"); ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
ax.set_title("1年で2倍・半分になる駅：利用者が急に変わったというより、数え方が変わったとみられる", loc="left", fontsize=12)
fig.text(0.01, -0.04, SOURCE, fontsize=7, color="#8a8984"); fig.savefig(FIG / "k2_examples.png"); plt.close(fig)
