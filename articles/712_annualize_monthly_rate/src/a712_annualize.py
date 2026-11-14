"""712 月の伸び率を年率に直すとき、12倍するか複利で直すかで、どれだけ違うのか

1) 式：月の伸び率 r を 12r と (1+r)^12−1 にしたときの差
2) 架空の会員数の月次（2022-01〜2025-12）。月の伸び率は平均2%前後で、月ごとにゆれ、途中で伸びが鈍る。
   各月の伸び率を年率に直した値（12倍・複利）と、その後12か月で実際に伸びた割合、前年同月比を比べる。
seed 712。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の会員数の月次（作成者が乱数で作成、seed 712）"
rng = np.random.default_rng(712)
# 1) 式
r = np.linspace(-0.06, 0.08, 141)
C = pd.DataFrame({"monthly_pct": r * 100, "simple_x12_pct": r * 1200, "compound_pct": ((1 + r) ** 12 - 1) * 100})
C["gap_pt"] = C.compound_pct - C.simple_x12_pct
C.round(3).to_csv(RES / "formula.csv", index=False)
gap_at = lambda m: {k: round(float(C.loc[(C.monthly_pct - m).abs().idxmin(), k]), 1) for k in ["simple_x12_pct", "compound_pct", "gap_pt"]}
thr = float(C[(C.monthly_pct > 0) & (C.gap_pt.abs() >= 1)].monthly_pct.min())
# 2) 架空の会員数
months = pd.date_range("2022-01-01", "2025-12-01", freq="MS")
base = np.where(np.arange(len(months)) < 24, 0.025, 0.012)  # 2024年から伸びが鈍る
g = base + rng.normal(0, 0.012, len(months)); g[0] = 0
mem = np.round(10000 * np.cumprod(1 + g)).astype(int)
M = pd.DataFrame({"ym": months, "members": mem})
M.assign(ym=M.ym.dt.strftime("%Y-%m")).to_csv(DATA / "members_monthly.csv", index=False)
M["mom"] = M.members / M.members.shift() - 1
M["ann_simple"] = M.mom * 12 * 100
M["ann_compound"] = ((1 + M.mom) ** 12 - 1) * 100
M["next12"] = (M.members.shift(-12) / M.members - 1) * 100
M["yoy"] = (M.members / M.members.shift(12) - 1) * 100
E2 = M.dropna(subset=["mom", "next12", "yoy"])  # 3つとも出せる月（2023-01〜2024-12）でそろえる
mae = {"12倍": round(float((E2.ann_simple - E2.next12).abs().mean()), 1), "複利": round(float((E2.ann_compound - E2.next12).abs().mean()), 1),
       "前年同月比をそのまま使う": round(float((E2.yoy - E2.next12).abs().mean()), 1)}
M.round(3).assign(ym=M.ym.dt.strftime("%Y-%m")).to_csv(RES / "monthly.csv", index=False)
out = {"formula": {"1%": gap_at(1), "2%": gap_at(2), "3%": gap_at(3), "5%": gap_at(5), "-3%": gap_at(-3), "-5%": gap_at(-5)},
       "gap_reaches_1pt_at_monthly_pct": round(thr, 1),
       "members_start": int(mem[0]), "members_end": int(mem[-1]),
       "monthly_growth_mean_pct": {"2022-2023": round(float(M.mom[1:24].mean() * 100), 2), "2024-2025": round(float(M.mom[24:].mean() * 100), 2)},
       "annualized_range_pct": {"12倍": [round(float(M.ann_simple.min()), 1), round(float(M.ann_simple.max()), 1)],
                                "複利": [round(float(M.ann_compound.min()), 1), round(float(M.ann_compound.max()), 1)]},
       "mae_vs_next12_pt": mae, "mae_months": f"{E2.ym.min():%Y-%m}〜{E2.ym.max():%Y-%m}（{len(E2)}か月）",
       "full_year_growth_pct": {"2022→2023": round(float(mem[23] / mem[11] - 1) * 100, 1), "2024→2025": round(float(mem[47] / mem[35] - 1) * 100, 1)}}
json.dump(out, open(RES / "a712_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：式
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(C.monthly_pct, C.compound_pct, color=BLUE, label="複利 (1+月率)^12−1")
ax.plot(C.monthly_pct, C.simple_x12_pct, color=ORANGE, ls="--", label="12倍")
for m in [-5, 3, 5]:
    v = gap_at(m); ax.annotate(f"月{m:+d}%：12倍{v['simple_x12_pct']:+.0f}%、複利{v['compound_pct']:+.0f}%", (m, v["compound_pct"]), xytext=(-150 if m > 0 else 10, 10), textcoords="offset points", fontsize=8.5)
ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
ax.set_xlabel("月の伸び率（%）"); ax.set_ylabel("年率（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("月の伸びが大きいほど、12倍は年率を小さく、マイナスでは大きく見せる")
save(fig, "a712_formula.png", SRC)
# 図2：月ごとの年率と、実際の次の12か月
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.plot(M.ym, M.ann_simple, color=ORANGE, lw=1, label="その月の伸びの12倍")
ax.plot(M.ym, M.ann_compound, color=BLUE, lw=1, label="その月の伸びの複利")
ax.plot(M.ym, M.next12, color="black", lw=2, label="その後12か月で実際に伸びた割合")
ax.axhline(0, color=GRAY, lw=0.6); ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=9)
ax.set_title("1か月の伸びを年率に直すと、直し方より月のゆれのほうがずっと大きい")
save(fig, "a712_monthly.png", SRC)
# 図3：誤差
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.bar(list(mae.keys()), list(mae.values()), color=[ORANGE, BLUE, GREEN])
for i, v in enumerate(mae.values()):
    ax.text(i, v + 0.5, f"{v:.1f}", ha="center")
ax.set_ylabel("その後12か月の実際の伸びとの差（平均、ポイント）")
ax.set_title("その後1年の伸びの見込みとして：12倍・複利・前年同月比", fontsize=12)
save(fig, "a712_error.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
