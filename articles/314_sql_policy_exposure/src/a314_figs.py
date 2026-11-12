"""314 図3枚"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

r = pd.read_csv(RES / "eight_ways.csv"); mon = pd.read_csv(RES / "by_month_2025.csv"); sw = pd.read_csv(RES / "growth_sweep.csv")
lab = [n.replace("_", " ", 1) for n in r["数え方"]]

fig, ax = plt.subplots(figsize=(9.2, 4.8))
v = r["正解との差(%)"].values; vv = np.clip(v, -20, 32)
ax.barh(range(8), vv, color=[GRAY if x == 0 else (ORANGE if x > 0 else BLUE) for x in v]); ax.set_yticks(range(8)); ax.set_yticklabels(lab, fontsize=9.2); ax.invert_yaxis()
ax.axvline(0, color=INK, lw=0.8)
for i, x in enumerate(v):
    num = f"{x:+.2f}%".replace("-", "−") if abs(x) < 1 else f"{x:+.1f}%".replace("-", "−")
    t = "正解（基準）" if i == 0 else f"{num}（事故率は {r['事故率(%)'][i]:.2f}%）" + ("→ 図の外" if abs(x) > 50 else "")
    ax.text(max(vv[i], 0) + 0.6, i, t, va="center", ha="left", fontsize=9)
ax.set_xlim(-22, 52); ax.set_xlabel("日数で数えた経過契約年との差（%）")
ax.set_title(f"在籍の量を件数で代えると、−8% から約2倍までずれた\n（日数で数えた事故率は {r['事故率(%)'][0]:.2f}%。分母がずれた分だけ事故率もずれる）", loc="left")
save(fig, "a314_eight.png")

fig, ax = plt.subplots(figsize=(9, 4.6))
for key, c, ls, name in [("B", BLUE, "-", "B 年初の件数"), ("C", ORANGE, "-", "C 年末の件数"), ("D", GREEN, "-", "D 年初と年末の平均"),
                         ("E", GRAY, "-", "E 月初の件数の12か月平均"), ("F", INK, "--", "F 月初と月末の平均の12か月平均")]:
    d = sw[sw["数え方"].str.startswith(key)]
    ax.plot(d["新しい契約の増え方"] * 100, d["正解との差(%)"], ls, marker="o", ms=4, color=c, label=name)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks([-20, -10, 0, 15, 30, 50]); ax.set_xticklabels(["−20%", "−10%", "0%", "+15%\n（基本）", "+30%", "+50%"])
ax.set_xlabel("新しい契約が毎年どれだけ増えるか"); ax.set_ylabel("正解との差（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("契約が増えも減りもしなければ、どの数え方でもほぼ合う。\n増えている・減っているときほど、年初や年末の1時点で代えるとずれる", loc="left")
save(fig, "a314_growth.png")

fig, ax = plt.subplots(figsize=(9, 4.4))
x = np.arange(12); w = 0.27
ax.bar(x - w, mon["月初の差(%)"], w, color=BLUE, label="月初の件数"); ax.bar(x, mon["月末の差(%)"], w, color=ORANGE, label="月末の件数"); ax.bar(x + w, mon["平均の差(%)"], w, color=INK, label="月初と月末の平均")
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"{i}月" for i in range(1, 13)]); ax.set_ylabel("日数で数えた在籍との差（%）"); ax.legend(frameon=False, ncol=3, fontsize=9, loc="upper right")
ax.set_title("月ごとに見ると、4月（始期が集まる月）は月初・月末の件数が2%あまりずれた", loc="left")
save(fig, "a314_month.png")
