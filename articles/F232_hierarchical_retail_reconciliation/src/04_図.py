# F232 04 図
import pandas as pd, numpy as np, json, pathlib
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.unicode_minus"] = False
B = pathlib.Path(__file__).resolve().parents[1]; R = B / "results"; FG = B / "figures"
Y = pd.read_csv(B / "data/hier_wide.csv", index_col=0); nodes = pd.read_csv(B / "data/nodes.csv")
COL = {"ボトムアップ": "#1f77b4", "MinT（縮小）": "#d62728", "WLS（ばらつき）": "#2ca02c", "WLS（構造）": "#9467bd",
       "ベース（そろえない）": "#555555", "トップダウン（予測の割合）": "#ff7f0e", "トップダウン（過去の割合）": "#8c564b", "OLS": "#e377c2"}
ORDER = ["ボトムアップ", "WLS（ばらつき）", "WLS（構造）", "MinT（縮小）", "ベース（そろえない）", "トップダウン（予測の割合）", "OLS", "トップダウン（過去の割合）"]
LVN = ["全体", "業態", "中分類", "商品（葉）"]

# 図1：階層の形（2025年の販売額と葉の数）
last = Y.loc["2025-01":"2025-12"].sum()
types = ["スーパー", "コンビニ", "ドラッグストア", "百貨店", "家電大型専門店", "ホームセンター"]
fig, ax = plt.subplots(figsize=(10, 5.2))
cm = plt.get_cmap("tab20")
for k, g in enumerate(types):
    lv = [c for c in Y.columns if c.startswith(g + "/") and nodes.set_index("ノード").loc[c, "階層"] == 3]
    vals = last[lv].sort_values(ascending=False); left = 0
    for j, (c, v) in enumerate(vals.items()):
        ax.barh(k, v / 1e6, left=left, color=cm(j % 20), edgecolor="white", lw=0.6)
        if v / last[g] > 0.2 and v / 1e6 > 1.2: ax.text(left + v / 2e6, k, c.split("/")[1][:6], ha="center", va="center", fontsize=8)
        left += v / 1e6
    ax.text(left + 0.3, k, f"{last[g]/1e6:.1f}兆円・{len(lv)}商品", va="center", fontsize=9)
ax.set_yticks(range(6)); ax.set_yticklabels(types); ax.invert_yaxis()
ax.set_xlabel("2025年の販売額（兆円）"); ax.set_xlim(0, last[types].max() / 1e6 * 1.35)
ax.set_title("そろえる対象：全体→6業態→（中分類5）→48商品、合わせて60系列（商業動態統計）")
fig.tight_layout(); fig.savefig(FG / "f232_1_hierarchy.png", dpi=150); plt.close()

# 図2：ベース予測のつじつまのずれ（全体の予測 vs 6業態の予測の合計）
gp = pd.read_csv(R / "B_base_incoherence_total_vs_types.csv")
v = gp.iloc[:, 1:].values
fig, ax = plt.subplots(figsize=(9, 4.6))
hh = np.arange(1, 13)
ax.fill_between(hh, np.percentile(v, 10, 0), np.percentile(v, 90, 0), color="#aaa", alpha=.4, label="起点39回の10〜90%")
ax.plot(hh, np.median(v, 0), "o-", color="k", label="中央値")
ax.set_xticks(hh); ax.set_xlabel("何か月先の予測か"); ax.set_ylabel("ずれ（%）")
ax.set_title("別々に作ると合わない：全体の予測と「6業態の予測の合計」のずれ")
ax.legend(); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(FG / "f232_2_incoherence.png", dpi=150); plt.close()

# 図3：方法×階層のMAPE（主の条件）
d = pd.read_csv(R / "D_mape_relative_to_base.csv"); dm = d[d.条件.str.startswith("主")]
P = dm.pivot_table(index="方法", columns="階層名", values="MAPE").loc[ORDER, LVN]
Q = dm.pivot_table(index="方法", columns="階層名", values="ベース比_%").loc[ORDER, LVN]
fig, ax = plt.subplots(figsize=(9.5, 5.4))
im = ax.imshow(Q.clip(-40, 60).values, cmap="RdBu_r", vmin=-40, vmax=40, aspect="auto")
for i in range(len(ORDER)):
    for j in range(4):
        ax.text(j, i, f"{P.values[i,j]:.2f}%\n({Q.values[i,j]:+.0f}%)", ha="center", va="center", fontsize=9, color="white" if abs(Q.values[i,j]) > 30 else "black")
ax.set_xticks(range(4)); ax.set_xticklabels(LVN); ax.set_yticks(range(len(ORDER))); ax.set_yticklabels(ORDER)
ax.set_title("階層ごとの外れ（MAPE、1〜12か月先の平均）と、そろえない予測との比（青＝良くなった）")
fig.colorbar(im, ax=ax, label="ベース比（%）"); fig.tight_layout(); fig.savefig(FG / "f232_3_methods_levels.png", dpi=150); plt.close()

# 図4：予測の先ごと
c = pd.read_csv(R / "C_mape_by_level_horizon.csv"); c = c[c.条件.str.startswith("主")]
show = ["ボトムアップ", "MinT（縮小）", "WLS（ばらつき）", "ベース（そろえない）", "トップダウン（予測の割合）"]
fig, axs = plt.subplots(1, 3, figsize=(12, 4.4))
for ax, lv in zip(axs, ["全体", "業態", "商品（葉）"]):
    for meth in show:
        x = c[(c.階層名 == lv) & (c.方法 == meth)].set_index("hb").MAPE.reindex(["1〜3か月", "4〜6か月", "7〜12か月"])
        ax.plot(x.index, x.values, "o-", color=COL[meth], label=meth)
    ax.set_title(lv); ax.grid(alpha=.3); ax.set_ylabel("MAPE（%）")
axs[0].legend(fontsize=8)
fig.suptitle("どの先の予測でも、全体と業態では「商品を足し上げる」がいちばん小さい外れ")
fig.tight_layout(); fig.savefig(FG / "f232_4_horizon.png", dpi=150); plt.close()

# 図5：条件を変えても同じか
conds = [x for x in d.条件.unique()]
lab = {k: k.split("（")[0] if not k.startswith("主") else "主" for k in conds}
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
for ax, lv in zip(axs, ["全体", "商品（葉）"]):
    for k, meth in enumerate(["ボトムアップ", "MinT（縮小）", "WLS（ばらつき）", "ベース（そろえない）"]):
        xs, ys = [], []
        for j, cd in enumerate(conds):
            r = d[(d.条件 == cd) & (d.方法 == meth) & (d.階層名 == lv)]
            if len(r): xs.append(j + (k - 1.5) * 0.15); ys.append(r.MAPE.iloc[0])
        ax.plot(xs, ys, "o", color=COL[meth], label=meth, ms=7)
    ax.set_xticks(range(len(conds))); ax.set_xticklabels([("主" if cd.startswith("主") else "季節ナイーブ" if cd.startswith("ベース") else "コロナ前" if cd.startswith("コロナ") else "2階層だけ" if cd.startswith("2階層") else "MinT外れ24か月") for cd in conds], fontsize=9)
    ax.set_title(lv); ax.set_ylabel("MAPE（%）"); ax.grid(alpha=.3)
axs[0].legend(fontsize=8)
fig.suptitle("条件を変えても、足し上げはほかの方法と同じか良い（季節ナイーブはもともとそろっている）")
fig.tight_layout(); fig.savefig(FG / "f232_5_robustness.png", dpi=150); plt.close()
print("ok")
