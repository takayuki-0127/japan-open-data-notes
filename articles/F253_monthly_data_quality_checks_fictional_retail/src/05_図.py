"""05 図（サンプルマート（架空）、合成データ）。図5は reports/dq_2025-12_確定_見本.html を画像にしたもの（playwright）。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#2b2b2b", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BLUE, ORANGE, AQUA, GRAY, INK, MUTED, RED = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29d", "#0b0b0b", "#52514e", "#c8423b"
NOTE = "サンプルマート（架空）・合成データ。会社も数字も実在しません。汚れは筆者が入れたもの。"
S = json.loads((RES / "summary.json").read_text(encoding="utf-8"))


def save(fig, name):
    fig.text(0.01, -0.06, NOTE, fontsize=8, color=MUTED)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


# 図1：汚れの種類 × どのチェックが拾ったか
E = pd.read_csv(RES / "E_detect_by_type.csv", index_col=0)
cols = ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q07", "Q08", "detected", "fixed_range"]
lab = ["Q01\n重複", "Q02\n行の欠け", "Q03\n空", "Q04\nゼロ", "Q05\n同じ値", "Q06\nふだん\nとの比", "Q07\n中の\n関係", "Q08\n部門の\n合計", "8つの\nどれか", "比べる相手：\n決めた範囲\nだけ"]
M = E[cols].values * 100
fig, ax = plt.subplots(figsize=(10.5, 5.6))
ax.imshow(M, cmap="Blues", vmin=0, vmax=130, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M[i, j]
        ax.text(j, i, "" if v == 0 else f"{v:.0f}", ha="center", va="center", fontsize=9.5, color="white" if v > 70 else INK, weight="bold" if j >= 8 else None)
ax.axvline(7.5, color="white", lw=4); ax.axvline(8.5, color="white", lw=4)
ax.set_xticks(range(len(cols)), lab, fontsize=8.6); ax.set_yticks(range(len(E)), E.index, fontsize=9.5)
ax.tick_params(length=0); [s.set_visible(False) for s in ax.spines.values()]
ax.set_title("10種類の汚れは、どのチェックで見つかったか（見つけた割合 %、各480個）", loc="left", fontsize=12)
save(fig, "fig1_detect_by_type.png")

# 図2：ふだんとの比の線 T と、汚れのない月の誤報（売上・客数・点数のどれかで鳴った店×日、1か月あたり）
A = pd.read_csv(RES / "A_false_alarms_by_T_mode.csv")
fig, ax = plt.subplots(figsize=(9, 4.8))
names = {"a": "a：前の8週の同じ曜日だけ", "ab": "a・b（＋1年前の同じ曜日）", "abc": "a・b・c（＋1年前の同じ日付）＝採用"}
for mode, col in zip(["a", "ab", "abc"], [GRAY, BLUE, RED]):
    x = A[(A["mode"] == mode) & (A.metric == "POS3_any")]
    y = x.false_alarms_per_month.clip(lower=0.01)
    ax.plot(x["T"], y, "o-", color=col, lw=2.2 if mode == "abc" else 1.6, label=names[mode])
ax.set_yscale("log"); ax.set_xscale("log"); ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
ax.set_xticks([1.2, 1.3, 1.5, 1.75, 2, 3, 5], ["1.2倍", "1.3倍", "1.5倍", "1.75倍", "2倍", "3倍", "5倍"])
ax.set_yticks([0.01, 0.1, 1, 10, 100], ["0", "0.1", "1", "10", "100"])
ax.axvline(1.5, color=RED, ls=":", lw=1); ax.text(1.52, 60, "採用：1.5倍", color=RED, fontsize=9)
ax.set_xlabel("ふだんの値の何倍（または何分の1）を超えたら鳴らすか"); ax.set_ylabel("汚れのない月に鳴った店×日（1か月あたり）")
ax.set_title("線を下げるほど誤報が増える。参照を3つにすると、同じ線で誤報は約20分の1", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", color="#eee")
save(fig, "fig2_false_alarms_by_threshold.png")

# 図3：売上・客数・点数がそろって f 倍になる汚れ（途中まで・2回足し込み）を見つける割合
B = pd.read_csv(RES / "B_detect_by_factor.csv")
fig, ax = plt.subplots(figsize=(9, 4.8))
for T, col in zip([1.3, 1.5, 2.0, 3.0], [AQUA, RED, BLUE, GRAY]):
    x = B[(B["mode"] == "abc") & (B["T"] == T)].sort_values("factor")
    ax.plot(x.factor, x.detect * 100, "o-", color=col, lw=2.2 if T == 1.5 else 1.4, ms=4, label=f"線 {T:g}倍" + ("（採用）" if T == 1.5 else ""))
ax.set_xscale("log"); ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter()); ax.set_xticks([0.2, 0.3, 0.5, 0.7, 1, 1.5, 2, 3], ["0.2倍", "0.3", "0.5", "0.7", "1", "1.5", "2", "3倍"])
ax.axvline(1, color="#ccc", lw=1)
ax.set_xlabel("汚れで売上・客数・点数が何倍になったか（0.5＝半分しか入らない、2＝2回足し込み）"); ax.set_ylabel("見つけた割合（%）")
ax.set_title("半分・2倍なら9割以上見つかるが、2〜3割の欠けや増えはほとんど見えない", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9, loc="center right"); ax.set_ylim(-3, 103); ax.grid(axis="y", color="#eee")
save(fig, "fig3_detect_by_factor.png")

# 図4：カレンダーの月ごとの誤報（1か月あたり）
C = pd.read_csv(RES / "C_false_alarms_by_calendar_month.csv", dtype={"cal_month": str})
order = ["04", "05", "06", "07", "08", "09", "10", "11", "12", "01", "02", "03"]
fig, ax = plt.subplots(figsize=(9, 4.4))
w = 0.27
for k, (mode, col) in enumerate(zip(["a", "ab", "abc"], [GRAY, BLUE, RED])):
    x = C[C["mode"] == mode].set_index("cal_month").reindex(order)
    v = x.pos3_flags + x.waste_flags
    ax.bar(np.arange(12) + (k - 1) * w, v, w, color=col, label=names[mode])
    ax.text(8 + (k - 1) * w, v.iloc[8] + 1, f"{v.iloc[8]:.1f}", ha="center", fontsize=8.5, color=col)
ax.set_xticks(range(12), [f"{int(o)}月" for o in order]); ax.set_ylabel("汚れのない月に鳴った数（1か月あたり）\n売上・客数・点数の店×日＋廃棄")
ax.set_title("誤報はほぼ12月だけ。年末（12/28〜31）のにぎわいを「ふだんと違う」と読んでしまう", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", color="#eee")
save(fig, "fig4_false_alarms_by_month.png")

# 図6：速報（締めの日）で、行の欠け（未着）がどれだけ出るか
G = pd.read_csv(RES / "G_sokuho_vs_kakutei.csv")
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1.25, 1]})
ax = axs[0]
for k, col in zip([1, 3, 5, 10], [RED, ORANGE, BLUE, AQUA]):
    x = G[G.close_day == k]
    ax.plot(range(12), x.pending_Q02, "o-", color=col, ms=4, label=f"翌月{k}日の締め")
ax.set_xticks(range(12), [f"{int(m[5:])}月" for m in G[G.close_day == 1].month], fontsize=8.5)
ax.set_ylabel("速報で「行の欠け」になった店×日"); ax.set_title("速報の欠けは、ほぼすべて未着（確定では0）", loc="left", fontsize=11.5)
ax.legend(frameon=False, fontsize=8.5); ax.grid(axis="y", color="#eee")
ax = axs[1]
g = G.groupby("close_day")[["pending_Q02", "Q08_sokuho"]].mean()
xx = np.arange(len(g))
ax.bar(xx, g.pending_Q02, 0.55, color=BLUE)
for i, a in enumerate(g.pending_Q02):
    ax.text(i, a + 0.1, f"{a:.1f}", ha="center", fontsize=9.5)
ax.set_ylim(0, g.pending_Q02.max() * 1.25)
ax.set_xticks(xx, [f"{k}日" for k in g.index]); ax.set_xlabel("締めの日（翌月）"); ax.set_ylabel("未着で保留した店×日（1か月あたり）")
ax.set_title("締めの日ごとの平均（FY2025）\n部門の合計の不一致は、どの締めでも0", loc="left", fontsize=11)
save(fig, "fig6_sokuho_pending.png")
print("figs done")

# 図5：1枚のチェック表（HTML を画像に）
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1240, "height": 900}, device_scale_factor=1.5)
    pg.goto((ROOT / "reports" / "dq_2025-12_確定_見本.html").as_uri()); pg.wait_for_timeout(500)
    pg.locator("body").screenshot(path=str(FIG / "fig5_monthly_check_sheet.png")); br.close()
print("fig5 done")
