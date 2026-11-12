import json, numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, INK, GREEN
ex = pd.read_csv(RES / "example_weekly_chart.csv"); det = json.load(open(RES / "detection.json")); rt = json.load(open(RES / "retrain.json"))
# 図1 例の管理図
fig, ax = plt.subplots(figsize=(9, 4.2)); w = np.arange(1, len(ex) + 1)
mu = ex.bias[52:78].mean(); sd = ex.bias[52:78].std(ddof=1)
ax.plot(w, ex.bias * 100, color=GRAY, lw=1); ax.plot(w[78:], ex.bias[78:] * 100, color=BLUE, lw=1.4)
for k, ls in [(2, ":"), (3, "--")]:
    for sgn in (1, -1): ax.axhline((mu + sgn * k * sd) * 100, color=ORANGE, ls=ls, lw=1)
ax.axvspan(53, 78, color="#eef3fb"); ax.axvline(80, color=INK, lw=0.8)
ax.text(53.5, -6.6, "管理限界を\n決めた26週", fontsize=8.5)
ax.text(81.5, -6.6, "80週目から\n需要が+10%", fontsize=8.5)
a = ex.index[(ex.r1_3sigma == 1) & (ex.index >= 78)]
if len(a): ax.scatter(a[0] + 1, ex.bias[a[0]] * 100, s=70, color="#c0392b", zorder=5); ax.annotate(f"{a[0]+1}週目に3σを超えて鳴った", (a[0] + 1, ex.bias[a[0]] * 100), (a[0] + 14, 1.0), fontsize=9, arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
ax.set_xlabel("週"); ax.set_ylabel("週の誤差（実績÷予測−1、%）")
ax.set_title("週の誤差の管理図（架空の1本）：点線は±2σ、破線は±3σ。1〜52週は予測を作った期間", loc="left", fontsize=11)
save(fig, "a296_chart.png")
# 図2 鳴るまでの週数と空振り
rules = ["R1 3σを1回", "R2 2σを3週中2回", "R3 1σを4週続けて", "R1〜R3のどれか", "CUSUM（k=0.5, h=4）"]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1.6, 1]})
ax = axes[0]; x = np.arange(len(rules)); wdt = 0.25
for i, (s, c) in enumerate([("+5%", GRAY), ("+10%", BLUE), ("+20%", ORANGE)]):
    v = [det["main"][s][r]["detected_within_8w"] * 100 for r in rules]
    ax.bar(x + (i - 1) * wdt, v, wdt, color=c, label=f"需要が{s}")
short = ["R1\n3σを1回", "R2\n2σを3週中2回", "R3\n1σを4週続けて", "R1〜R3の\nどれか", "CUSUM"]
ax.set_xticks(x); ax.set_xticklabels(short, fontsize=8.5); ax.set_ylabel("8週以内に鳴った割合（%）"); ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3)
ax.set_title("変化を8週以内に見つけた割合", loc="left", fontsize=11)
ax = axes[1]; v = [det["main"]["+0%"][r]["false_alarms_per_year"] for r in rules]; v2 = [det["annual5"]["+0%"][r]["false_alarms_per_year"] for r in rules]
ax.barh(x + 0.2, v, 0.38, color=BLUE, label="誤差が週ごとに独立"); ax.barh(x - 0.2, v2, 0.38, color=ORANGE, label="予測が年の季節（±5%）を\n取りこぼしている")
for i, (a1, a2) in enumerate(zip(v, v2)): ax.text(a1 + 0.3, i + 0.2, f"{a1:.2f}", va="center", fontsize=8.5); ax.text(a2 + 0.3, i - 0.2, f"{a2:.1f}", va="center", fontsize=8.5)
ax.set_yticks(x); ax.set_yticklabels(["R1", "R2", "R3", "R1〜R3", "CUSUM"]); ax.invert_yaxis(); ax.set_xlim(0, 25); ax.set_xlabel("変化がないのに鳴った回数（1年あたり）"); ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.45, -0.17), ncol=1)
ax.set_title("空振り", loc="left", fontsize=11)
fig.suptitle("決まりを組み合わせるほど早く見つかるが、空振りも増える。誤差に季節が残っていると、管理図は鳴りっぱなしになった", x=0.01, ha="left", fontsize=11.2, y=1.02)
save(fig, "a296_rules.png", y=-0.2)
# 図3 作り直しの決まり
fig, ax = plt.subplots(figsize=(8.5, 3.8)); strats = ["作り直さない", "13週ごと", "鳴ったら"]; x = np.arange(3)
a = [rt[f"+10% {s}"]["first8_weeks_pct"] for s in strats]; b = [rt[f"+10% {s}"]["weekly_abs_error_after_break_pct"] for s in strats]; c = [rt[f"+0% {s}"]["weekly_abs_error_after_break_pct"] for s in strats]
ax.bar(x - 0.27, a, 0.26, color=GRAY, label="+10%：変化の後の8週"); ax.bar(x, b, 0.26, color=BLUE, label="+10%：変化の後の77週"); ax.bar(x + 0.27, c, 0.26, color=GREEN, label="変化なし：同じ77週")
for xs, vs in [(x - 0.27, a), (x, b), (x + 0.27, c)]:
    for xi, vi in zip(xs, vs): ax.text(xi, vi + 0.15, f"{vi:.1f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{s}\n（作り直し {rt[f'+10% {s}']['refits_per_run']:g}回／変化なしで {rt[f'+0% {s}']['refits_per_run']:g}回）" for s in strats], fontsize=9)
ax.set_ylabel("週の誤差の絶対値の平均（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("鳴ったら作り直す決まりは、変化の直後の誤差を10%から6.6%に下げ、変化がないときの損はわずかだった", loc="left", fontsize=10.8)
save(fig, "a296_retrain.png")
