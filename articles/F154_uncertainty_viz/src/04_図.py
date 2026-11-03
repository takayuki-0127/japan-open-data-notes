"""図をつくる（fig1〜fig6、HOP の GIF）"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from common import DATA, RES, FIG, SEED

z = np.load(DATA / "samples.npz")
BY, BS = z["births_future_years"], z["births_future"].astype(float) / 1e4     # 万人
AY, AV = z["births_actual_years"], z["births_actual"] / 1e4
EY, EF, EM = z["e0_years"], z["e0_f"].astype(float), z["e0_m"].astype(float)
C1, C2, CG = "#1f5fa8", "#d1495b", "#888888"
hist = (AY >= 2015)


def base_ax(ax, title):
    ax.plot(AY[hist], AV[hist], color="k", lw=1.8, label="実績")
    ax.axhline(60, color=C2, lw=0.8, ls="--"); ax.text(2015.2, 60.8, "60万人", color=C2, fontsize=8)
    ax.set_title(title, fontsize=11, loc="left"); ax.set_ylim(38, 105); ax.set_xlim(2014.5, 2030.8)
    ax.grid(alpha=0.25); ax.set_ylabel("出生数（万人）")


def fig1():
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.6))
    med = np.median(BS, 0); lo, hi = np.percentile(BS, [2.5, 97.5], 0)
    ax = axs[0, 0]; base_ax(ax, "① 点だけ（中央値）")
    ax.plot(np.r_[AY[-1], BY], np.r_[AV[-1], med], color=C1, lw=2, marker="o", ms=4)
    ax.text(2015.3, 44, "2030年に60万人を下回るか？\n→ 中央値が下なので「下回る」としか読めない", fontsize=8.5)
    ax = axs[0, 1]; base_ax(ax, "② 95%区間（エラーバー）")
    ax.errorbar(BY, med, yerr=[med - lo, hi - med], fmt="o", color=C1, capsize=4, ms=4)
    ax.text(2015.3, 44, "幅は分かるが、区間の中のどこが\n出やすいかは分からない", fontsize=8.5)
    ax = axs[1, 0]; base_ax(ax, "③ ファン図（50・80・95%の帯）")
    for (a, b), al in [((2.5, 97.5), 0.18), ((10, 90), 0.3), ((25, 75), 0.45)]:
        l, h = np.percentile(BS, [a, b], 0)
        ax.fill_between(np.r_[AY[-1], BY], np.r_[AV[-1], l], np.r_[AV[-1], h], color=C1, alpha=al, lw=0)
    ax.plot(np.r_[AY[-1], BY], np.r_[AV[-1], med], color=C1, lw=1.5)
    ax.text(2015.3, 44, "濃い帯ほど出やすい。\n帯の境目から確率をおおよそ読める", fontsize=8.5)
    ax = axs[1, 1]
    k = 20; dots = np.percentile(BS[:, -1], (np.arange(k) + 0.5) / k * 100)
    bins = np.arange(38, 106, 4.0); idx = np.digitize(dots, bins)
    cnt = {}
    for d, i in zip(dots, idx):
        cnt[i] = cnt.get(i, 0) + 1
        x = (bins[i - 1] + 2); y = cnt[i]
        ax.scatter(x, y, s=230, color=C2 if d < 60 else C1, edgecolor="white", zorder=3)
    ax.axvline(60, color=C2, lw=0.8, ls="--")
    ax.set_title("④ 2030年の分位点ドットプロット（20点）", fontsize=11, loc="left")
    ax.set_xlabel("2030年の出生数（万人）"); ax.set_yticks([]); ax.set_ylim(0, 7.5); ax.set_xlim(38, 100)
    nb = int((dots < 60).sum())
    ax.text(62, 6.4, f"1点＝5%。60万人より左の点は{nb}個\n→「下回る確率はおよそ{nb * 5}%」と数えられる", fontsize=8.5)
    fig.suptitle("同じ出生数の予測（F55、4,000本のシミュレーション）を4つの形で描く", fontsize=12.5, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(FIG / "fig1_four_ways.png", dpi=130); plt.close(fig)


def fig2_gif():
    rng = np.random.default_rng(SEED); idx = rng.choice(BS.shape[0], 20, replace=False)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    def draw(i):
        ax.clear(); base_ax(ax, "")
        for j in idx[:i]:
            ax.plot(np.r_[AY[-1], BY], np.r_[AV[-1], BS[j]], color=CG, lw=0.6, alpha=0.25)
        p = BS[idx[i]]
        ax.plot(np.r_[AY[-1], BY], np.r_[AV[-1], p], color=C2 if p[-1] < 60 else C1, lw=2.4, marker="o", ms=4)
        below = int((BS[idx[:i + 1], -1] < 60).sum())
        ax.set_title(f"HOP：1コマに1本の「ありうる未来」（前のコマは薄く残す）\n　{i + 1}/20コマ　2030年に60万人未満：{below}本", fontsize=10.5, loc="left")
        ax.set_ylim(38, 105)
    anim = FuncAnimation(fig, draw, frames=20)
    anim.save(FIG / "fig2_hop.gif", writer=PillowWriter(fps=1.4), dpi=85)
    draw(19); fig.savefig(FIG / "fig2_hop_last_frame.png", dpi=110); plt.close(fig)


def fig3():
    b = pd.read_csv(RES / "B_pair_comparisons.csv")
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.3), gridspec_kw=dict(width_ratios=[1, 1.35]))
    ax = axs[0]; j1, j2 = np.where(EY == 2045)[0][0], np.where(EY == 2050)[0][0]
    rng = np.random.default_rng(SEED); sel = rng.choice(EF.shape[0], 40, replace=False)
    for s in sel:
        a, c = EF[s, j1], EF[s, j2]
        ax.plot([0, 1], [a, c], color=C1 if c > a else C2, lw=0.8, alpha=0.6)
    for xx, j in [(-0.12, j1), (1.12, j2)]:
        l, m, h = np.percentile(EF[:, j], [2.5, 50, 97.5])
        ax.errorbar(xx, m, yerr=[[m - l], [h - m]], fmt="o", color="k", capsize=5)
    ax.set_xticks([0, 1], ["2045年", "2050年"]); ax.set_xlim(-0.4, 1.4); ax.set_ylabel("女性の平均寿命（年）")
    r = b[(b.example == "平均寿命・女（2025〜70年）") & (b.year1 == 2045) & (b.year2 == 2050)].iloc[0]
    ax.set_title(f"95%区間は大きく重なるが、道筋で見ると\n2050年のほうが長い確率は{r.p_later_higher_truth * 100:.0f}%（線は40本の例）", fontsize=10, loc="left")
    ax.grid(alpha=0.25)
    ax = axs[1]
    sel = [("平均寿命・女（2025〜70年）", 2045, 2046, "平均寿命・女\n2045→46年が長い"), ("平均寿命・女（2025〜70年）", 2045, 2050, "平均寿命・女\n2045→50年が長い"),
           ("平均寿命・女（2025〜70年）", 2050, 2060, "平均寿命・女\n2050→60年が長い"),
           ("出生数（2026〜30年）", 2027, 2028, "出生数\n2027→28年が減る"), ("出生数（2026〜30年）", 2029, 2030, "出生数\n2029→30年が減る")]
    lab, t, r_ = [], [], []
    for n, y1, y2, l in sel:
        rr = b[(b.example == n) & (b.year1 == y1) & (b.year2 == y2)].iloc[0]
        flip = n.startswith("出生")
        t.append((1 - rr.p_later_higher_truth if flip else rr.p_later_higher_truth) * 100)
        r_.append((1 - rr.p_read_as_independent if flip else rr.p_read_as_independent) * 100); lab.append(l)
    y = np.arange(len(lab))
    ax.barh(y + 0.2, r_, 0.38, color=CG, label="年ごとの95%区間から読んだ確率（2つの年を独立とみなす）")
    ax.barh(y - 0.2, t, 0.38, color=C1, label="道筋（シミュレーション）から数えた確率")
    for yy, a, c in zip(y, t, r_):
        ax.text(a + 1, yy - 0.2, f"{a:.0f}%", va="center", fontsize=8.5); ax.text(c + 1, yy + 0.2, f"{c:.0f}%", va="center", fontsize=8.5, color="#555")
    ax.set_yticks(y, lab, fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 112); ax.set_xlabel("確率（%）")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.45, -0.13), ncol=1, frameon=False); ax.grid(axis="x", alpha=0.25)
    ax.set_title("2つの年の比較は、年ごとの区間からは読めない", fontsize=10.5, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "fig3_pairs.png", dpi=130); plt.close(fig)


def fig4():
    c = pd.read_csv(RES / "C_band_vs_paths.csv")
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.6))
    ax = axs[0]
    lo, hi = np.percentile(EF, [2.5, 97.5], 0); med = np.median(EF, 0)
    ax.fill_between(EY, lo, hi, color=C1, alpha=0.18, lw=0, label="各年の95%の帯")
    ax.plot(EY, med, color=C1, lw=1.5)
    inside = ((EF >= lo) & (EF <= hi)).all(1)
    rng = np.random.default_rng(SEED + 3)
    for s in rng.choice(np.where(~inside)[0], 4, replace=False):
        ax.plot(EY, EF[s], color=C2, lw=0.9, alpha=0.8)
    for s in rng.choice(np.where(inside)[0], 2, replace=False):
        ax.plot(EY, EF[s], color="k", lw=0.9, alpha=0.6)
    ax.set_title("女性の平均寿命：帯の外に一度は出る道筋（赤）と\n最後まで帯の中の道筋（黒）", fontsize=10, loc="left")
    ax.set_ylabel("平均寿命（年）"); ax.grid(alpha=0.25); ax.legend(fontsize=8, loc="upper left")
    ax = axs[1]
    sty = {"平均寿命・女（2025〜70年）": (C1, "-"), "平均寿命・男（2025〜70年）": ("#6aa5e3", "--"),
           "出生数（2026〜30年）": (C2, "-"), "出生数（2020〜25年、2019年までで予測）": ("#e8949f", "--")}
    for n, g in c.groupby("example", sort=False):
        col, ls = sty[n]
        ax.plot(g.horizon_years, g.share_paths_inside95_all_years * 100, color=col, ls=ls, marker="o", ms=3.5, label=n)
    ax.axhline(95, color="k", lw=0.7, ls=":"); ax.text(30, 96, "95%（1年だけなら）", fontsize=8)
    ax.set_xscale("log"); ax.set_xticks([1, 2, 5, 10, 20, 46], ["1", "2", "5", "10", "20", "46"])
    ax.set_xlabel("見る年数（予測の最初の年から）"); ax.set_ylabel("全期間95%の帯の中にいる道筋（%）")
    ax.set_ylim(60, 100); ax.grid(alpha=0.25); ax.legend(fontsize=7.5, loc="lower left")
    ax.set_title("期間が長いほど「帯の中だけを通る未来」は少ない", fontsize=10.5, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "fig4_band_vs_paths.png", dpi=130); plt.close(fig)


def fig5():
    g = pd.read_csv(RES / "D_power_monthly_exceed.csv")
    from scipy.stats import binom
    fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.4), gridspec_kw=dict(width_ratios=[1, 1.4]))
    ax = axs[0]; ks = np.arange(0, 12)
    obs = np.array([(g.n_exceed == k).mean() for k in ks]) * 100
    exp_ = np.array([np.mean([binom.pmf(k, d, 0.05) for d in g.days]) for k in ks]) * 100
    ax.bar(ks - 0.2, exp_, 0.4, color=CG, label="外れが日ごとに独立なら")
    ax.bar(ks + 0.2, obs, 0.4, color=C1, label="実際（78か月）")
    ax.set_xlabel("1か月に95%上限を超えた日数"); ax.set_ylabel("月の割合（%）"); ax.legend(fontsize=8.5)
    ax.set_title("超えない月が多く、超える月はまとめて超える", fontsize=10.5, loc="left"); ax.grid(axis="y", alpha=0.25)
    ax = axs[1]
    col = {"夏（7〜9月）": C2, "冬（12〜2月）": C1, "その他": CG}
    xs = np.arange(len(g))
    ax.bar(xs, g.n_exceed, color=[col.get(s, CG) for s in g.season])
    ax.axhline(1.5, color="k", lw=0.7, ls=":"); ax.text(1, 1.8, "平均1.5日（30日×5%）", fontsize=8)
    tick = [i for i, m in enumerate(g.ym) if m.endswith("-04")]
    ax.set_xticks(tick, [g.ym[i][:4] + "年4月" for i in tick], fontsize=8, rotation=0)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=c_, label=s_) for s_, c_ in col.items()], fontsize=8, loc="upper right"); ax.set_ylabel("95%上限を超えた日数")
    ax.set_title("東京エリアの翌日ピーク需要：月ごとの「95%上限」超え（F92）", fontsize=10.5, loc="left"); ax.grid(axis="y", alpha=0.25)
    fig.tight_layout(); fig.savefig(FIG / "fig5_power_month.png", dpi=130); plt.close(fig)


def fig6():
    r = pd.read_csv(RES / "R_format_mae_robustness.csv")
    r = r[r.setting == "基本のしきい値（確率2〜98%の問い）"]
    cols = [("point", "点だけ"), ("interval_inside_all", "95%区間\n（中は一様・外なし）"), ("interval_uniform", "95%区間\n（中は一様）"),
            ("interval_normal", "95%区間\n（正規分布）"), ("hop20", "HOP\n20コマ"), ("hop100", "HOP\n100コマ"), ("dots20", "ドット\n20点"), ("fan", "ファン図\n（7本の境目）")]
    fig, ax = plt.subplots(figsize=(11.5, 4.6))
    ex = list(r.example); w = 0.8 / len(ex); colors = [C2, C1, "#e8949f", "#6aa5e3"]
    for i, (n, cc) in enumerate(zip(ex, colors)):
        rr = r[r.example == n].iloc[0]
        ax.bar(np.arange(len(cols)) + (i - (len(ex) - 1) / 2) * w, [rr[c] for c, _ in cols], w, color=cc, label=n)
    ax.set_xticks(np.arange(len(cols)), [l for _, l in cols], fontsize=9)
    ax.set_ylabel("確率の読みのずれ（平均、%ポイント）"); ax.set_yscale("log"); ax.set_yticks([0.5, 1, 2, 5, 10, 20], ["0.5", "1", "2", "5", "10", "20"])
    ax.grid(axis="y", alpha=0.25); ax.legend(fontsize=8, loc="upper right")
    ax.set_title("「しきい値を下回る確率」を図から読んだときのずれ（正解は4,000〜5,000本のシミュレーション）", fontsize=10.5, loc="left")
    fig.tight_layout(); fig.savefig(FIG / "fig6_format_error.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    fig1(); fig2_gif(); fig3(); fig4(); fig5()
    if (RES / "R_format_mae_robustness.csv").exists():
        fig6()
