"""F290 図（6枚）"""
import importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
spec = importlib.util.spec_from_file_location("sim", ROOT / "src" / "zz_f290_03_シミュ.py")
sim = importlib.util.module_from_spec(spec); spec.loader.exec_module(sim)
A = pd.read_csv(ROOT / "results" / "A_main.csv"); B = pd.read_csv(ROOT / "results" / "B_robust.csv")
C = pd.read_csv(ROOT / "results" / "C_tipping.csv"); J = json.loads((ROOT / "results" / "main.json").read_text())
MN = {"M0": "重みなし", "M1": "男女×年齢", "M2": "＋雇用形態", "M3": "＋就業時間・所得"}
SN = {"S1": "S1 年齢・男女で決まる", "S2": "S2 観測できる5項目で決まる", "S3": "S3 S2＋副業ありほど答える"}
C1, C2, C3, C4 = "#9aa5b1", "#4c78a8", "#59a14f", "#e15759"

# 図1 回答者の構成と母集団（期待値）
d = sim.population(2022)
def resp_share(sc):
    e = sim.eta(d, sc); a = sim.calib_a(d, e, 0.20); p = 1 / (1 + np.exp(-(a + e)))
    return d.P * p / (d.P * p).sum()
r2, r3 = resp_share("S2"), resp_share("S3")
fig, ax = plt.subplots(1, 3, figsize=(13, 4.2), gridspec_kw={"width_ratios": [7, 4, 2]})
for k, (col, ttl) in enumerate([("age", "年齢"), ("emp", "雇用形態")]):
    g = pd.DataFrame({"母集団": d.P, "回答者（S2）": r2, "k": d[col]}).groupby("k").sum()
    if col == "age": g = g.loc[list(sim.AGE_C)]
    x = np.arange(len(g)); ax[k].bar(x - 0.2, g["母集団"] * 100, 0.4, color=C1, label="母集団")
    ax[k].bar(x + 0.2, g["回答者（S2）"] * 100, 0.4, color=C2, label="回答者（S2）")
    ax[k].set_xticks(x); ax[k].set_xticklabels(g.index, rotation=30, ha="right", fontsize=9); ax[k].set_title(ttl); ax[k].set_ylabel("%")
ax[0].legend(frameon=False, fontsize=9)
vals = [(d.P * d.y).sum(), (r2 * d.y).sum(), (r3 * d.y).sum()]
ax[2].bar([0, 1, 2], np.array(vals) * 100, color=[C1, C2, C4]); ax[2].set_xticks([0, 1, 2]); ax[2].set_xticklabels(["母集団", "S2", "S3"])
ax[2].set_title("副業ありの割合"); ax[2].set_ylabel("%")
for i, v in enumerate(vals): ax[2].text(i, v * 100 + 0.1, f"{v*100:.1f}", ha="center", fontsize=9)
fig.suptitle("図1 回答者の構成（回答率20%、期待値）：若い人・非正規が多く、高齢・役員・自営が少ない", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig1_respondent_mix.png", dpi=150); plt.close()

# 図2 方法ごとの偏り
fig, ax = plt.subplots(1, 3, figsize=(13, 4.2), sharey=False)
for k, sc in enumerate(["S1", "S2", "S3"]):
    s = A[(A.scenario == sc) & A.method.isin(list(MN))].set_index("method").loc[list(MN)]
    ax[k].bar(range(4), s.bias_pt, yerr=s.sd_pt, color=[C1, C2, C3, C4], capsize=3)
    ax[k].axhline(0, color="k", lw=0.8); ax[k].set_xticks(range(4)); ax[k].set_xticklabels(MN.values(), rotation=20, fontsize=9)
    ax[k].set_title(SN[sc], fontsize=10); ax[k].set_ylabel("偏り（ポイント）")
    for i, v in enumerate(s.bias_pt): ax[k].text(i + 0.08, v / 2, f"{v:+.2f}", ha="left", fontsize=8, color="k")
fig.suptitle(f"図2 副業ありの割合の偏り（本当の値 {J['truth_pct']:.2f}%、500回の平均。ひげは標準偏差）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig2_bias_by_method.png", dpi=150); plt.close()

# 図3 95%区間が本当の値を含む割合
fig, ax = plt.subplots(figsize=(8.5, 4.2))
x = np.arange(3)
for i, (m, c) in enumerate(zip(MN, [C1, C2, C3, C4])):
    v = [A[(A.scenario == sc) & (A.method == m)].coverage.iloc[0] * 100 for sc in ["S1", "S2", "S3"]]
    ax.bar(x + (i - 1.5) * 0.2, v, 0.2, color=c, label=MN[m])
ax.axhline(95, ls="--", color="k", lw=0.8); ax.text(2.45, 96, "95%", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([SN[s] for s in ["S1", "S2", "S3"]], fontsize=9); ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=9, loc=(0.70, 0.30))
ax.set_title("図3 95%区間が本当の値を含んだ割合：S3 はどの方法でも0%", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig3_coverage.png", dpi=150); plt.close()

# 図4 補正に使っていない項目での確かめ
h = C[C.method == "M2h"].sort_values("odds_ratio")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].plot(h.odds_ratio, h.tvd_inc, "o-", color=C2); ax[0].axhline(J["noise95_tvd_inc"], ls="--", color="k", lw=0.8)
ax[0].text(1.0, J["noise95_tvd_inc"] + 0.001, "偏りのない回答者でのぶれ（95%点）", fontsize=9)
ax[0].set_ylim(0, 0.04); ax[0].set_xlabel("副業ありの人の答えやすさ（オッズ比）"); ax[0].set_ylabel("所得の分布のずれ（TVD）")
ax[0].set_title("(a) 補正に使っていない所得の分布のずれ", fontsize=10)
ax[1].plot(h.odds_ratio, h.bias_pt, "o-", color=C4); ax[1].fill_between(h.odds_ratio, -h.halfw_pt, h.halfw_pt, color=C1, alpha=0.3, label="95%区間の半幅")
ax[1].axhline(0, color="k", lw=0.8); ax[1].set_xlabel("副業ありの人の答えやすさ（オッズ比）"); ax[1].set_ylabel("副業ありの割合の偏り（ポイント）")
ax[1].legend(frameon=False, fontsize=9); ax[1].set_title("(b) 知りたい項目の偏り", fontsize=10)
fig.suptitle("図4 男女・年齢・雇用形態・就業時間でレーキングした後：所得のずれは変わらず、知りたい項目の偏りだけが大きくなる", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "fig4_holdout_check.png", dpi=150); plt.close()

# 図5 回答者数と RMSE（S2）
rows = []
for v, n in [("R3_n2000", 2000), ("base200", 5000), ("R3_n20000", 20000)]:
    for m in ["M0", "M1", "M3"]:
        s = B[(B.variant == v) & (B.scenario == "S2") & (B.method == m)].iloc[0]
        rows.append(dict(n=n, m=m, rmse=s.rmse_pt, bias=s.bias_pt, sd=s.sd_pt))
R = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for i, (m, c) in enumerate(zip(["M0", "M1", "M3"], [C1, C2, C4])):
    s = R[R.m == m]; ax.bar(np.arange(3) + (i - 1) * 0.27, s.rmse, 0.27, color=c, label=MN[m])
    for j, (rm, b) in enumerate(zip(s.rmse, s.bias)): ax.text(j + (i - 1) * 0.27, rm + 0.01, f"{rm:.2f}", ha="center", fontsize=8)
ax.set_xticks(range(3)); ax.set_xticklabels(["約2,000人", "約5,000人", "約20,000人"]); ax.set_ylabel("RMSE（ポイント）")
ax.legend(frameon=False, fontsize=9); ax.set_title("図5 S2：回答者が多いほど、ぶれより偏りが効き、重み付けの差が出る", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig5_rmse_by_n.png", dpi=150); plt.close()

# 図6 問い直し：どこまでの「答えやすさの差」で区間が外れるか
h0 = C[C.method == "M0"].sort_values("odds_ratio"); h3 = C[C.method == "M3"].sort_values("odds_ratio")
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
ax[0].plot(h0.odds_ratio, h0.bias_pt, "o-", color=C1, label="重みなし"); ax[0].plot(h3.odds_ratio, h3.bias_pt, "o-", color=C4, label="5項目でレーキング")
ax[0].fill_between(h3.odds_ratio, 0, h3.halfw_pt, color=C2, alpha=0.2, label="95%区間の半幅（レーキング）")
ax[0].set_xlabel("副業ありの人の答えやすさ（オッズ比）"); ax[0].set_ylabel("偏り（ポイント）"); ax[0].legend(frameon=False, fontsize=9)
ax[0].set_title("(a) 偏り", fontsize=10)
ax[1].plot(h3.odds_ratio, h3.coverage * 100, "o-", color=C4); ax[1].axhline(95, ls="--", color="k", lw=0.8)
ax[1].set_xlabel("副業ありの人の答えやすさ（オッズ比）"); ax[1].set_ylabel("95%区間が本当の値を含む割合（%）"); ax[1].set_title("(b) 区間の当たり方（5項目でレーキング）", fontsize=10)
fig.suptitle("図6 問い直し：答えやすさが1.2倍で、補正後の区間の当たりは半分を下回る", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig6_tipping_point.png", dpi=150); plt.close()
print("figures ok")
