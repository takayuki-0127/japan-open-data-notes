"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：総務省「消費者物価指数」2025年基準 品目別価格指数、日本銀行「外国為替相場」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
d = pd.read_csv(D / "monthly.csv").set_index("ym")
x = (d.index // 100) + ((d.index % 100) - 0.5) / 12

# 図1 端末の指数とドル円
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, d.phone_device, color=C[1], lw=2, label="携帯電話機（2025年＝100、左軸）")
ax2 = ax.twinx(); ax2.plot(x, d.usdjpy, color=C[0], lw=1.4, ls="--", label="ドル円（円、右軸）"); ax2.set_ylabel("ドル円（円）"); ax2.spines["top"].set_visible(False)
ax.axvline(2019 + 9.5 / 12, color=GRID, lw=1); ax.text(2019.9, 128, "2019年10月\n改正電気通信事業法", fontsize=8.5, color=INK2)
ax.set_xlim(2004.8, 2027); ax.set_ylim(70, 135); ax2.set_ylim(60, 180); ax.set_xticks(range(2005, 2027, 5))
ax.set_ylabel("携帯電話機の指数")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"端末の指数は2005〜19年に{-m['device_2005_2019']:.0f}%下がり、2019→23年に+{m['device_2019_2023']:.0f}%。ドル円と似た波", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.92, top=0.91, bottom=0.14)
save(fig, F / "fig1_device_index_fx.png", SRC, "注：指数は品質の違いを調整した値で、店で払う値段そのものではない。")

# 図2 通信料（携帯電話）
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, d.mobile_fee, color=C[2], lw=2.2, label="通信料（携帯電話）")
ax.plot(x, d["all"], color=C[5], lw=1.4, label="総合")
for yv, t in [(2021 + 3.5 / 12, "2021年4月\n前月比 %+.0f%%" % m["fee_step_202103_202104"]), (2021 + 9.5 / 12, "2021年10月\n%+.0f%%" % m["fee_step_202109_202110"])]:
    ax.axvline(yv, color=GRID, lw=1)
ax.text(2015.5, 120, f"2021年4月 前月比 {m['fee_step_202103_202104']:+.0f}%\n2021年10月 前月比 {m['fee_step_202109_202110']:+.0f}%", fontsize=9, color=INK2)
ax.set_xlim(1999.8, 2027); ax.set_ylabel("2025年＝100")
ax.legend(frameon=False, loc="upper right", fontsize=9)
style(ax)
ax.set_title(f"通信料の指数は2019年平均より{-m['fee_drop_vs_2019']:.0f}%低い。2022年1月の底からは+{q['fee_rise_from_min']:.0f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig2_mobile_fee.png", SRC)

# 図3 先行の相関
lc = pd.read_csv(R / "lead_corr.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.6))
ax.bar(lc.lead, lc["corr"], color=[C[1] if l == q["best_lead"] else C[5] for l in lc.lead], width=0.7)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlabel("ドル円を何か月先行させたか"); ax.set_ylabel("前年比どうしの相関（2013〜2026年）")
style(ax)
ax.set_title(f"ドル円の動きの約{q['best_lead']}か月あとと、端末の指数がよく並ぶ（相関 {q['best_corr']:.2f}）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.15)
save(fig, F / "fig3_lead_corr.png", SRC)

# 図4 散布図
y = (np.log(d.phone_device) - np.log(d.phone_device.shift(12))) * 100
f = ((np.log(d.usdjpy) - np.log(d.usdjpy.shift(12))) * 100).shift(q["best_lead"])
s = pd.concat([y, f], axis=1).loc[201301:202609].dropna(); s.columns = ["y", "f"]
fig, ax = plt.subplots(figsize=(7.6, 5.6))
pre = s.index < 202001
ax.scatter(s.f[pre], s.y[pre], s=18, color=C[0], alpha=0.7, label="2013〜2019年")
ax.scatter(s.f[~pre], s.y[~pre], s=18, color=C[1], alpha=0.7, label="2020〜2026年")
xx = np.linspace(s.f.min(), s.f.max(), 10); b = np.polyfit(s.f, s.y, 1)
ax.plot(xx, np.polyval(b, xx), color=INK2, lw=1.2)
ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
ax.set_xlabel(f"{q['best_lead']}か月前のドル円の前年比（%、対数×100）"); ax.set_ylabel("携帯電話機の指数の前年比（%、対数×100）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"6か月前のドル円の前年比に対する端末の指数の前年比の傾きは{q['best_slope']:.2f}（並び方の目安）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.15)
save(fig, F / "fig4_scatter.png", SRC, "注：月次の前年比（2013年1月〜2026年9月）。傾きは最小二乗。")
