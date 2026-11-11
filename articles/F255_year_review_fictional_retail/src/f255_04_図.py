# F255 04 図：fig1〜fig5（fig6 は 05 で報告を画像にする）
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(f).exists():
        fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
HERE = Path(__file__).resolve().parents[1]
RES = HERE / "results"; FIG = HERE / "figures"; FIG.mkdir(exist_ok=True)
BLUE, GRAY, RED, ORANGE = "#2b6cb0", "#a0aec0", "#c53030", "#dd6b20"

# ---- fig1 1年の地図（何を作り、前の回の何を使ったか）
C = pd.read_csv(RES / "C_code_audit.csv", encoding="utf-8-sig")
work = {"F246": ("KPI を決める", "KPI 定義書・会社設定書"), "F247": ("データを整える", "データマート・テスト"),
        "F248": ("月次レポートの型", "毎月の報告の雛形"), "F249": ("ダッシュボード", "3ページの設計・Power BI 一式"),
        "F250": ("売上が落ちた月の説明", "1枚の報告"), "F251": ("販促の効果を測る", "効果測定の報告"),
        "F252": ("来期の予算", "予測と予算案"), "F253": ("データの品質チェック", "チェックのスクリプト"),
        "F254": ("引き継げる形にする", "引き継ぎ資料"), "F255": ("1年の振り返り", "この記事")}
fig, ax = plt.subplots(figsize=(10, 6.2))
arts = list(work)
for i, a in enumerate(arts):
    y = len(arts) - 1 - i
    ax.text(0.0, y, a, fontsize=11, weight="bold", va="center")
    ax.text(0.9, y, work[a][0], fontsize=11, va="center")
    ax.text(4.3, y, work[a][1], fontsize=10, va="center", color="#4a5568")
    row = C[C.回 == a]
    for j, col in enumerate(["F246に依存_コミットか関数", "F247に依存_コミットか関数"]):
        x = 7.6 + j * 1.3
        if a in ("F254", "F255"):
            ax.text(x, y, "−", ha="center", va="center", color=GRAY)
        elif a == "F246" and j == 1:
            ax.text(x, y, "−", ha="center", va="center", color=GRAY)
        elif (a == "F246" and j == 0) or (a == "F247" and j == 1):
            ax.text(x, y, "作った回", ha="center", va="center", fontsize=8, color=GRAY)
        elif len(row) and row[col].iloc[0] == 1:
            ax.scatter([x], [y], s=120, color=BLUE)
        else:
            ax.scatter([x], [y], s=120, facecolor="white", edgecolor=GRAY)
ax.text(7.6, len(arts) - 0.2, "F246 の\n合成データ", ha="center", fontsize=9)
ax.text(8.9, len(arts) - 0.2, "F247 の\nデータマート", ha="center", fontsize=9)
ax.set_xlim(-0.1, 9.6); ax.set_ylim(-0.7, len(arts) + 0.6); ax.axis("off")
ax.set_title("架空のスーパーの1年：何を作り、前の回の何を使ったか（●＝コードで使っている）", fontsize=12, loc="left")
fig.tight_layout(); fig.savefig(FIG / "fig1_year_map.png", dpi=150); plt.close(fig)

# ---- fig2 素朴なやり方と採用したやり方
A = pd.read_csv(RES / "A_before_after.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(11, 5.8))
for i, r in A.iloc[::-1].reset_index(drop=True).iterrows():
    ax.plot([r.素朴, r.採用], [i, i], color=GRAY, lw=2, zorder=1)
    ax.scatter([r.素朴], [i], s=90, color=GRAY, zorder=2)
    ax.scatter([r.採用], [i], s=90, color=BLUE, zorder=3)
    ax.text(r.素朴, i + 0.28, f"{r.素朴:.0f}%  {r.素朴なやり方}", ha="center", fontsize=8.5, color="#4a5568")
    ax.text(r.採用, i - 0.38, f"{r.採用:.0f}%  {r.採用したやり方}", ha="center", fontsize=8.5, color=BLUE)
    ax.text(-6, i, f"{r.回} {r.仕事}（{r.向き}）\n{r.ものさし}", ha="right", va="center", fontsize=8.5)
ax.axvline(80, ls=":", color=ORANGE, lw=1); ax.text(80, -0.75, "予算の目標 80%", color=ORANGE, fontsize=8, ha="center")
ax.set_xlim(-5, 112); ax.set_ylim(-0.9, len(A) - 0.2); ax.set_yticks([])
ax.set_xlabel("%（灰色＝素朴なやり方、青＝採用したやり方）")
ax.set_title("6つの仕事で、素朴なやり方と採用したやり方を同じものさしで比べる（架空の会社）", fontsize=12, loc="left")
fig.subplots_adjust(left=0.36, right=0.97, top=0.9, bottom=0.11)
fig.savefig(FIG / "fig2_before_after.png", dpi=150); plt.close(fig)

# ---- fig3 同じ偶然の幅を何度も測った
B = pd.read_csv(RES / "B_noise_bands.csv", encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4))
for ax, q in zip(axes, ["全社・月・売上の前年比", "1店・月・売上の前年比"]):
    d = B[B.量 == q].reset_index(drop=True)
    for i, r in d.iterrows():
        if r["幅の取り方（%）"] == 90:
            ax.scatter([i], [r["書いた値"]], marker="x", color=ORANGE, s=60, zorder=3)
        ax.scatter([i], [r["95%に直した値"]], color=BLUE, s=80, zorder=4)
        ax.text(i, r["95%に直した値"] * 1.015, f"±{r['95%に直した値']:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(range(len(d))); ax.set_xticklabels(d.回)
    lo, hi = d["95%に直した値"].min(), d["95%に直した値"].max()
    ax.set_ylim(min(d["書いた値"].min(), lo) * 0.85, hi * 1.12)
    ax.set_title(f"{q}\n（95%に直すと最大÷最小 {hi / lo:.2f}倍）", fontsize=10.5)
    ax.set_ylabel("偶然の幅（±%）")
axes[1].scatter([], [], color=BLUE, label="95% の幅（90% は ×1.96/1.645 で直した）")
axes[1].scatter([], [], color=ORANGE, marker="x", label="記事に書いた 90% の幅")
axes[1].legend(fontsize=8, loc="lower right")
fig.suptitle("同じ「偶然の幅」を4つの回で測り直していた。値はそろっていたが、90% と 95% が混ざっていた", fontsize=11.5, x=0.02, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(FIG / "fig3_noise_bands.png", dpi=150); plt.close(fig)

# ---- fig4 予算の答え合わせとモデルの順位
D = pd.read_csv(RES / "D_budget_check_rank.csv", encoding="utf-8-sig")
N = pd.read_csv(HERE / "data/processed/numbers.csv").set_index("id")["値"]
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.axvspan(N.F252_check_lo, N.F252_check_hi, color=BLUE, alpha=0.12)
ax.text((N.F252_check_lo + N.F252_check_hi) / 2, -0.62, f"見直しの線 {N.F252_check_lo:+.1f}〜{N.F252_check_hi:+.1f}%", ha="center", fontsize=9, color=BLUE)
ax.axvline(0, color="#4a5568", lw=0.8)
for i, r in D.iloc[::-1].reset_index(drop=True).iterrows():
    c = RED if "予算に使った" in r.モデル else GRAY
    ax.barh(i, r["2026年4〜8月の差（%）"], color=c, height=0.55)
    ax.text(r["2026年4〜8月の差（%）"] - 0.05, i, f"{r['2026年4〜8月の差（%）']:+.2f}%", ha="right", va="center", fontsize=9)
    ax.text(0.15, i, f"過去の外れ {r.iloc[1]:.2f}%（{r.過去の順位}位）→ 答え合わせ {r.答え合わせの順位}位", va="center", fontsize=9)
ax.set_yticks(range(len(D))); ax.set_yticklabels(D.モデル.iloc[::-1], fontsize=9)
ax.set_xlim(-3.4, 3.0); ax.set_xlabel("2026年4〜8月の売上累計の、予算との差（%）")
ax.set_ylim(-0.8, len(D) - 0.5)
fig.suptitle("予算の答え合わせ（1回だけ）：5か月で見直しの線の外に出た。\n過去にいちばん外れたモデルが、今回はいちばん近かった", fontsize=11.5, x=0.02, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.88)); fig.savefig(FIG / "fig4_budget_check.png", dpi=150); plt.close(fig)

# ---- fig5 コードの点検
m = json.loads((RES / "main.json").read_text(encoding="utf-8"))["C"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw=dict(width_ratios=[1.4, 1]))
ax = axes[0]
ax.bar(C.回, C.行数, color=GRAY)
for i, r in C.iterrows():
    ax.text(i, r.行数 + 20, f"{r.スクリプト}本", ha="center", fontsize=8.5)
ax.set_ylabel("コードの行数"); ax.set_title(f"8回で {m['scripts']} 本・{m['lines']:,} 行", fontsize=10.5)
ax = axes[1]
items = [("合成データを\n作る・作り直す回", m["regen_synthetic"], 8), ("偶然の幅を\n自分で計算する回", m["noise_band_code"], 8),
         ("版を固定した\nrequirements の行", m["pinned"], m["pinned"] + m["floor_only"])]
for i, (lab, v, tot) in enumerate(items):
    ax.barh(i, 100, color="#edf2f7"); ax.barh(i, v / tot * 100, color=BLUE if i < 2 else RED)
    ax.text(102, i, f"{v}/{tot}", va="center", fontsize=10)
ax.set_yticks(range(3)); ax.set_yticklabels([x[0] for x in items], fontsize=9); ax.invert_yaxis()
ax.set_xlabel("%")
ax.set_xlim(0, 120); ax.set_title("同じ処理の繰り返しと、版の固定", fontsize=10.5)
fig.suptitle("コードの点検：同じ仕事を回ごとに書き直し、ライブラリの版は1行も固定していなかった", fontsize=11.5, x=0.02, ha="left")
fig.tight_layout(rect=(0, 0, 1, 0.92)); fig.savefig(FIG / "fig5_code_audit.png", dpi=150); plt.close(fig)
print("figs ok")
