"""黄砂は西日本ほど多いのか：11地点の観測日を地点別に比べる（1967〜2023年）"""
from common import *

d = load("kosa_days_by_station.csv")
d["date"] = pd.to_datetime(d.date); d = d[d.date.dt.year <= 2023]
ST = ["那覇", "鹿児島", "福岡", "広島", "高松", "大阪", "名古屋", "新潟", "東京", "仙台", "札幌"]   # 西から東へ（経度順）
LON = {"那覇": 127.69, "鹿児島": 130.55, "福岡": 130.38, "広島": 132.46, "高松": 134.05, "大阪": 135.52,
       "名古屋": 136.97, "東京": 139.75, "新潟": 139.05, "仙台": 140.90, "札幌": 141.33}   # 気象台のおよその経度
NY = 2023 - 1967 + 1
X = d[ST]
st = pd.DataFrame({"lon": pd.Series(LON), "days": X.sum(), "per_year": X.sum() / NY})
st["share_of_all_days"] = X.sum() / len(d) * 100
st["alone_days"] = X[d.n_stations == 1].sum()
st["spring_share"] = X[d.date.dt.month.isin([3, 4, 5])].sum() / X.sum() * 100
st["winter_share"] = X[d.date.dt.month.isin([11, 12, 1, 2])].sum() / X.sum() * 100
st["mean_stations_when_obs"] = [(d.n_stations * X[s]).sum() / X[s].sum() for s in st.index]
st = st.loc[ST]
st.round(2).to_csv(RES / "a190_station_stats.csv")
# 条件付き割合：行の地点で観測した日に、列の地点でも観測した割合（%）
M = pd.DataFrame({b: [(X[a] & X[b]).sum() / X[a].sum() * 100 for a in ST] for b in ST}, index=ST)
M.round(1).to_csv(RES / "a190_cooccurrence.csv")
nd = d.n_stations.value_counts().sort_index()
west = ["鹿児島", "福岡", "広島"]; east = ["東京", "仙台", "札幌"]
w_any = X[west].max(axis=1).astype(bool); e_any = X[east].max(axis=1).astype(bool)
L = [f"観測日 {len(d)}日（1967〜2023年、11地点のどこかで観測）",
     "地点別の年平均（西→東）: " + ", ".join(f"{k}{v:.1f}" for k, v in st.per_year.items()),
     "多い順: " + ", ".join(f"{k}{v:.1f}" for k, v in st.per_year.sort_values(ascending=False).items()),
     f"経度と年平均の相関 11地点 r={st.lon.corr(st.per_year):.2f} / 那覇を除く10地点 r={st.drop('那覇').lon.corr(st.drop('那覇').per_year):.2f}",
     f"福岡/東京 {st.per_year['福岡']/st.per_year['東京']:.1f}倍, 広島/札幌 {st.per_year['広島']/st.per_year['札幌']:.1f}倍",
     "全観測日に占める割合: " + ", ".join(f"{k}{v:.0f}%" for k, v in st.share_of_all_days.items()),
     "1地点だけの日の地点: " + ", ".join(f"{k}{int(v)}" for k, v in st.alone_days.items()) + f" / 1地点だけの日 計{int(nd.get(1,0))}日（{nd.get(1,0)/len(d):.0%}）",
     "観測地点数の分布: " + ", ".join(f"{k}地点{v}" for k, v in nd.items()),
     "3〜5月の割合: " + ", ".join(f"{k}{v:.0f}%" for k, v in st.spring_share.items()),
     "11〜2月の割合: " + ", ".join(f"{k}{v:.0f}%" for k, v in st.winter_share.items()),
     "観測した日の平均地点数: " + ", ".join(f"{k}{v:.1f}" for k, v in st.mean_stations_when_obs.items()),
     f"東京で観測した日に福岡でも {M.loc['東京','福岡']:.0f}%, 広島でも {M.loc['東京','広島']:.0f}% / 福岡で観測した日に東京でも {M.loc['福岡','東京']:.0f}%",
     f"札幌で観測した日に広島 {M.loc['札幌','広島']:.0f}% 福岡 {M.loc['札幌','福岡']:.0f}% / 仙台→広島 {M.loc['仙台','広島']:.0f}%",
     f"那覇で観測した日に鹿児島 {M.loc['那覇','鹿児島']:.0f}% 福岡 {M.loc['那覇','福岡']:.0f}% / 那覇だけの日 {int(st.alone_days['那覇'])}",
     f"西3地点（鹿児島・福岡・広島）のどこかで観測 {w_any.sum()}日 / 東3地点（東京・仙台・札幌）のどこかで {e_any.sum()}日 / 東3地点で観測した日のうち西3地点でも {(e_any & w_any).sum()/e_any.sum():.0%} / 東3地点だけ（西なし） {(e_any & ~w_any).sum()}日"]
(RES / "a190_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：地点別の年平均観測日数（西→東）
fig, ax = plt.subplots(figsize=(10, 4.4))
cols = [ORANGE if s in ("那覇",) else BLUE for s in ST]
ax.bar(range(len(ST)), st.per_year, color=cols, width=0.62)
for i, v in enumerate(st.per_year):
    ax.text(i, v + 0.1, f"{v:.1f}", ha="center", fontsize=9)
ax.set_xticks(range(len(ST))); ax.set_xticklabels(ST)
ax.set_ylabel("年平均の観測日数（日）"); ax.set_xlabel("← 西　　　　　　　　　　　　　　　　　　　　東 →")
ax.set_title("黄砂を観測した日数の年平均（1967〜2023年、気象台の目視観測）")
save(fig, "a190_station_days.png")

# 図2：ある地点で観測した日に、ほかの地点でも観測した割合
fig, ax = plt.subplots(figsize=(8.8, 7.4))
im = ax.imshow(M.values, cmap="Blues", vmin=0, vmax=100)
for i in range(len(ST)):
    for j in range(len(ST)):
        v = M.values[i, j]
        ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if v > 60 else INK)
ax.set_xticks(range(len(ST))); ax.set_xticklabels(ST, rotation=45, ha="right")
ax.set_yticks(range(len(ST))); ax.set_yticklabels(ST)
ax.set_xlabel("この地点でも観測した割合（%）"); ax.set_ylabel("この地点で観測した日")
ax.set_title("ある地点で黄砂を観測した日に、ほかの地点でも観測した割合")
ax.spines[:].set_visible(False)
save(fig, "a190_cooccurrence.png")

# 図3：観測した日の、その日の観測地点数（地点別の平均）と1地点だけの日
fig, ax1 = plt.subplots(figsize=(10, 4.4))
ax1.bar(range(len(ST)), st.mean_stations_when_obs, color=LIGHT, width=0.62, label="観測した日の、全国の観測地点数（平均、左）")
ax1.set_ylabel("地点数"); ax1.set_ylim(0, 8)
ax2 = ax1.twinx()
ax2.plot(range(len(ST)), st.alone_days / st.days * 100, color=ORANGE, marker="o", lw=2, label="その地点だけで観測した日の割合（右）")
ax2.set_ylabel("%"); ax2.set_ylim(0, 60); ax2.spines["right"].set_visible(True)
ax1.set_xticks(range(len(ST))); ax1.set_xticklabels(ST)
ax1.set_title("観測した日に黄砂がどこまで広がっていたか")
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=9)
save(fig, "a190_spread.png")
