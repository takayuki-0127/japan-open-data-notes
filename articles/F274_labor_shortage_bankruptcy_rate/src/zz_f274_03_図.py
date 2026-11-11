"""図を figures/ に書く（6枚）。"""
import csv, json, os
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
plt.rcParams["svg.hashsalt"] = "f274"; plt.rcParams["figure.dpi"] = 100
H = os.path.dirname(os.path.abspath(__file__)) + "/../"
Y = {int(r["year"]): {k: (float(v) if v != "" else None) for k, v in r.items()} for r in csv.DictReader(open(H + "results/A_yearly.csv", encoding="utf-8"))}
R = json.load(open(H + "results/main.json", encoding="utf-8"))
yrs = [y for y in sorted(Y) if y >= 2016]
C = {"tdb": "#1f5fa8", "tsr3": "#e07b00", "tsr4": "#8c8c8c", "k": "#555555"}
def s(k, ys=yrs): return [Y[y][k] for y in ys]
def save(fig, name):
    fig.tight_layout(); fig.savefig(H + "figures/" + name, dpi=150, metadata={"Software": None}); plt.close(fig)
# 図1 件数
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(yrs, s("tdb_jinte"), "-o", color=C["tdb"], label="帝国データバンク「人手不足倒産」")
for seg in ([2016, 2017, 2018, 2019], [2022, 2023, 2024, 2025]):
    ax.plot(seg, s("tsr_3f", seg), "-s", color=C["tsr3"], label="東京商工リサーチ 3要因（後継者難を除く）" if seg[0] == 2016 else None)
    ax.plot(seg, s("tsr_4f", seg), "--^", color=C["tsr4"], label="東京商工リサーチ 4要因（後継者難を含む）" if seg[0] == 2016 else None)
for y in (2019, 2025):
    for k, c in (("tdb_jinte", C["tdb"]), ("tsr_3f", C["tsr3"]), ("tsr_4f", C["tsr4"])):
        ax.annotate(f"{Y[y][k]:.0f}", (y, Y[y][k]), textcoords="offset points", xytext=(0, -15) if k == "tsr_3f" else (0, 7), ha="center", fontsize=9, color=c)
ax.set_ylabel("件（負債1,000万円以上）"); ax.set_xticks(yrs); ax.set_ylim(0, 950); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("図1 人手不足に関わる倒産の件数（東京商工リサーチの2020・21年は年の値なし）", fontsize=11)
save(fig, "f274_1_counts.png")
# 図2 法人10万社あたり・企業10万者あたり（TDB）
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(yrs, s("tdb_jinte_per10man_hojin"), "-o", color=C["tdb"], label="法人10万社あたり（国税庁の法人数）")
ax.plot(yrs, s("tdb_jinte_per10man_kigyo"), "--o", color="#7aa6d6", label="企業10万者あたり（経済センサスの企業数、個人企業を含む）")
for y in (2019, 2025):
    ax.annotate(f"{Y[y]['tdb_jinte_per10man_hojin']:.1f}", (y, Y[y]["tdb_jinte_per10man_hojin"]), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=C["tdb"])
ax.set_ylabel("件（帝国データバンク）"); ax.set_xticks(yrs); ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_ylim(0, 16)
ax.set_title("図2 会社の数でそろえた人手不足倒産（2025年の法人数と2022年以降の企業数は延ばした値）", fontsize=10.5)
save(fig, "f274_2_per_firm.png")
# 図3 倒産全体に占める割合
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(yrs, s("tdb_share_pct"), "-o", color=C["tdb"], label="帝国データバンク（人手不足倒産 ÷ 倒産全体）")
for seg in ([2016, 2017, 2018, 2019], [2022, 2023, 2024, 2025]):
    ax.plot(seg, s("tsr3_share_pct", seg), "-s", color=C["tsr3"], label="東京商工リサーチ 3要因 ÷ 倒産全体" if seg[0] == 2016 else None)
    ax.plot(seg, s("tsr4_share_pct", seg), "--^", color=C["tsr4"], label="東京商工リサーチ 4要因 ÷ 倒産全体" if seg[0] == 2016 else None)
ax2 = ax.twinx(); ax2.bar(yrs, s("tdb_total_per10man_hojin"), color="#dddddd", width=0.6, zorder=0); ax2.set_ylabel("倒産全体（法人10万社あたり、灰色の棒）", color="#888888"); ax2.set_ylim(0, 1200)
ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False); ax2.spines["top"].set_visible(False)
ax.set_ylabel("%"); ax.set_xticks(yrs); ax.set_ylim(0, 10); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("図3 倒産全体に占める人手不足倒産の割合", fontsize=11)
save(fig, "f274_3_share.png")
# 図4 TSRの4要因の内訳（数え方）
fig, ax = plt.subplots(figsize=(8, 4.6))
ys = [2016, 2017, 2018, 2019, 2022, 2023, 2024, 2025]; x = np.arange(len(ys)); bot = np.zeros(len(ys))
for k, lab, c in (("tsr_kyujinnan", "求人難", "#e07b00"), ("tsr_taishoku", "従業員退職", "#f2b366"), ("tsr_jinkenhi", "人件費高騰", "#b34700"), ("tsr_koukeisha", "後継者難（いまは別に集計）", "#bdbdbd")):
    v = np.array(s(k, ys)); ax.bar(x, v, bottom=bot, color=c, label=lab, width=0.65); bot += v
for i, y in enumerate(ys): ax.text(i, bot[i] + 10, f"{bot[i]:.0f}", ha="center", fontsize=9)
ax.set_xticks(x, [str(y) for y in ys]); ax.set_ylabel("件（東京商工リサーチ）"); ax.set_ylim(0, 950); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.axvline(3.5, color="#999999", lw=0.8, ls=":"); ax.text(3.5, 900, " 2020・21年は3要因の年の値なし", fontsize=8.5, color="#666666")
ax.set_title("図4 東京商工リサーチの「人手不足」関連倒産の内訳（2019年までは後継者難を含めて発表）", fontsize=10)
save(fig, "f274_4_tsr_breakdown.png")
# 図5 有効求人倍率と法人10万社あたり（TDB）
fig, ax = plt.subplots(figsize=(7.2, 5))
xs = np.array([Y[y]["yuko_kyujin"] for y in yrs]); zs = np.array(s("tdb_jinte_per10man_hojin"))
cols = ["#1f5fa8" if y <= 2019 else ("#999999" if y <= 2022 else "#d1495b") for y in yrs]
ax.scatter(xs, zs, c=cols, s=45, zorder=3)
for y, a, b in zip(yrs, xs, zs): ax.annotate(str(y), (a, b), textcoords="offset points", xytext=(5, 4), fontsize=9)
h = R["H4"]; xx = np.linspace(1.1, 1.65, 10); ax.plot(xx, h["intercept"] + h["slope"] * xx, color="#1f5fa8", lw=1, ls="--", label="2016〜2019年の当てはめ")
ax.set_xlabel("有効求人倍率（年平均）"); ax.set_ylabel("人手不足倒産（法人10万社あたり、帝国データバンク）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("図5 求人倍率と人手不足倒産（青＝2016〜19年、灰＝2020〜22年、赤＝2023〜25年）", fontsize=10)
save(fig, "f274_5_jobratio.png")
# 図6 問い直し：3要因の中身
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4.4), gridspec_kw={"width_ratios": [1.3, 1]})
ys = [2016, 2017, 2018, 2019, 2022, 2023, 2024, 2025]; x = np.arange(len(ys)); bot = np.zeros(len(ys))
for k, lab, c in (("tsr_kyujinnan", "求人難", "#e07b00"), ("tsr_taishoku", "従業員退職", "#f2b366"), ("tsr_jinkenhi", "人件費高騰", "#b34700")):
    v = np.array([R["reask"]["share"][str(y)][k] * 100 for y in ys]); a1.bar(x, v, bottom=bot, color=c, label=lab, width=0.65); bot += v
a1.set_xticks(x, [str(y)[2:] for y in ys]); a1.set_ylabel("3要因の中の割合（%）"); a1.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3); a1.set_ylim(0, 118); a1.set_yticks([0, 20, 40, 60, 80, 100])
a1.set_title("3要因の中の割合（年は下2桁）", fontsize=10)
g = R["reask"]["per_hojin_ratio_2025_2019"]; labs = ["求人難", "従業員退職", "人件費高騰"]; vals = [g["tsr_kyujinnan"], g["tsr_taishoku"], g["tsr_jinkenhi"]]
a2.barh(labs, vals, color=["#e07b00", "#f2b366", "#b34700"]); a2.axvline(1, color="#999999", lw=0.8)
for i, v in enumerate(vals): a2.text(v + 0.05, i, f"{v:.1f}倍", va="center", fontsize=9)
a2.set_xlim(0, 4.8); a2.set_title("法人10万社あたり 2025年÷2019年", fontsize=10)
fig.suptitle("図6 もう一度問う：増えたのは「採れない」倒産か、「払えない」倒産か（東京商工リサーチ）", fontsize=10.5)
save(fig, "f274_6_reask.png")
print("ok")
