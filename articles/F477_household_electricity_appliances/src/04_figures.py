"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "svg.hashsalt": "f477"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#999999"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：環境省「家庭部門のCO2排出実態統計調査」（年度。2025年度は速報値）をもとに作成者が加工して作成"
META = {"Software": None}
KWH = 1e6 / 3600


def finish(fig, ax, title, src=SRC, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, src, fontsize=7.6, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.loads((R / "main.json").read_text(encoding="utf-8"))
q = json.loads((R / "requestion.json").read_text(encoding="utf-8"))

# 図1：推移
tr = pd.read_csv(R / "trend_national.csv").dropna(subset=["elec_gj"])
fig, ax = plt.subplots(figsize=(9, 5))
fig.subplots_adjust(left=0.09, right=0.97, top=0.86, bottom=0.15)
cols = [C[5] if y == 2025 else C[0] for y in tr.fy]
ax.bar(tr.fy, tr.elec_gj, color=cols, width=0.65)
for y, v in zip(tr.fy, tr.elec_gj):
    ax.text(y, v + 0.15, f"{v:.2f}\n（{v * KWH:,.0f}kWh）", ha="center", fontsize=8.6, color=INK)
ax.text(2024, 0.5, "2024年度は\n調査なし", ha="center", fontsize=8.6, color=INK2)
ax.set_xticks(list(range(2017, 2026)))
ax.set_xticklabels([f"{y}" + ("\n速報" if y == 2025 else "") for y in range(2017, 2026)])
ax.set_ylim(0, 18.5); ax.set_ylabel("電気の消費量（GJ/世帯・年）")
finish(fig, ax, f"1世帯あたりの電気は2017→2023年度に{-m['elec_change_pct']['2017_2023']:.1f}%減った")
save(fig, "fig1_elec_trend.png")

# 図2：用途別の変化（全エネルギー）
u = m["uses_diff_2017_2023"]
uses = ["暖房", "冷房", "給湯", "台所用コンロ", "照明・家電製品等"]
fig, ax = plt.subplots(figsize=(9, 5))
fig.subplots_adjust(left=0.18, right=0.95, top=0.86, bottom=0.15)
vals = [u[k] for k in uses]
ax.barh(uses, vals, color=[C[1] if v > 0 else C[0] for v in vals])
for i, v in enumerate(vals):
    ax.text(v + (0.05 if v > 0 else -0.05), i, f"{v:+.2f}", va="center", ha="left" if v > 0 else "right", fontsize=9.5)
ax.axvline(0, color=INK2, lw=0.8); ax.invert_yaxis(); ax.set_xlim(-3.0, 1.0)
ax.set_xlabel("2017→2023年度の変化（GJ/世帯・年。電気・ガス・灯油の合計）")
finish(fig, ax, f"減ったのは暖房と給湯。照明・家電製品等は減少の{m['lighting_appliances_share_of_decline_pct']:.0f}%", grid="x")
save(fig, "fig2_uses_change.png")

# 図3：使用年数の分布と分解
vt = pd.read_csv(R / "vintage_age_tables.csv")
fr = vt[(vt.appliance == "fridge") & (vt.pair == "2017→2022")]
fig, axs = plt.subplots(1, 2, figsize=(10, 5.2), gridspec_kw={"width_ratios": [1.1, 1]})
fig.subplots_adjust(left=0.07, right=0.97, top=0.80, bottom=0.17, wspace=0.55)
ax = axs[0]
x = np.arange(len(fr)); w = 0.38
ax.bar(x - w / 2, fr.share0, w, color=C[5], label="2017年度")
ax.bar(x + w / 2, fr.share1, w, color=C[0], label="2022年度")
ax.set_xticks(x); ax.set_xticklabels(fr.age, fontsize=8.8, rotation=30)
ax.set_ylabel("世帯の割合（%、製造時期不明を除く）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("冷蔵庫（1台目）の使用年数", loc="left", fontsize=10.5)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax = axs[1]
v = m["vintage"]; hs = m["household_size_2017_2023"]
labels = ["電気の変化（全国）\n2017→2023", "世帯人数の構成 2017→2023\n（半分強は2021年度の重みの段差）", "冷蔵庫の年数の構成\n2017→2022", "エアコンの年数の構成\n2017→2022", "テレビの年数の構成\n2017→2022"]
vals = [m["elec_diff_gj_2017_2023"], hs["composition"], v["fridge_2017_2022"]["composition"], v["aircon_2017_2022"]["composition"], v["tv_2017_2022"]["composition"]]
cols = [INK2, C[3], C[0], C[0], C[0]]
ax.barh(labels, vals, color=cols)
for i, val in enumerate(vals):
    ax.text(val - 0.03 if val < 0 else val + 0.03, i, f"{val:+.3f}" if abs(val) < 0.01 else f"{val:+.2f}", va="center", ha="right" if val < 0 else "left", fontsize=9)
ax.axvline(0, color=INK2, lw=0.8); ax.invert_yaxis(); ax.set_xlim(-1.9, 0.5)
ax.set_xlabel("GJ/世帯・年"); ax.tick_params(axis="y", labelsize=8.8)
ax.set_title("構成の変化で説明できる分", loc="left", fontsize=10.5)
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.suptitle("冷蔵庫は若返っていない。年数の構成で説明できる減少はほぼ0", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
save(fig, "fig3_age_and_decomposition.png")

# 図4：問い直し（LED）
p = pd.read_csv(R / "requestion_led_by_fy.csv")
cats = q["categories_2023"]
short = ["LEDのみ", "LED＋他\n（白熱なし）", "LED＋他\n（白熱あり）", "LEDなし\n（白熱なし）", "LEDなし\n（白熱あり）"]
fig, axs = plt.subplots(1, 2, figsize=(10, 5.2))
fig.subplots_adjust(left=0.07, right=0.97, top=0.80, bottom=0.2, wspace=0.3)
ax = axs[0]
for i, c in enumerate(cats):
    s = p[p.cat == c]
    ax.plot(s.fy, s.share_pct, color=C[i], lw=2 if i == 0 else 1.4, marker="o", ms=3, label=short[i].replace("\n", ""))
ax.set_ylabel("世帯の割合（%）"); ax.legend(frameon=False, fontsize=8.2, loc="upper left", ncol=2)
ax.set_title("照明の種類（住宅全体）", loc="left", fontsize=10.5); ax.set_ylim(0, 52)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax = axs[1]
x = np.arange(len(cats)); w = 0.38
ax.bar(x - w / 2, [q["elec_2017"][c] for c in cats], w, color=C[5], label="2017年度")
ax.bar(x + w / 2, [q["elec_2023"][c] for c in cats], w, color=C[0], label="2023年度")
ax.set_xticks(x); ax.set_xticklabels(short, fontsize=8.2)
ax.set_ylabel("電気（GJ/世帯・年）"); ax.legend(frameon=False, fontsize=9, loc="upper right"); ax.set_ylim(0, 20)
ax.set_title("区分ごとの電気の平均", loc="left", fontsize=10.5)
ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
fig.suptitle(f"LED の世帯ほど電気が多い。LED 化の構成の効果は {q['composition']:+.2f}GJ と逆向き", x=0.01, ha="left", fontsize=12.5, color=INK)
fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
save(fig, "fig4_led_requestion.png")
