import json
import numpy as np, pandas as pd, geopandas as gpd
import matplotlib.pyplot as plt
from common import RAW, RES, FIG

FIG.mkdir(exist_ok=True)
g = pd.read_csv(RES / "estimates_2023.csv")
o = pd.read_csv(RES / "estimates_2023_overdisp.csv"); g = g.merge(o, on="code")
S = json.load(open(RES / "summary.json"))
P = g.y_colon.sum() / g.n_colon.sum()

# 図1 ファネルプロット
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.scatter(g.n_colon, g.p * 100, s=7, alpha=0.45, color="#3b6fb6", lw=0)
nn = np.logspace(np.log10(15), np.log10(g.n_colon.max()), 200)
for zc, ls, lab in [(1.96, "--", "95%"), (3.09, ":", "99.8%")]:
    se = np.sqrt(P * (1 - P) / nn) * 100
    ax.plot(nn, P * 100 + zc * se, "k" + ls, lw=1, label=f"偶然だけなら収まる範囲（{lab}）")
    ax.plot(nn, np.clip(P * 100 - zc * se, 0, None), "k" + ls, lw=1)
ax.axhline(P * 100, color="#e08a2c", lw=1.2, label=f"全国 {P*100:.1f}%")
ax.set_xscale("log"); ax.set_ylim(0, 65)
ax.set_xlabel("対象者数（国保の被保険者、40〜69歳、対数目盛）"); ax.set_ylabel("大腸がん検診の受診率（%）")
ax.set_title("小さな町ほど受診率は散らばる。ただ、大きな市でも多くが「偶然の範囲」の外にある（2023年度）", fontsize=11)
ax.legend(fontsize=9, loc="upper right")
fig.tight_layout(); fig.savefig(FIG / "f19_funnel.png", dpi=150); plt.close()

# 図2 直接推定 → 縮小推定（対象者が少ない40の町。名前は出さない）
s = g.sort_values("n_colon").head(40).sort_values("p").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(9, 7))
for i, r in s.iterrows():
    ax.annotate("", xy=(r.eb_od * 100, i), xytext=(r.p * 100, i),
                arrowprops=dict(arrowstyle="->", color="#e08a2c", lw=1.2))
    ax.plot(r.p * 100, i, "o", color="#3b6fb6", ms=4)
    ax.text(max(r.p, r.eb_od) * 100 + 1, i, f"{int(r.n_colon)}人", va="center", fontsize=7, color="#555")
ax.plot([], [], "o", color="#3b6fb6", label="直接の受診率")
ax.plot([], [], color="#e08a2c", label="縮小推定（年ごとのぶれも入れた版）")
ax.set_yticks([]); ax.set_xlabel("受診率（%）"); ax.set_ylabel("対象者が少ない40の町（受診率の順）")
ax.set_title("対象者が少ない町ほど、推定値は「似た町の水準」へ引き寄せられる", fontsize=11)
ax.legend(fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f19_arrows.png", dpi=150); plt.close()

# 図3 直接推定をどれだけ信じるか（γ）と対象者数
fig, ax = plt.subplots(figsize=(9, 5))
ax.scatter(g.n_colon, g.gamma, s=6, alpha=0.5, color="#3b6fb6", lw=0, label="二項分布どおりのぶれ")
ax.scatter(g.n_colon, g.gamma_od, s=6, alpha=0.5, color="#e08a2c", lw=0, label=f"年ごとのぶれも入れた版（ぶれ×{S['phi_hat']:.1f}）")
ax.set_xscale("log"); ax.set_ylim(0, 1.02)
ax.set_xlabel("対象者数（対数目盛）"); ax.set_ylabel("直接の受診率に置く重み γ")
ax.set_title("対象者が数百人を下回ると、直接の受診率への重みが下がっていく", fontsize=11)
ax.legend(fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f19_gamma.png", dpi=150); plt.close()

# 図4 地図（縮小推定、過分散あり）
gm = gpd.read_file(RAW / "N03-21_210101.json")
gm = gm[gm["N03_007"].notna()].copy()
gm["code5"] = gm["N03_007"].astype(str).str.zfill(5).astype(int)
is_ward = gm["N03_004"].fillna("").str.endswith("区") & gm["N03_003"].fillna("").str.endswith("市")
# 政令市の区は市のコード（下2桁が00）にまとめる。東京23区は区のまま
gm["key"] = np.where(is_ward & (gm.code5 // 1000 != 13), gm.code5 // 100 * 100, gm.code5)
gm = gm.dissolve(by="key", as_index=False)
gm = gm.merge(g[["code", "eb_od"]], left_on="key", right_on="code", how="left")
print("地図で色が付いた市区町村", gm.eb_od.notna().sum(), "/", len(g))
fig, ax = plt.subplots(figsize=(10, 10))
gm[gm.eb_od.isna()].plot(ax=ax, color="#eeeeee", lw=0)
gm[gm.eb_od.notna()].plot(ax=ax, column=gm.loc[gm.eb_od.notna(), "eb_od"] * 100, cmap="YlGnBu", vmin=5, vmax=40,
                          lw=0.05, edgecolor="white", legend=True,
                          legend_kwds=dict(shrink=0.5, label="受診率の縮小推定（%）"))
ax.set_xlim(128.5, 146.2); ax.set_ylim(30.5, 45.7); ax.set_axis_off()
ax.set_title("大腸がん検診の受診率（国保、40〜69歳、2023年度、縮小推定）\n灰色はデータなし。沖縄・小笠原などの離島は範囲外", fontsize=11)
fig.savefig(FIG / "f19_map.png", dpi=150, bbox_inches="tight"); plt.close()

# 図5 翌年をどちらがよく当てたか（対象者数の区分ごと）
v = S["base"]["validation_2024"]
labs = [k for k in v if k != "全体"]
imp = [(1 - v[k]["mse_eb"] / v[k]["mse_dir"]) * 100 for k in labs]
rob = pd.read_csv(RES / "robustness.csv")
fig, axes = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw=dict(width_ratios=[1, 1.3]))
ax = axes[0]
ax.bar(range(len(labs)), imp, color="#3b6fb6")
for i, x in enumerate(imp):
    ax.text(i, x + 0.2, f"{x:.1f}%", ha="center", fontsize=9)
ax.set_xticks(range(len(labs))); ax.set_xticklabels([f"{k}\n({v[k]['n']})" for k in labs], fontsize=9)
ax.set_ylabel("翌年（2024年度）との二乗誤差が\n直接の値より何%小さいか", fontsize=9)
ax.set_title("縮小推定のほうが翌年をよく当てた。\n効くのは対象者が少ない町", fontsize=11)
ax = axes[1]
y = np.arange(len(rob))[::-1]
ax.barh(y + 0.18, rob["全体_改善%"], 0.36, color="#3b6fb6", label="全体")
ax.barh(y - 0.18, rob["小_改善%"], 0.36, color="#e08a2c", label="対象者500人未満")
ax.set_yticks(y); ax.set_yticklabels(rob["設定"], fontsize=9)
ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("翌年との誤差の改善（%）")
ax.set_title("設定を変えても、改善はプラス", fontsize=11)
ax.legend(fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "f19_validation.png", dpi=150); plt.close()
print("ok")
