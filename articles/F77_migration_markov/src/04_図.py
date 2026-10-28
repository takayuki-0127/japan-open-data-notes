"""図を作る。"""
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from common import DATA, RES, FIG

st = pd.read_csv(RES / "stationary_2025.csv")
path = pd.read_csv(RES / "path_migration_only.csv")
yr = pd.read_csv(RES / "stationary_by_year.csv")
cmp = pd.read_csv(RES / "projection_2050.csv")
rob = pd.read_csv(RES / "robustness.csv")
S = json.load(open(RES / "summary.json"))

# 1. 地図：定常分布 ÷ いまの割合
g = gpd.read_file(DATA / "pref.geojson").rename(columns={"N03_001": "pref"}).merge(st, on="pref")
ok = g.pref != "沖縄県"
fig, ax = plt.subplots(figsize=(7.5, 7.5))
norm = TwoSlopeNorm(vmin=0.65, vcenter=1.0, vmax=1.25)
g[ok].plot(column="ratio", cmap="RdBu", norm=norm, edgecolor="white", linewidth=0.3, ax=ax, legend=True,
           legend_kwds=dict(label="定常分布での割合 ÷ 2025年の割合", shrink=0.6))
ax.set_xlim(128.5, 146); ax.set_ylim(30.5, 45.8); ax.axis("off")
ax.set_title("今の人の流れが続くと、人口の割合はどう変わるか（沖縄県は省略、比は%.2f）"
             % float(st.loc[st.pref == "沖縄県", "ratio"].iloc[0]), fontsize=11)
fig.text(0.02, 0.02, "2025年の都道府県間移動（日本人）から作った推移確率の定常分布。出生・死亡は入れていない", fontsize=8)
fig.savefig(FIG / "f77_map.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 2. 都道府県ごとの比（棒）
s = st.sort_values("ratio")
fig, ax = plt.subplots(figsize=(8, 9))
col = ["#c0392b" if r > 1 else "#2c7fb8" for r in s.ratio]
ax.barh(s.pref, s.ratio, color=col)
ax.axvline(1, color="k", lw=0.8)
ax.set_xlabel("定常分布での割合 ÷ 2025年の割合（1より大きい＝割合が増える）")
ax.set_title("割合が増えるのは10都府県、37道県は減る", fontsize=12)
ax.tick_params(axis="y", labelsize=7)
fig.savefig(FIG / "f77_ratio.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 3. 収束の速さ
fig, ax = plt.subplots(figsize=(8, 4.8))
p = path[path.t <= 300]
ax.plot(2025 + p.t, 100 * p.tokyo_area, color="#c0392b", label="1都3県の割合（移動だけ）")
ax.axhline(100 * S["base"]["tokyo_area_pi"], color="#c0392b", ls="--", lw=1, label="定常分布 %.1f%%" % (100 * S["base"]["tokyo_area_pi"]))
for yy in (2050, 2075):
    v = 100 * p.loc[p.t == yy - 2025, "tokyo_area"].iloc[0]
    ax.plot(yy, v, "o", color="k", ms=4); ax.annotate("%d年 %.1f%%" % (yy, v), (yy, v), xytext=(5, -14), textcoords="offset points", fontsize=9)
ax.set_xlabel("年"); ax.set_ylabel("%"); ax.legend(fontsize=9, loc="lower right")
ax.set_title("定常分布までの差が半分になるのに%d年（固有値から出した半減期は約%d年）"
             % (S["base"]["years_to_half_gap"], round(S["base"]["half_life"])), fontsize=11)
fig.savefig(FIG / "f77_path.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 4. 年ごとの定常分布
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(yr.year, 100 * yr.tokyo_area_pi, "o-", color="#c0392b", label="1都3県（定常分布）")
ax.plot(yr.year, 100 * yr.tokyo_pi, "s-", color="#7f3c8d", label="東京都（定常分布）")
ax.axhline(100 * S["base"]["tokyo_area_now"], color="#c0392b", lw=0.8, ls=":", label="1都3県の2025年の割合")
ax.axvspan(2019.5, 2022.5, color="0.9")
ax.text(2021, 31.5, "コロナ期", ha="center", fontsize=9)
ax.set_xlabel("移動の年"); ax.set_ylabel("%"); ax.legend(fontsize=9, loc="center left")
ax.set_title("その年の流れが続いた場合の行き着く先：2019年が最も集中、コロナで一度戻った", fontsize=11)
fig.savefig(FIG / "f77_by_year.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 5. 2050年：出生・死亡を入れた投影と社人研
fig, ax = plt.subplots(figsize=(6.6, 6.2))
x = 100 * (cmp.ipss_share2050 / cmp.now_share - 1); y = 100 * (cmp.mine_share2050 / cmp.now_share - 1)
ax.scatter(x, y, s=18, color="#2c7fb8")
lo, hi = min(x.min(), y.min()) - 2, max(x.max(), y.max()) + 2
ax.plot([lo, hi], [lo, hi], color="k", lw=0.8)
for _, r in cmp.assign(x=x, y=y).iterrows():
    if r.pref in ("東京都", "秋田県", "沖縄県", "青森県", "神奈川県", "高知県"):
        ax.annotate(r.pref, (r.x, r.y), xytext=(3, 3), textcoords="offset points", fontsize=8)
ax.set_xlabel("社人研2023年推計：2025→2050年の割合の変化（%）")
ax.set_ylabel("この記事の連鎖（移動＋出生・死亡）：同じ変化（%）")
ax.set_title("2050年の割合の変化は社人研とよく似る（相関%.2f）" % S["growth"]["corr_share_change_vs_ipss"], fontsize=11)
fig.savefig(FIG / "f77_vs_ipss.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 6. 頑健性
fig, ax = plt.subplots(figsize=(8, 4.2))
r = rob.iloc[::-1]
ax.barh(r.setting, 100 * r.tokyo_area_pi, color="#c0392b")
for i, v in enumerate(100 * r.tokyo_area_pi):
    ax.text(v + 0.2, i, "%.1f%%" % v, va="center", fontsize=9)
ax.axvline(100 * S["base"]["tokyo_area_now"], color="k", lw=0.8, ls=":")
ax.set_xlim(25, 42); ax.set_xlabel("1都3県の定常分布での割合（%）、点線は2025年の割合")
ax.set_title("設定を変えても行き着く先は34〜38%", fontsize=11)
fig.savefig(FIG / "f77_robust.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print("ok")
