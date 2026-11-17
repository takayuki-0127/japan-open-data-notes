"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省「貿易取引通貨別比率」「貿易統計」、日本銀行「外国為替相場」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.read_csv(R / "jpy_share.csv").set_index("half")
x = np.array([int(h[:4]) + (0.25 if h.endswith("H1") else 0.75) for h in t.index])

# 図1 世界の円・ドルの割合（輸出・輸入）
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, t.WORLD, color=C[1], lw=2.4, label="輸出：円建て")
ax.plot(x, t.usd_WORLD, color=C[0], lw=2.0, label="輸出：ドル建て")
ax.plot(x, t.imp_jpy_WORLD, color=C[1], lw=1.4, ls="--", label="輸入：円建て")
ax.set_ylim(0, 80); ax.set_ylabel("契約の通貨の割合（%、半期）")
ax.legend(frameon=False, loc="upper right", fontsize=9, ncol=3)
style(ax)
ax.set_title(f"輸出の円建ては25年で{m['world_min']:.0f}〜{m['world_max']:.0f}%、平均{m['world_mean']:.1f}%。2026年上半期は{m['world_last']:.1f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig1_world_shares.png", SRC, "注：2000年下半期〜2026年上半期。")

# 図2 地域別の円建ての割合
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for a, lab, c, ls in [("ASIA", "アジア向け", C[1], "-"), ("OTHER", "その他の地域向け（逆算）", C[5], ":"), ("EU", "EU 向け", C[2], "-"), ("USA", "米国向け", C[0], "-")]:
    ax.plot(x, t[a], color=c, lw=2.0, ls=ls, label=lab)
    ax.text(x[-1] + 0.3, t[a].iloc[-1], f"{t[a].iloc[-1]:.0f}", fontsize=9, color=c, va="center")
ax.set_xlim(2000, 2027.5); ax.set_ylim(0, 60)
ax.set_ylabel("輸出の円建ての割合（%）")
ax.legend(frameon=False, loc="lower left", fontsize=9, ncol=2)
style(ax)
ax.set_title(f"アジア向けは{m['asia_first']:.0f}%→{m['asia_last']:.0f}%、EU 向けは{m['eu_first']:.0f}%→{m['eu_last']:.0f}%、米国向けは1割台のまま", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.14)
save(fig, F / "fig2_area_shares.png", SRC, "注：その他の地域は、世界の割合と3地域の割合・輸出額から逆算した目安。EU の加盟国は期間中に変わった（英国は2020年に離脱）。")

# 図3 シフト・シェア
fig, ax = plt.subplots(1, 2, figsize=(9.6, 4.6), gridspec_kw={"width_ratios": [1.1, 1]})
vals = [m["ss_total"], m["ss_within"], m["ss_composition"]]
ax[0].bar(["世界の変化", "地域の中の\n割合の変化", "地域の構成\nの変化"], vals, color=[INK2, C[1], C[0]])
for i, v in enumerate(vals):
    ax[0].text(i, v + (0.2 if v >= 0 else -0.5), f"{v:+.1f}", ha="center", fontsize=9.5)
ax[0].axhline(0, color=INK2, lw=0.8); ax[0].set_ylabel("ポイント（2000年下半期→2026年上半期）"); ax[0].set_ylim(-7.5, 6.5); style(ax[0])
ax[1].plot(x, t.w_ASIA * 100, color=C[1], lw=2, label="アジア")
ax[1].plot(x, t.w_USA * 100, color=C[0], lw=2, label="米国")
ax[1].plot(x, t.w_EU * 100, color=C[2], lw=2, label="EU")
ax[1].set_ylabel("輸出額に占める割合（%）"); ax[1].legend(frameon=False, fontsize=9); style(ax[1]); ax[1].set_ylim(0, 65)
fig.suptitle("地域の中では円建てが減ったが、円建ての多いアジアへの輸出が増えて打ち消した", x=0.01, ha="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.17, wspace=0.35)
save(fig, F / "fig3_shift_share.png", SRC)

# 図4 ドル円の変化と円の割合の変化
s = t.WORLD / 100
dl = np.log(t.usdjpy).diff() * 100
act = s.diff() * 100
ok = dl.notna() & act.notna()
fig, ax = plt.subplots(figsize=(7.8, 5.6))
ax.scatter(dl[ok], act[ok], color=C[1], s=28)
xx = np.linspace(dl[ok].min(), dl[ok].max(), 10)
ax.plot(xx, q["slope_actual"] * xx / 100, color=C[1], lw=1.6, label=f"実際の傾き（{q['slope_actual']:.1f}）")
ax.plot(xx, q["slope_mechanical"] * xx / 100, color=INK2, lw=1.4, ls="--", label=f"計算の上の効果だけの傾き（{q['slope_mechanical']:.1f}）")
ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
ax.set_xlabel("ドル円の半期平均の変化（%、対数×100、正は円安）")
ax.set_ylabel("輸出の円建ての割合の変化（ポイント）")
ax.legend(frameon=False, loc="upper right", fontsize=9)
style(ax)
ax.set_title("円安の半期は円建ての割合が下がるが、計算の上の効果の半分ほど", loc="left", fontsize=12)
fig.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.17)
save(fig, F / "fig4_fx_effect.png", SRC, "注：計算の上の効果：外貨建ての契約の円換算額がドル円とともに膨らむ分。傾きは Δlog(ドル円)1 あたりのポイント。")
