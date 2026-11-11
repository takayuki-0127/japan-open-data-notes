"""05 図（サンプルマート（架空）、合成データ）"""
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8a8984", "axes.labelcolor": "#2b2b2b", "xtick.color": "#52514e", "ytick.color": "#52514e"})
BLUE, ORANGE, AQUA, GRAY, INK, MUTED = "#2a78d6", "#eb6834", "#1baf7a", "#a3a29d", "#0b0b0b", "#52514e"
NOTE = "サンプルマート（架空）・合成データ。会社も数字も実在しません。"


def save(fig, name):
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


def box(ax, x, y, w, h, title, body, fc="#eef4fc", ec=BLUE, gap=0.55):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h - 0.18, title, ha="center", va="top", fontsize=11, weight="bold", color=INK)
    ax.text(x + w / 2, y + h - gap, body, ha="center", va="top", fontsize=8.6, color=MUTED, linespacing=1.45)


def arrow(ax, a, b, color=MUTED):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3))


# ---- 図1 流れ ----
fig, ax = plt.subplots(figsize=(12.5, 6.2)); ax.set_xlim(0, 12.5); ax.set_ylim(0, 6.6); ax.axis("off")
src = [("POS（店×日・部門×日）", "毎朝6時台に届く。再送・遅れあり\n2024-04 店コード振り直し"),
       ("勤怠", "勤怠システムの店番\n人時・人件費が空の日あり"),
       ("廃棄登録", "店の端末から入力\n一部の店・月が千円単位"),
       ("会計（店×月）", "売上高・その他経費\n照合の基準にする")]
for i, (t, b) in enumerate(src):
    box(ax, 0.1, 5.0 - i * 1.5, 2.7, 1.25, t, b, fc="#f6f6f4", ec=GRAY)
box(ax, 3.4, 4.3, 2.4, 1.95, "対応表・補正表", "店コード（有効期間つき）\n勤怠店番・部門コード\n補正表：分析担当が足す\n（テストで見つけたもの）", fc="#fff4ec", ec=ORANGE)
box(ax, 3.4, 0.4, 2.4, 3.5, "staging（10）", "締めの時点までに届いた行\n再送は最新の1回だけ\n期間を見て店番に置き換え\n部門は元の7部門へ\n廃棄の単位を直す\n空の人時は平均で埋めて\n印をつける", fc="#eef4fc")
box(ax, 6.5, 0.4, 2.4, 3.5, "mart（20）", "店×日\n店×日×部門\n店×月（会計の経費・\n既存店の印つき）", fc="#eef4fc")
box(ax, 6.5, 4.3, 2.4, 1.95, "テスト（30）", "T01〜T09\nどれも「問題の行の数」\n0 なら合格", fc="#ecf8f3", ec=AQUA)
box(ax, 9.6, 2.4, 2.8, 2.6, "使う側", "F248 ダッシュボード\nF249 需要の予測\n（mart/ のファイルを\nそのまま読む）", fc="#f6f6f4", ec=GRAY)
for i in range(4):
    arrow(ax, (2.8, 5.62 - i * 1.5), (3.4, 2.2 + (1.5 - i) * 0.5))
arrow(ax, (4.6, 4.3), (4.6, 3.9)); arrow(ax, (5.8, 2.15), (6.5, 2.15)); arrow(ax, (7.7, 3.9), (7.7, 4.3), color=AQUA)
arrow(ax, (6.5, 5.3), (5.8, 5.3), color=ORANGE); ax.text(6.15, 5.42, "見つかったら\n補正表へ", ha="center", va="bottom", fontsize=8, color=ORANGE)
arrow(ax, (8.9, 2.15), (9.6, 3.2))
ax.text(0.1, 0.05, "SQL は SQL Server 互換の書き方（CTE・ROW_NUMBER・CASE・COALESCE）。この記事では DuckDB で実行した。　" + NOTE, fontsize=8.2, color=MUTED)
ax.set_title("図1　届いたファイルから mart までの流れ", loc="left", fontsize=13, weight="bold")
save(fig, "fig1_pipeline.png")

# ---- 図2 汚れの一覧 ----
lg = pd.read_csv(RES / "issue_log.csv")
cnt = lg.issue.value_counts()
_ps = pd.read_csv(ROOT / "data/raw_synth/pos_store_day.csv.gz", dtype={"店コード": str})
N_RENUM = int(((_ps["営業日"] >= "2024-04-01") & (_ps["店コード"] != "9999")).sum())
_pd = pd.read_csv(ROOT / "data/raw_synth/pos_dept_day.csv.gz", dtype={"店コード": str})
N_DEPT = int(_pd["部門コード"].isin([8, 9]).sum())
items = [("再送（同じ店×日が2回届く）", cnt.get("dup", 0), "店×日"),
         ("遅れて届く（3〜20日後）", cnt.get("late", 0), "店×日"),
         ("店コードの振り直し（2024-04 以降の行）", N_RENUM, "店×日"),
         ("16店の新コードが対応表にない", 366, "店×日"),
         ("トレーニング用コード 9999", cnt.get("test_store", 0), "日"),
         ("部門の付け替え・惣菜の分割（2025-04 以降）", N_DEPT, "店×日×部門"),
         ("人時・人件費が空", cnt.get("hr_null", 0), "店×日"),
         ("廃棄が千円単位（19店・3か月）", cnt.get("waste_unit", 0), "店×日×部門")]
fig, ax = plt.subplots(figsize=(10.5, 5.2))
y = np.arange(len(items))[::-1]
v = [i[1] for i in items]
ax.barh(y, v, color=BLUE, height=0.55)
for yi, (t, n, u) in zip(y, items):
    ax.text(n * 1.12, yi, f"{n:,}（{u}）", va="center", fontsize=9.5, color=INK)
ax.set_xscale("log"); ax.set_xlim(10, 200000)
ax.set_yticks(y, [i[0] for i in items]); ax.set_xlabel("汚れのある行の数（対数目盛。合成データ。全体は店×日 32,325、店×日×部門 約23万）")
ax.grid(axis="x", color="#e6e5e1"); ax.set_axisbelow(True)
ax.set_title("図2　届いたファイルに入れた8種類の汚れ（seed 0）", loc="left", fontsize=13, weight="bold")
fig.text(0.01, -0.02, "行の数の多さと、KPI への効き方は別もの（図4）。9999 は25日分だけだが、テストは5つ落ちる（図3）。" + NOTE, fontsize=8.5, color=MUTED)
save(fig, "fig2_issues.png")

# ---- 図3 シナリオ × テスト ----
C = pd.read_csv(RES / "C_scenario_tests.csv").set_index("シナリオ")
short = ["T01 重複", "T02 対応表にない店コード", "T03 部門の参照", "T04 店の参照", "T05 欠けた日", "T06 空の値", "T07 部門と店の合計", "T08 会計との照合", "T09 値の範囲"]
C.columns = short
fig, ax = plt.subplots(figsize=(12.5, 6.4))
Z = np.log10(C.values + 1)
cmap = matplotlib.colors.LinearSegmentedColormap.from_list("b", ["#ffffff", "#cfe0f6", "#6fa3e6", "#1f5fae"])
ax.imshow(Z, cmap=cmap, aspect="auto", vmin=0, vmax=5)
for i in range(C.shape[0]):
    for j in range(C.shape[1]):
        n = C.values[i, j]
        ax.text(j, i, f"{n:,}" if n else "・", ha="center", va="center", fontsize=8.8, color="white" if Z[i, j] > 3 else (INK if n else GRAY))
ax.set_xticks(range(len(short)), short, rotation=30, ha="right"); ax.set_yticks(range(len(C)), C.index)
ax.spines[:].set_visible(False); ax.tick_params(length=0)
ax.set_xticks(np.arange(-.5, len(short)), minor=True); ax.set_yticks(np.arange(-.5, len(C)), minor=True)
ax.grid(which="minor", color="white", lw=2)
ax.set_title("図3　手当てを1つ抜いたとき、どのテストが見つけるか（数字は問題の行の数、・は0）", loc="left", fontsize=13, weight="bold")
fig.text(0.01, -0.12, "どの汚れも、少なくとも1つのテストで見つかる。会計との照合（T08）がいちばん多くを拾うが、部門の付け替え・人時の空・廃棄の単位は別のテストでしか見つからない。\n" + NOTE, fontsize=8.5, color=MUTED)
save(fig, "fig3_test_matrix.png")

# ---- 図4 KPI のずれ ----
B = pd.read_csv(RES / "B_scenario_kpi.csv").set_index("シナリオ").drop(index="正しく整えたもの")
ks = [("既存店売上_FY2025_正解とのずれ", "既存店売上（FY2025）", "%", 100),
      ("既存店営業利益の前年比_正解とのずれ", "既存店営業利益の前年比", "pt", 100),
      ("全店売上_FY2025_正解とのずれ", "全店売上（FY2025）", "%", 100),
      ("既存店惣菜売上の前年比_正解とのずれ", "既存店の惣菜売上の前年比", "pt", 100)]
fig, axs = plt.subplots(1, 4, figsize=(15, 6.2), sharey=True)
LIM = 6
yy = np.arange(len(B))[::-1]
for ax, (c, t, u, mul) in zip(axs, ks):
    v = B[c].values * mul
    vc = np.clip(v, -LIM, LIM)
    ax.barh(yy, vc, color=[ORANGE if abs(x) >= 0.5 else GRAY for x in v], height=0.6)
    for yi, x, xc in zip(yy, v, vc):
        if abs(x) >= 0.05:
            lab = f"{x:+.1f}{u}" if abs(x) < 100 else f"{x:+,.0f}{u}"
            if abs(x) > LIM:
                lab = (lab + " ▶") if x > 0 else ("◀ " + lab)
            ax.text(xc + (0.15 if xc >= 0 else -0.15), yi, lab, va="center", ha="left" if xc >= 0 else "right", fontsize=8.3, color=INK)
    ax.axvline(0, color=INK, lw=0.8); ax.set_xlim(-LIM - 4.5, LIM + 4.5); ax.set_title(t + f"\n正解とのずれ（{u}）", fontsize=10.5)
    ax.grid(axis="x", color="#eeeeea"); ax.set_axisbelow(True)
axs[0].set_yticks(yy, B.index)
fig.suptitle("図4　手当てを1つ抜くと、FY2025 の KPI がどれだけ狂うか（正解＝F246 の数字）", x=0.01, ha="left", fontsize=13, weight="bold")
fig.text(0.01, -0.03, f"棒は ±{LIM} で切った（▶・◀ はその先まで伸びる）。橙は 0.5 以上ずれたもの。正しく整えたものは、営業利益の前年比が −0.02pt ずれる（空の人時を平均で埋めた分）ほかは一致。\n" + NOTE, fontsize=8.5, color=MUTED)
fig.tight_layout()
save(fig, "fig4_kpi_distortion.png")

# ---- 図5 締めの日 ----
D = pd.read_csv(RES / "D_close_day_revision.csv")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 5), gridspec_kw={"width_ratios": [1.7, 1]})
x = pd.to_datetime(D[D["締めの日"] == 5].ym)
fin = D[D["締めの日"] == 5]["既存店前年比_確定"].values * 100
a1.plot(x, fin, color=INK, lw=2, label="確定（すべて届いたあと）")
for cd, col, ls in ((1, ORANGE, "-"), (5, BLUE, "-")):
    d = D[D["締めの日"] == cd]
    a1.plot(x, d["既存店前年比_締め"].values * 100, color=col, lw=1.6, ls=ls, marker="o", ms=4, label=f"翌月{cd}日の締めの時点")
a1.axhline(0, color=GRAY, lw=0.8); a1.set_ylabel("既存店売上の前年同月比（%）"); a1.legend(fontsize=9, frameon=False)
a1.set_title("FY2025 の各月：締めの時点の数字と確定の数字", loc="left", fontsize=11)
a1.grid(axis="y", color="#eeeeea")
S = pd.read_csv(RES / "D_close_day_summary.csv")
a2.bar(S["締めの日"].astype(str) + "日", S["直り幅の絶対値_平均pt"], color=BLUE, width=0.55, label="平均")
a2.scatter(S["締めの日"].astype(str) + "日", S["直り幅の絶対値_最大pt"], color=ORANGE, s=40, zorder=3, label="最大")
for i, r in S.iterrows():
    a2.text(i, r["直り幅の絶対値_平均pt"] + 0.03, f"{r['直り幅の絶対値_平均pt']:.2f}", ha="center", va="bottom", fontsize=9)
a2.set_ylabel("あとで直る幅（pt、絶対値）"); a2.set_xlabel("締めの日（営業日の翌月）"); a2.legend(fontsize=9, frameon=False)
a2.set_title("締めの日ごとの「あとで直る幅」（12か月）", loc="left", fontsize=11)
fig.suptitle("図5　月次の締めを早くすると、遅れて届く分だけ前年比があとで動く", x=0.01, ha="left", fontsize=13, weight="bold")
fig.text(0.01, -0.04, "店×日の 2% が 3〜20日遅れて届く設定。前年同月は確定しているので、締めの時点の前年比は低めに出る。" + NOTE, fontsize=8.5, color=MUTED)
fig.tight_layout(); save(fig, "fig5_close_day.png")

# ---- 図6 mart の形 ----
fig, ax = plt.subplots(figsize=(13, 6.6)); ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
T = [(0.2, 3.3, "fact_store_day（店×日）", "キー：biz_date, store_id\nreceipts, member_receipts, items\nsales, gross_profit_before_waste\nwaste, gross_profit\nlabor_hours, labor_cost\nlabor_imputed（1＝埋めた日）\n32,325 行"),
     (4.5, 3.3, "fact_store_day_category\n（店×日×部門）", "キー：biz_date, store_id,\n　　　category_id（7部門）\nsales, gross_profit_before_waste\nwaste\n226,275 行"),
     (8.8, 3.3, "store_month（店×月）", "キー：ym, store_id\n店×日の合計＋other_cost\noperating_profit\nis_existing（既存店の印）\nlabor_imputed_days\n1,062 行"),
     (0.2, 0.2, "dim_store", "store_id, 名前（架空）, 大きさ\nopen_date, close_date ほか"),
     (3.4, 0.2, "dim_category", "category_id 1〜7\n（2025-04 以前の部門）"),
     (6.6, 0.2, "dim_date", "date, ym, fy, dow\nhol, flyer"),
     (9.8, 0.2, "dim_store_code_history", "POS の店コード → store_id\n有効期間つき（振り直しの記録）")]
for x0, y0, t, b in T:
    big = y0 > 3
    w = 4.0 if big else 3.0; h = 2.9 if big else 1.4
    box(ax, x0, y0 + (0.4 if big else 0.3), w, h, t, b, fc="#eef4fc" if big else "#f6f6f4", ec=BLUE if big else GRAY, gap=0.9 if "\n" in t else 0.55)
ax.text(0.2, 6.85, "下の dim（店・部門・日付・店コードの履歴）を store_id・category_id・date で結合して使う。会員の月次（fact_member_month）と EC の日次（fact_ec_day）は F246 のものをそのまま渡す。数字はすべて架空。", fontsize=8.6, color=MUTED, va="top")
ax.set_title("図6　F248・F249 に渡す mart の形（粒度とキー）", loc="left", fontsize=13, weight="bold")
save(fig, "fig6_mart_model.png")
print("ok")
