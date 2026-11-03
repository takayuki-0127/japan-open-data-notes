"""04 図：results/ の数字から図を5枚つくる。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    try:
        fm.fontManager.addfont(f)
    except Exception:
        pass
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
H9 = ["<1", "1-3", "3-5", "5-10", "10-20", "20-30", "30-50", "50-100", "100+"]
LAB9 = ["1ha未満", "1〜3", "3〜5", "5〜10", "10〜20", "20〜30", "30〜50", "50〜100", "100ha以上"]
C = dict(exit="#c0504d", up="#2e75b6", down="#9dc3e6", stay="#d9d9d9", gray="#7f7f7f")
ud = pd.read_csv(RES / "stay_up_down_exit.csv")

# 図1 規模ごとの5年後の行き先（2015→2020）
m = ud[(ud.period == "2015-2020") & (ud.classes == "H9") & (ud.exit_def == "exit+unlinked")].set_index("size").reindex(H9)
fig, ax = plt.subplots(figsize=(9, 5.2))
left = np.zeros(9)
for k, lab in (("exit", "やめた（接続不可を含む）"), ("down", "小さくなった"), ("stay", "同じ規模"), ("up", "大きくなった")):
    ax.barh(LAB9, m[k] * 100, left=left, color=C[k], label=lab, edgecolor="white")
    for i, v in enumerate(m[k] * 100):
        if v >= 6:
            ax.text(left[i] + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9, color="white" if k in ("exit", "up") else "black")
    left += m[k].values * 100
ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("2015年の経営体のうちの割合（%）")
ax.set_ylabel("2015年の経営耕地面積"); ax.legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=9)
ax.set_title("1ha未満は3軒に1軒がやめ、3ha以上はやめる割合と大きくなる割合が近い", fontsize=12, pad=28)
fig.text(0.01, 0.01, "出典：農林業センサス 2020年 構造動態編（経営耕地面積規模別経営体数の相関表、全国）を加工", fontsize=8, color=C["gray"])
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig1_destinations_2015_2020.png", dpi=150); plt.close(fig)

# 図2 やめた割合と大きくなった割合の推移（5区分、3期間）
H5 = ["<1", "1-3", "3-5", "5-10", "10+"]; LAB5 = ["1ha未満", "1〜3ha", "3〜5ha", "5〜10ha", "10ha以上"]
fig, axs = plt.subplots(1, 2, figsize=(10, 4.6), sharey=False)
cols = {"2005-2010": "#bdd7ee", "2010-2015": "#6fa8dc", "2015-2020": "#1f4e79"}
x = np.arange(5); w = 0.26
for j, (per, cc) in enumerate(cols.items()):
    s = ud[(ud.period == per) & (ud.classes == "H5") & (ud.exit_def == "exit+unlinked")].set_index("size").reindex(H5)
    axs[0].bar(x + (j - 1) * w, s.exit * 100, w, color=cc, label=per.replace("-", "→"))
    axs[1].bar(x[:4] + (j - 1) * w, s.up.iloc[:4] * 100, w, color=cc, label=per.replace("-", "→"))
axs[0].set_title("やめた割合（%）", fontsize=11); axs[1].set_title("大きくなった割合（%）", fontsize=11)
axs[0].set_xticks(x, LAB5, fontsize=9); axs[1].set_xticks(x[:4], LAB5[:4], fontsize=9)
axs[0].legend(frameon=False, fontsize=9)
fig.suptitle("小さい層ほど、やめる割合が期を追って高くなった。大きくなる割合は増えていない", fontsize=12)
fig.text(0.01, 0.01, "出典：農林業センサス 2010年・2015年・2020年 構造動態の相関表を加工。2005→2010年は北海道＋都府県。やめた＝前回の経営体のうち今回は経営体でない＋接続不可", fontsize=7.5, color=C["gray"])
fig.tight_layout(rect=(0, 0.04, 1, 0.94)); fig.savefig(FIG / "fig2_exit_up_trend.png", dpi=150); plt.close(fig)

# 図3 大きい層の入れ替わり（2015→2020）
dec = pd.read_csv(RES / "large_class_decomposition.csv"); dec = dec[dec.period == "2015-2020"].set_index("threshold")
th = ["10-20", "30-50", "100+"]; thl = ["10ha以上", "30ha以上", "100ha以上"]
fig, ax = plt.subplots(figsize=(10, 5.6))
y = np.arange(3)
for i, t_ in enumerate(th):
    r = dec.loc[t_]; s0 = r.start
    out = [("to_smaller", "小さくなって出た", C["down"]), ("exit", "やめた", C["exit"]), ("unlinked_out", "接続不可（前回側）", "#e6b8b7")]
    inn = [("from_smaller", "下の規模から上がってきた", C["up"]), ("entry", "新しく始めた", "#70ad47"), ("unlinked_in", "接続不可（今回側）", "#a9d18e")]
    lft = 0
    for k, lab, cc in out:
        v = r[k] / s0 * 100; ax.barh(i - 0.2, -v, left=-lft, height=0.35, color=cc, label=lab if i == 0 else None); lft += v
    lft = 0
    for k, lab, cc in inn:
        v = r[k] / s0 * 100; ax.barh(i + 0.2, v, left=lft, height=0.35, color=cc, label=lab if i == 0 else None); lft += v
    ax.text(57, i, f"{int(r.start):,} → {int(r.end):,}（{(r.end / r.start - 1) * 100:+.0f}%）", va="center", fontsize=10)
ax.axvline(0, color="black", lw=0.8); ax.set_yticks(y, thl); ax.invert_yaxis(); ax.set_xlim(-35, 90)
ax.set_xlabel("2015年の経営体数に対する割合（%）　左＝出ていった　右＝入ってきた")
ax.legend(ncol=3, fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13))
ax.set_title("大きい層は、出ていく数より、下から上がってくる数と接続不可の入りが多かった", fontsize=12)
fig.text(0.01, 0.01, "出典：農林業センサス 2020年 構造動態編を加工。接続不可は、法人化や経営の引き継ぎなどで前後の経営体をつなげなかったもの（推測を含む）", fontsize=7.5, color=C["gray"])
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig3_large_turnover.png", dpi=150); plt.close(fig)

# 図4 マルコフ連鎖の予測と2025年の実際
bt = pd.read_csv(RES / "markov_backtest.csv")
a = bt[(bt.case == "2020→2025（2015-20の遷移）") & (bt.entry == "前回の数に比例")].set_index("size").reindex(H9)
b = bt[(bt.case == "2020→2025（2010-15の遷移）") & (bt.entry == "前回の数に比例")].set_index("size").reindex(H9)
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.6), gridspec_kw=dict(width_ratios=[1.3, 1]))
x = np.arange(9)
axs[0].bar(x - 0.2, a.actual / 1000, 0.4, color="#7f7f7f", label="2025年の実際")
axs[0].bar(x + 0.2, a.pred / 1000, 0.4, color=C["up"], label="2015→20年の遷移で予測")
axs[0].set_yscale("log"); axs[0].set_xticks(x, LAB9, rotation=45, fontsize=8.5); axs[0].set_ylabel("経営体数（千、対数目盛）")
axs[0].legend(frameon=False, fontsize=9); axs[0].set_title("規模別の数", fontsize=11)
axs[1].plot(x, a.err_pct, "o-", color=C["up"], label="2015→20年の遷移")
axs[1].plot(x, b.err_pct, "s--", color="#f4b183", label="2010→15年の遷移")
axs[1].axhline(0, color="black", lw=0.8); axs[1].set_xticks(x, LAB9, rotation=45, fontsize=8.5)
axs[1].set_ylabel("予測の外れ（%）"); axs[1].legend(frameon=False, fontsize=9); axs[1].set_title("予測の外れ", fontsize=11)
fig.suptitle("直近の遷移を使えば、2025年の経営体数は全体で1%、10ha以上で0.2%の差で当たった", fontsize=12)
fig.text(0.01, 0.01, "出典：農林業センサス 2015年・2020年 構造動態の相関表、2025年 総括編（経営耕地面積規模別経営体数）を加工。新しく始める数は前回の数に比例すると置いた", fontsize=7.5, color=C["gray"])
fig.tight_layout(rect=(0, 0.04, 1, 0.94)); fig.savefig(FIG / "fig4_markov_backtest.png", dpi=150); plt.close(fig)

# 図5 シフトシェア（都道府県の5年残存率：規模の構成で見込んだ値と実際）
ss = pd.read_csv(RES / "shift_share_pref_2015_2020.csv")
regs = ["北海道", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州・沖縄"]
cm = plt.get_cmap("tab10")
fig, ax = plt.subplots(figsize=(7.4, 6))
for i, r in enumerate(regs):
    s = ss[ss.region == r]
    ax.scatter(s.surv_rate_mix * 100, s.surv_rate * 100, s=np.sqrt(s.n2015) / 2.2, color=cm(i), alpha=0.8, label=r, edgecolor="white")
lo, hi = 58, 86
ax.plot([lo, hi], [lo, hi], color="black", lw=0.8, ls=":")
ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
ax.set_xlabel("規模の構成だけで見込んだ5年残存率（%）"); ax.set_ylabel("実際の5年残存率（%）")
ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper left")
s = json.load(open(RES / "summary.json", encoding="utf-8"))["shift_share"]
ax.set_title(f"都道府県の残存率の差は、規模の構成ではほとんど説明できない（R²={s['r2_mix']:.2f}）", fontsize=11)
fig.text(0.01, 0.01, "出典：農林業センサス 2020年 構造動態編（都道府県別）を加工。点の大きさは2015年の経営体数。点線は見込みどおりの線", fontsize=7.5, color=C["gray"])
fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig5_shift_share.png", dpi=150); plt.close(fig)
print("ok", sorted(p.name for p in FIG.glob("*.png")))
