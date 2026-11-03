"""04 図と、3本の結論の判定表（results/verdict.csv）"""
from common import *
import json

# ---- 判定表：元記事の主張 × 作り直した結果
a = pd.read_csv(RES / "a_summary.csv", index_col=0).value
b = pd.read_csv(RES / "b_summary.csv", index_col=0).value
c = pd.read_csv(RES / "c_summary.csv", index_col=0).value
V = [
 ("008 人の流入と所得", "所得の係数は、条件をそろえると0と区別できない", "一部変わった",
  f"基本の形では変わらず（クラスタ標準誤差で p={float(a.full_p_cluster):.2f}）。ただし512通りのうち{float(a.spec_neg_sig)*100:.0f}%ではっきりマイナス、"
  f"標本・定義を変えた4通りのうち{int(float(a.variants_n_sig))}通りではっきりマイナス"),
 ("008 人の流入と所得", "残ったのは大卒の割合と人口密度", "同じ（書き漏れあり）",
  f"大卒は入れた指定の{float(a.univ_pos_sig_share)*100:.0f}%、人口密度は{float(a.density_pos_sig_share)*100:.0f}%ではっきりプラス。単独世帯の割合（マイナス）も元の結果表で有意だったが、要約に書いていなかった"),
 ("019 似た街のグループ", "5つのグループに分かれる", "変わった",
  f"標本を入れ替えると k=5 は2〜9の中で安定性が低い側（ARI の中央値 {float(b.k5_boot_ari_median):.2f}）。別の手法との一致は ARI {float(b.alt_ari_min):.2f}〜{float(b.alt_ari_max):.2f}"),
 ("019 似た街のグループ", "乱数の種を変えても結果はほぼ同じ（ARI 0.95）", "変わった",
  f"種ではなく標本を替えると ARI の中央値 {float(b.boot_ari_median):.2f}。都道府県で半分に分けて当てると {float(b.half_ari_median):.2f}"),
 ("019 似た街のグループ", "境目はあいまい（シルエット係数 0.3未満）", "同じ",
  f"ギャップ統計は k=2〜9 のどこでも止まらず、いちばん近い中心と2番目の差が10%未満の町が{float(b.share_margin_lt10)*100:.0f}%"),
 ("020 失業率の予測", "1〜12か月先のどこでも SARIMA が単純な予測より誤差が小さい", "同じ（差の確かさは弱め）",
  f"平均誤差の並びは12か月とも同じ。ただし差がはっきりしたのは「最新の値のまま」に対して{int(float(c.dm_sig_vs_naive_excl))}か月分、「前年同月＋前年差」に対して{int(float(c.dm_sig_vs_snaivedrift_excl))}か月分"),
 ("020 失業率の予測", "（比べていなかった）指数平滑法（ETS）", "新しく分かった",
  f"全期間では SARIMA が12か月とも平均で小さいが、はっきりした差は0か月分。2022年以降が予測先だと ETS のほうが{12-int(float(c.claim_h_2022_vs_ets))}か月分で小さい"),
 ("020 失業率の予測", "（書いていなかった）予測区間", "新しく分かった",
  f"80%予測区間に実際が入った割合は平均{float(c.cov80_mean)*100:.0f}%、95%区間は{float(c.cov95_mean)*100:.0f}%（コロナ期を除く）。区間は広すぎた"),
 ("020 失業率の予測", "次数は2014年までの AIC で決めて固定", "同じ",
  f"毎年選び直すと11年中{int(float(c.n_changed_orders))}年で次数が変わったが、誤差の差は0.003ポイント以内"),
]
V = pd.DataFrame(V, columns=["article", "original_claim", "verdict", "detail"]); V.to_csv(RES / "verdict.csv", index=False, encoding="utf-8-sig")
print(V[["article", "verdict"]])

# ---- 図1：008 の specification curve
sp = pd.read_csv(RES / "a_spec_curve.csv").sort_values("coef").reset_index(drop=True)
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9, 5.6), height_ratios=[3, 1.3], sharex=True)
col = np.where((sp.p < .05) & (sp.coef > 0), ORANGE, np.where((sp.p < .05) & (sp.coef < 0), BLUE, GRAY))
ax.vlines(sp.index, sp.lo, sp.hi, color=col, alpha=.25, lw=.8); ax.scatter(sp.index, sp.coef, c=col, s=6, zorder=3)
ax.axhline(0, color=INK, lw=.8)
base = sp[(sp.n_ctrl == 6) & sp.fe & (sp.weight == "なし") & (sp.y == "net_mig")].index[0]
ax.annotate("元記事の最後の形", (base, sp.coef[base]), xytext=(base - 160, sp.coef[base] + 2.2), arrowprops=dict(arrowstyle="->", color=INK, lw=.8), fontsize=9)
ax.set_ylabel("所得 1標準偏差あたりの\n転入超過（1,000人あたり）")
ax.set_title(f"条件の組み合わせ512通り：はっきりマイナス{(sp.coef.lt(0)&sp.p.lt(.05)).mean()*100:.0f}%、はっきりプラス{(sp.coef.gt(0)&sp.p.lt(.05)).mean()*100:.0f}%", loc="left")
for i, (k, lab) in enumerate([("old_in", "65歳以上の割合を入れる"), ("c_univ", "大卒の割合を入れる"), ("w", "人口で重みづけ")]):
    m = sp[k] if k != "w" else sp.weight.eq("人口")
    ax2.scatter(sp.index[m], np.full(m.sum(), i), s=2, color=INK, marker="|")
ax2.set_yticks(range(3), ["65歳以上の割合を入れる", "大卒の割合を入れる", "人口で重みづけ"], fontsize=9); ax2.set_ylim(-.6, 2.6)
ax2.set_xlabel("512通りの指定（係数の小さい順）"); ax2.spines["left"].set_visible(False)
fig.text(0.01, -0.02, SRC_MUNI + "／元記事 008 のデータ。都道府県でクラスタした標準誤差。青＝はっきりマイナス、橙＝はっきりプラス", fontsize=7.5, color="#8a8984")
fig.savefig(FIG / "fig1_spec_curve.png"); plt.close(fig)

# ---- 図2：008 元の結果と、標準誤差・標本を変えた結果
st = pd.read_csv(RES / "a_steps_reproduce.csv"); vr = pd.read_csv(RES / "a_variants.csv")
rows = [("元記事（HC3）", *st.query("step=='＋ほかの条件すべて' and se=='HC3'")[["coef", "lo", "hi", "p"]].values[0])]
rows += [(r.variant.replace("基本（フル・クラスタ）", "都道府県でクラスタした標準誤差"), r.coef, r.lo, r.hi, r.p) for r in vr.itertuples()]
t = pd.DataFrame(rows, columns=["name", "coef", "lo", "hi", "p"])
fig, ax = plt.subplots(figsize=(8.5, 3.6)); yy = np.arange(len(t))[::-1]
for yi, r in zip(yy, t.itertuples()):
    cc = BLUE if r.p < .05 else GRAY
    ax.hlines(yi, r.lo, r.hi, color=cc, lw=2.5); ax.scatter(r.coef, yi, color=cc, s=40, zorder=3)
    ax.text(0.7, yi, f"{r.coef:+.2f}" + ("" if r.p < .05 else "（はっきりしない）"), va="center", fontsize=9)
ax.axvline(0, color=INK, lw=.8); ax.set_yticks(yy, t.name); ax.set_xlim(-3.2, 1.9)
ax.set_xlabel("所得 1標準偏差あたりの転入超過（1,000人あたり）")
ax.set_title("008：すべての条件をそろえた形でも、標本を変えるとマイナスに寄る", loc="left")
fig.text(0.01, -0.06, SRC_MUNI + "／95%区間。灰色は0をまたぐ", fontsize=8, color="#8a8984"); fig.savefig(FIG / "fig2_migration_variants.png"); plt.close(fig)

# ---- 図3：019 k ごとのシルエットと安定性
ks = pd.read_csv(RES / "b_k_choice.csv")
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.plot(ks.k, ks.boot_ari_median, marker="o", color=BLUE, label="標本を入れ替えたときの一致（ARI の中央値）")
ax.fill_between(ks.k, ks.boot_ari_p10, ks.boot_ari_median, color=LIGHT, alpha=.5)
ax.plot(ks.k, ks.silhouette, marker="s", color=ORANGE, label="シルエット係数")
ax.axhline(0.949, color=GRAY, ls="--", lw=1); ax.text(9.2, 0.90, "元記事の\n「種を変えた ARI」\n0.95", fontsize=8, va="top", color="#52514e")
ax.axvline(5, color=GRAY, ls=":"); ax.set_ylim(0, 1.05); ax.set_xlim(1.8, 10.3); ax.set_xlabel("グループの数 k")
ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_title("019：k=5 は、標本を入れ替えると崩れやすい側だった", loc="left")
fig.text(0.01, -0.05, SRC_MUNI + "／k ごとに復元抽出50回。帯は下から10%点〜中央値", fontsize=8, color="#8a8984"); fig.savefig(FIG / "fig3_cluster_k.png"); plt.close(fig)

# ---- 図4：019 グループごとの再現（Jaccard）
bj = pd.read_csv(RES / "b_bootstrap_jaccard.csv", index_col=0); al = pd.read_csv(RES / "b_alternatives.csv").set_index("variant")
G = list(bj.index); H = pd.concat([bj[["jaccard_mean"]].T.rename(index={"jaccard_mean": "標本の入れ替え（200回の平均）"}), al[G].iloc[1:]])
fig, ax = plt.subplots(figsize=(9, 4.3)); im = ax.imshow(H.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(G)), G, rotation=20, ha="right", fontsize=9); ax.set_yticks(range(len(H)), H.index, fontsize=9)
for i in range(H.shape[0]):
    for j in range(H.shape[1]):
        ax.text(j, i, f"{H.values[i, j]:.2f}", ha="center", va="center", fontsize=8.5, color="white" if H.values[i, j] > .6 else INK)
for sp_ in ax.spines.values(): sp_.set_visible(False)
fig.colorbar(im, ax=ax, pad=.01).set_label("元のグループとの重なり（Jaccard）")
ax.set_title("019：元の5グループは、手法や前処理を変えるとどれも半分ほどしか重ならない", loc="left")
fig.text(0.01, -0.12, SRC_MUNI + "／0.75未満は「形は見えるが安定しない」、0.5以下は「崩れた」と読むことが多い（Hennig 2007）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "fig4_cluster_jaccard.png"); plt.close(fig)

# ---- 図5：020 期間を分けた平均誤差
p1 = pd.read_csv(RES / "c_mae_by_h_2015_2019.csv", index_col=0); p2 = pd.read_csv(RES / "c_mae_by_h_2022plus.csv", index_col=0)
fig, axs = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
for ax, (tt, df) in zip(axs, [("予測先が2015〜2019年", p1), ("予測先が2022年以降", p2)]):
    for m, lab, cc, ls in [("sarima", "SARIMA（元記事）", BLUE, "-"), ("ets", "指数平滑法（ETS、今回追加）", GREEN, "-"),
                           ("naive_last", "最新の値のまま", GRAY, "--"), ("snaive_drift", "前年同月＋前年差", ORANGE, "--")]:
        ax.plot(df.index, df[m], marker="o", ms=3, color=cc, ls=ls, label=lab)
    ax.set_title(tt, fontsize=11, loc="left"); ax.set_xlabel("何か月先の予測か"); ax.set_xticks(range(1, 13))
axs[0].set_ylabel("平均絶対誤差（ポイント）"); axs[0].set_ylim(0, None); axs[1].legend(frameon=False, fontsize=8.5, loc="upper left")
fig.suptitle("020：2022年以降は、比べていなかった指数平滑法のほうが小さい月が多い", x=0.01, y=1.02, ha="left", fontsize=13)
fig.text(0.01, -0.04, SRC_LFS + "／元記事と同じローリング評価（コロナ期を除く）", fontsize=8, color="#8a8984"); fig.savefig(FIG / "fig5_unemp_periods.png"); plt.close(fig)

# ---- 図6：3本の判定のまとめ
COL = {"同じ": "#cfe3f7", "同じ（書き漏れあり）": "#cfe3f7", "同じ（差の確かさは弱め）": "#e6eef7", "一部変わった": "#fde2c8", "変わった": "#f8c4a8", "新しく分かった": "#e9e1f6"}
fig, ax = plt.subplots(figsize=(10.5, 4.6)); ax.axis("off")
for i, r in enumerate(V.itertuples()):
    yv = len(V) - i
    ax.add_patch(plt.Rectangle((0.0, yv - .45), 1.0, .9, color=COL[r.verdict], lw=0))
    ax.text(0.01, yv, r.article, fontsize=9, va="center", color="#52514e")
    ax.text(0.21, yv, r.original_claim, fontsize=9.5, va="center")
    ax.text(0.76, yv, r.verdict, fontsize=10, va="center", weight="bold")
ax.set_xlim(0, 1); ax.set_ylim(.4, len(V) + .9)
ax.text(0.01, len(V) + .65, "元記事", fontsize=9, color="#8a8984"); ax.text(0.21, len(V) + .65, "元の主張", fontsize=9, color="#8a8984"); ax.text(0.76, len(V) + .65, "作り直した結果", fontsize=9, color="#8a8984")
ax.set_title("3本・9つの点を作り直すと：同じ2、同じだが弱め・書き漏れ2、変わった3、新しく分かった2", loc="left", fontsize=12)
fig.text(0.01, 0.0, "出典：e-Stat の市区町村データ・労働力調査を加工（元記事 008・019・020 のデータ）", fontsize=8, color="#8a8984")
fig.savefig(FIG / "fig6_verdict.png"); plt.close(fig)
print(V.verdict.value_counts())
