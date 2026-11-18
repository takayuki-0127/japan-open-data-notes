"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2, GRID, MUTE = "#52514e", "#e4e3df", "#a3a29d"
SRC = "出典：総務省「消費者物価指数」（2025年基準、全国、月次・年平均）をもとに作成者が加工して作成"
META = {"Software": None}
m = pd.read_csv(ROOT / "data" / "monthly.csv").set_index("period")
main = json.load(open(R / "main.json", encoding="utf-8"))
req = json.load(open(R / "requestion.json", encoding="utf-8"))
TAXM = [198904, 199704, 201404, 201910]


def taxrate(p):
    return 0.0 if p < 198904 else 0.03 if p < 199704 else 0.05 if p < 201404 else 0.08 if p < 201910 else 0.10


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


t = pd.to_datetime([f"{str(i)[:4]}-{str(i)[4:]}-01" for i in m.index])
tax = np.array([taxrate(p) for p in m.index])

# 図1 税を除いた水準（1987年4月＝100）
fig, ax = plt.subplots(figsize=(9.5, 5.2)); fig.subplots_adjust(bottom=0.17, top=0.88, left=0.08, right=0.84)
sel = m.index >= 198704
series = [("jr_regular", "普通運賃（JR）", C[0], 2.4), ("pr_regular", "普通運賃（JR以外）", C[1], 1.8),
          ("bus", "一般路線バス代", C[2], 1.8), ("services", "サービス全体", C[3], 1.8)]
for k, lab, col, lw in series:
    s = m[k] / (1 + tax) * 1.10
    s = s / s.loc[198704] * 100
    ax.plot(t[sel], s[sel], color=col, lw=lw)
    ax.text(t[-1] + pd.Timedelta(days=120), s.iloc[-1], f"{lab} {s.iloc[-1]:.0f}", color=INK2, fontsize=9, va="center")
for p in TAXM:
    ax.axvline(pd.Timestamp(f"{str(p)[:4]}-{str(p)[4:]}-01"), color=MUTE, lw=0.7, ls=":")
ax.set_ylabel("消費税を除いた指数（1987年4月＝100）"); ax.grid(axis="y", color=GRID, lw=0.7)
fig.suptitle("図1 消費税を除くと、JR の普通運賃は1987年4月から2026年2月まで4.5%しか上がっていない", x=0.01, ha="left", fontsize=12)
foot(fig, "点線は消費税の導入と引き上げ（1989年4月・1997年4月・2014年4月・2019年10月）。税を除いた指数＝指数÷（1＋その月の税率）")
save(fig, "fig1_taxex_levels_since_1987.png")

# 図2 普通運賃（JR）の前月比が0.5%以上動いた月
ch = main["jr_regular_change_months_all"]
fig, ax = plt.subplots(figsize=(9.5, 5)); fig.subplots_adjust(bottom=0.17, top=0.88, left=0.08, right=0.97)
for p, v, tx in ch:
    d = pd.Timestamp(f"{str(p)[:4]}-{str(p)[4:]}-01")
    ax.bar(d, v, width=200, color=C[3] if tx else C[0])
    if p >= 198700:
        dx = {199601: -260, 199704: 260, 202304: -120, 202504: -230}.get(p, 0)
        ax.text(d + pd.Timedelta(days=dx), v * 1.12 + 0.3, f"{str(p)[:4]}.{int(str(p)[4:])}\n{v:+.1f}%", ha="center", fontsize=7.6, color=INK2)
ax.set_yscale("symlog", linthresh=5); ax.set_yticks([0, 2, 5, 10, 20, 50]); ax.set_yticklabels(["0", "2", "5", "10", "20", "50"])
ax.set_ylim(0, 90)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C[0], label="消費税以外の月"), Patch(color=C[3], label="消費税の引き上げの月")], frameon=False, loc="upper right"); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_ylabel("前月比（%、5%より上は縮めた目盛り）")
fig.suptitle("図2 JR の普通運賃が動いた月：1996年2月から2023年3月までは消費税の月だけ", x=0.01, ha="left", fontsize=12)
foot(fig, "前月比の絶対値が0.5%以上の月（1975年2月〜2026年9月）。下がった月はない。1987年以降の月に年月と前月比を付けた")
save(fig, "fig2_jr_change_months.png")

# 図3 期間の上がり方（税を除く）
sc = main["span_changes"]
items = [("jr_regular", "普通運賃（JR）"), ("jr_commuter", "通勤定期（JR）"), ("pr_regular", "普通運賃（JR以外）"), ("pr_commuter", "通勤定期（JR以外）"),
         ("bus", "一般路線バス代"), ("taxi", "タクシー代"), ("services", "サービス全体"), ("all_items", "総合")]
fig, ax = plt.subplots(figsize=(9.5, 5.2)); fig.subplots_adjust(bottom=0.17, top=0.88, left=0.2, right=0.97)
y = np.arange(len(items))[::-1]
v1 = [sc[f"198704-202602|{k}"]["tax_excluded"] for k, _ in items]
v2 = [sc[f"198704-202609|{k}"]["tax_excluded"] for k, _ in items]
ax.barh(y + 0.19, v1, height=0.36, color=C[0], label="1987年4月→2026年2月")
ax.barh(y - 0.19, v2, height=0.36, color=C[1], label="1987年4月→2026年9月")
for yy, a1, a2 in zip(y, v1, v2):
    ax.text(a1 + 1, yy + 0.19, f"{a1:+.1f}%", va="center", fontsize=8.4, color=INK2)
    ax.text(a2 + 1, yy - 0.19, f"{a2:+.1f}%", va="center", fontsize=8.4, color=INK2)
ax.set_yticks(y); ax.set_yticklabels([n for _, n in items]); ax.set_xlabel("消費税を除いた上がり方（%）")
ax.grid(axis="x", color=GRID, lw=0.7); ax.legend(frameon=False, loc="lower right"); ax.set_xlim(0, 95)
fig.suptitle("図3 JR 発足からの上がり方（税を除く）：JR の運賃はサービス全体より小さい", x=0.01, ha="left", fontsize=12)
foot(fig, "月次の指数を消費税率で割って比べた（2026年4月の指数に運賃の改定が出たため、2026年2月と9月の2つの終点を示す）")
save(fig, "fig3_change_since_1987.png")

# 図4 問い直し：券の種類ごとの4月の前月比
fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.9), sharey=True); fig.subplots_adjust(bottom=0.2, top=0.82, left=0.08, right=0.97, wspace=0.08)
kinds = [("regular", "普通運賃"), ("commuter", "通勤定期"), ("school", "通学定期")]
for ax, (grp, gl) in zip(axs, [("jr", "JR"), ("pr", "JR以外")]):
    xs = np.arange(4)
    for i, (k, kl) in enumerate(kinds):
        vals = [req["april_mom"][p][f"{grp}_{k}"] for p in ["202304", "202404", "202504", "202604"]]
        ax.bar(xs + (i - 1) * 0.26, vals, width=0.24, color=C[i], label=kl)
        for xx, vv in zip(xs + (i - 1) * 0.26, vals):
            if abs(vv) >= 0.5:
                ax.text(xx, vv + (0.2 if vv >= 0 else -0.2), f"{vv:+.1f}", ha="center", va="bottom" if vv >= 0 else "top", fontsize=7.6, color=INK2)
    ax.set_xticks(xs); ax.set_xticklabels(["2023年4月", "2024年4月", "2025年4月", "2026年4月"], fontsize=9)
    ax.axhline(0, color=INK2, lw=0.8); ax.grid(axis="y", color=GRID, lw=0.7); ax.set_title(gl, fontsize=11, color=INK2)
axs[0].set_ylabel("前月比（%）"); axs[0].legend(frameon=False, loc="upper left", fontsize=9)
fig.suptitle("図4 2023年以降の値上げは、普通運賃より通勤定期で大きかった", x=0.01, ha="left", fontsize=12)
foot(fig, "各年4月の前月比。運賃の改定は指数では4月に表れている（3月の前月比はどの券も0.0%）")
save(fig, "fig4_april_by_ticket_type.png")
print("figures done")
