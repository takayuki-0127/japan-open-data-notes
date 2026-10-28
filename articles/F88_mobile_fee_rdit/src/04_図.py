import json
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import DATA, RES, FIG, EVENT, EVENT2, plt
s = pd.read_csv(DATA / "cpi_monthly.csv", index_col=0); s.index = pd.PeriodIndex(s.index, freq="M")
L = 100 * np.log(s); S = json.load(open(RES / "summary.json"))
ev = pd.Period(EVENT, "M"); ev2 = pd.Period(EVENT2, "M")
ts = lambda idx: idx.to_timestamp()

# 1 通信の指数
fig, ax = plt.subplots(figsize=(9, 4.6))
x = s.loc["2015-01":]
ax.plot(ts(x.index), x["通信"], color="#1f5fa8", lw=2, label="通信（携帯電話通信料などを含む）")
ax.plot(ts(x.index), x["総合"], color="#888", lw=1.5, label="総合")
for p, t, ha, yy in [(ev, "2021年4月 大幅値下げ ", "right", 92), (ev2, " 2021年10月 2回目", "left", 85)]:
    ax.axvline(p.to_timestamp(), color="#c0392b", ls="--", lw=1); ax.text(p.to_timestamp(), yy, t, color="#c0392b", fontsize=9, ha=ha, va="center")
ax.set_ylabel("指数（2020年=100）"); ax.set_title("消費者物価指数の「通信」は2021年4月に24%下がった", fontsize=12)
ax.legend(loc="lower left", fontsize=9); ax.set_ylim(60, 118); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f88_comm_index.png", dpi=150); plt.close()

# 2 RDiT の図（通信とコアコア）
def fitline(series, pre=24, post=6):
    y = series.loc[ev - pre: ev + post - 1]; r = np.array([(p - ev).n for p in y.index], float); D = (r >= 0) * 1.0
    X = sm.add_constant(np.column_stack([D, r, D * r])); b = sm.OLS(y.values, X).fit().params
    return y, r, b
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
for ax, c, t in [(axes[0], "通信", "通信"), (axes[1], "生鮮食品及びエネルギーを除く総合", "生鮮食品とエネルギーを除く総合")]:
    y, r, b = fitline(L[c])
    base = y.iloc[np.where(r == -1)[0][0]]
    ax.scatter(r, y - base, s=18, color="#333")
    rp = np.linspace(-24, -0.01, 50); rq = np.linspace(0, 5, 20)
    ax.plot(rp, b[0] + b[2] * rp - base, color="#1f5fa8", lw=2); ax.plot(rq, b[0] + b[1] + (b[2] + b[3]) * rq - base, color="#c0392b", lw=2)
    ax.axvline(-0.5, color="#999", ls=":")
    j = S[f"base_{c}"]
    ax.set_title(f"{t}：段差 {j['jump']:.2f}（95%区間 {j['lo']:.2f}〜{j['hi']:.2f}）", fontsize=10.5)
    ax.set_xlabel("2021年4月からの月数"); ax.set_ylabel("2021年3月との差（対数×100 約 %）"); ax.grid(alpha=.3)
fig.suptitle("時間の回帰不連続：2021年4月の前後に直線を当てはめ、境目の段差を測る", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f88_rdit.png", dpi=150); plt.close()

# 3 寄与度
cc = pd.read_csv(RES / "contribution_monthly.csv", index_col=0); cc.index = pd.PeriodIndex(cc.index, freq="M")
cc = cc.loc["2019-01":"2024-12"]
fig, ax = plt.subplots(figsize=(9.5, 4.6))
ax.bar(ts(cc.index), cc["通信_寄与_コア"], width=25, color="#1f5fa8", label="通信の寄与")
ax.plot(ts(cc.index), cc["コア_前年比"], color="#c0392b", lw=2, label="生鮮食品を除く総合（前年比）")
ax.plot(ts(cc.index), cc["コア_通信除く"], color="#c0392b", lw=1.5, ls="--", label="通信の寄与を除いた場合")
ax.axhline(0, color="#333", lw=.8)
ax.set_ylabel("％・ポイント"); ax.set_title("値下げは1年間、物価の前年比を約1.4ポイント押し下げ、2022年4月に消えた", fontsize=12)
ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f88_contrib.png", dpi=150); plt.close()

# 4 プラセボ
pl = pd.read_csv(RES / "placebo.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, c, key, t in [(axes[0], "総合", "base_総合", "総合"), (axes[1], "コアコア", "base_生鮮食品及びエネルギーを除く総合", "生鮮食品とエネルギーを除く総合")]:
    ax.hist(pl[c], bins=40, color="#bbb", edgecolor="white")
    a = S[key]["jump"]; ax.axvline(a, color="#c0392b", lw=2); ax.text(a, ax.get_ylim()[1] * .9, f" ← 2021年4月 {a:.2f}", color="#c0392b", fontsize=9, ha="left")
    share = (pl[c].abs() >= abs(a)).mean() * 100
    ax.set_title(f"{t}\n同じ大きさ以上の段差が出た月：{share:.0f}%", fontsize=10)
    ax.set_xlabel("「境」を置いた月の段差（対数×100）"); ax.set_ylabel("月数")
fig.suptitle("プラセボ：2003〜2020年の各月を境にしたときの段差の分布（右の山は2014年の消費増税）", fontsize=11.5)
fig.tight_layout(); fig.savefig(FIG / "f88_placebo.png", dpi=150); plt.close()

# 5 頑健性
rob = pd.read_csv(RES / "robustness.csv")
series = [("総合", "総合", "implied_総合_jump_pct"), ("生鮮食品を除く総合", "生鮮食品を除く総合", "implied_生鮮食品を除く総合_jump_pct"),
          ("生鮮食品及びエネルギーを除く総合", "生鮮食品とエネルギーを除く総合", "implied_生鮮食品及びエネルギーを除く総合_jump_pct")]
fig, axes = plt.subplots(1, 3, figsize=(12, 4.6), sharey=True)
specs = [x for x in rob.spec.unique() if x != "情報通信関係費で測る"]
for ax, (c, t, imp) in zip(axes, series):
    d = rob[rob.series == c].set_index("spec").loc[specs]
    yy = np.arange(len(d))[::-1]
    ax.errorbar(d.jump, yy, xerr=[d.jump - d.lo, d.hi - d.jump], fmt="o", color="#1f5fa8", capsize=3)
    ax.axvline(S[imp], color="#c0392b", ls="--", lw=1.5, label="ウエイトから見込まれる段差")
    ax.axvline(0, color="#333", lw=.8); ax.set_title(t, fontsize=10.5); ax.grid(alpha=.3)
    ax.set_yticks(yy); ax.set_yticklabels(d.index, fontsize=9)
fig.legend(*axes[0].get_legend_handles_labels(), loc="lower right", fontsize=9); fig.supxlabel("2021年4月の段差（対数×100 約 %）と95%区間", fontsize=10)
fig.suptitle("設定を変えた段差：コアコアは見込みに近いが、総合・コアは設定で大きく揺れる", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f88_robust.png", dpi=150); plt.close()
print("ok")
