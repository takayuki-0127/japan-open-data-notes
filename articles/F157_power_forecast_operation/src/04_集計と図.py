"""04 集計と図：1年の運用で、再学習の間隔ごとの外れ方・モデルの古さ・ピークの上限の当たり方をまとめる"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, CACHE
import pickle

FIG.mkdir(exist_ok=True)
MAIN = ["固定（開始前に1回）", "四半期ごと", "毎月", "毎週", "監視ルールで"]
COL = {"固定（開始前に1回）": "#d93025", "四半期ごと": "#f29900", "毎月": "#1a73e8", "毎週": "#188038",
       "監視ルールで": "#9334e6", "1週間前の同じ時刻": "#9aa0a6"}


def load(name):
    P = pd.read_csv(RES / f"pred_{name}.csv.gz", index_col=0, parse_dates=True)
    meta = json.load(open(RES / f"retrain_{name}.json"))
    return P, meta


def summary(P, meta, label):
    a = P["actual"]; day = P.index.normalize(); rows = []
    pa = a.groupby(day).max()
    for c in P.columns[1:]:
        e = P[c] - a; ape = e.abs() / a
        dm = 100 * ape.groupby(day).mean()
        pp = P[c].groupby(day).max()
        rows.append({"設定": label, "モデル・再学習": c, "学習の回数": meta.get(c, 0),
                     "MAPE(%)": 100 * ape.mean(), "RMSE(MW)": np.sqrt((e ** 2).mean()),
                     "ピークのMAPE(%)": 100 * ((pp - pa).abs() / pa).mean(),
                     "ずれの平均(%)": 100 * (e / a).mean(),
                     "日ごとMAPEの95%点(%)": dm.quantile(0.95), "いちばん外れた日(%)": dm.max(),
                     "MAPE3%超の日数": int((dm > 3).sum())})
    return pd.DataFrame(rows)


def monthly(P, cols):
    a = P["actual"]; m = P.index.to_period("M")
    return pd.DataFrame({c: (100 * (P[c] - a).abs() / a).groupby(m).mean() for c in cols})


def monthly_bias(P, cols):
    a = P["actual"]; m = P.index.to_period("M")
    return pd.DataFrame({c: (100 * (P[c] - a) / a).groupby(m).mean() for c in cols})


if __name__ == "__main__":
    P, meta = load("main")
    S = [summary(P, meta, "東京・2025年10月〜2026年9月（基本）")]
    for nm, lab in [("kansai", "関西・2025年10月〜2026年9月"), ("prev", "東京・2024年10月〜2025年9月")]:
        try:
            Q, mq = load(nm); S.append(summary(Q, mq, lab))
        except FileNotFoundError:
            print("まだない:", nm)
    S = pd.concat(S); S.to_csv(RES / "summary.csv", index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 20)
    print(S.round(3).to_string())

    mm = monthly(P, MAIN + ["1週間前の同じ時刻", "固定・1年前に学習したまま", "固定・2年前に学習したまま", "固定・3年前に学習したまま"])
    mm.to_csv(RES / "monthly_mape.csv"); print(mm.round(2))
    mb = monthly_bias(P, MAIN + ["固定・1年前に学習したまま", "固定・2年前に学習したまま", "固定・3年前に学習したまま"])
    mb.to_csv(RES / "monthly_bias.csv"); print(mb.round(2))

    # 再学習で差が出た月（毎月 − 固定）の、ブロック・ブートストラップの区間（日を週ごとにまとめて引き直す）
    a = P["actual"]; day = P.index.normalize()
    dm = pd.DataFrame({c: 100 * ((P[c] - a).abs() / a).groupby(day).mean() for c in P.columns[1:]})
    dm.to_csv(RES / "daily_mape.csv")
    rng = np.random.default_rng(42)
    wk = (np.arange(len(dm)) // 7)
    rows = []
    for c in P.columns[2:]:
        if c == "固定（開始前に1回）": continue
        diff = (dm[c] - dm["固定（開始前に1回）"]).values
        blocks = [diff[wk == w] for w in np.unique(wk)]
        bs = [np.mean(np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])) for _ in range(2000)]
        rows.append({"モデル・再学習": c, "固定との差(ポイント)": diff.mean(), "95%区間・下": np.percentile(bs, 2.5), "95%区間・上": np.percentile(bs, 97.5),
                     "固定より良かった日の割合(%)": 100 * (diff < 0).mean()})
    D = pd.DataFrame(rows); D.to_csv(RES / "diff_vs_fixed.csv", index=False); print(D.round(3).to_string())

    # ピークの上限（95%）：点予測（毎月の再学習）× (1 + q)。q の決め方を3通り比べる
    yr1 = pickle.load(open(CACHE / "tokyo_light_20241001_20260930_exp_0.pkl", "rb"))  # 1年前に学習したモデル
    from importlib import import_module
    d = import_module("03_運用の再現").load("tokyo")
    bt = yr1.loc["2024-10-01":"2025-09-30 23:00"]
    bday = bt.index.normalize()
    bt_rel = (d.loc[bt.index, "demand"].groupby(bday).max() / bt.groupby(bday).max() - 1)  # 実績÷予測 − 1
    pk_p = P["毎月"].groupby(day).max(); pk_a = a.groupby(day).max()
    rel = pk_a / pk_p - 1
    def season(ix):
        m = pd.DatetimeIndex(ix).month
        return np.where(np.isin(m, [7, 8, 9]), "夏", np.where(np.isin(m, [12, 1, 2]), "冬", "その他"))
    q_all = bt_rel.quantile(0.95)
    q_sea = bt_rel.groupby(season(bt_rel.index)).quantile(0.95)
    hist = pd.concat([bt_rel, rel])
    q_roll = pd.Series([hist.loc[:dte - pd.Timedelta(days=1)].iloc[-90:].quantile(0.95) for dte in rel.index], index=rel.index)
    U = pd.DataFrame({"実績÷予測−1": rel,
                      "1年分で1つの幅": q_all,
                      "季節ごとの幅": pd.Series(season(rel.index), index=rel.index).map(q_sea),
                      "直近90日で毎日更新": q_roll})
    for c in ["1年分で1つの幅", "季節ごとの幅", "直近90日で毎日更新"]:
        U[c + "_収まった"] = (U["実績÷予測−1"] <= U[c]).astype(int)
    U.to_csv(RES / "peak_upper_daily.csv")
    cov = U.groupby(U.index.to_period("M"))[[c for c in U.columns if c.endswith("_収まった")]].mean() * 100
    cov.loc["1年"] = U[[c for c in U.columns if c.endswith("_収まった")]].mean() * 100
    wid = U[["1年分で1つの幅", "季節ごとの幅", "直近90日で毎日更新"]].mean() * 100
    cov.to_csv(RES / "peak_upper_coverage.csv"); wid.to_csv(RES / "peak_upper_width.csv")
    print("q_all", round(q_all * 100, 2), "q_sea", (q_sea * 100).round(2).to_dict()); print(cov.round(1)); print(wid.round(2))

    # ---------------- 図 ----------------
    # 図1：月ごとの MAPE
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = np.arange(len(mm)); labs = [f"{p.year % 100}/{p.month}" for p in mm.index]
    for c in MAIN:
        ax.plot(x, mm[c], marker="o", ms=4, lw=1.8 if c != "固定（開始前に1回）" else 2.4, color=COL[c], label=f"{c}（{meta[c]}回）")
    ax.set_xticks(x, labs); ax.set_ylabel("MAPE（%）"); ax.set_ylim(0, None)
    ax.set_title("図1 再学習の間隔ごとの月別の外れ方（東京・翌日24時間の予測）")
    ax.legend(fontsize=8.5, ncol=2); ax.grid(alpha=.3)
    fig.text(0.01, 0.01, "1週間前の同じ時刻をそのまま使った場合の年間 MAPE は %.2f%%。気温は実測で代用" % (100 * ((P["1週間前の同じ時刻"] - a).abs() / a).mean()), fontsize=8, color="#555")
    fig.tight_layout(rect=(0, .03, 1, 1)); fig.savefig(FIG / "fig1_monthly_mape.png", dpi=150); plt.close()

    # 図2：学習の回数と年間の MAPE
    fig, ax = plt.subplots(figsize=(8, 4.6))
    mk = {"東京・2025年10月〜2026年9月（基本）": "o", "関西・2025年10月〜2026年9月": "s", "東京・2024年10月〜2025年9月": "^"}
    for lab, g in S.groupby("設定", sort=False):
        g = g[g["モデル・再学習"].isin(MAIN)].sort_values("学習の回数")
        ax.plot(g["学習の回数"], g["MAPE(%)"], marker=mk.get(lab, "o"), lw=1.4, label=lab)
        if lab.endswith("（基本）"):
            for _, r in g.iterrows():
                ax.annotate(r["モデル・再学習"], (r["学習の回数"], r["MAPE(%)"]), textcoords="offset points", xytext=(4, 5), fontsize=8)
    ax.set_xscale("log"); ax.set_xlabel("1年間に学習した回数（対数）"); ax.set_ylabel("1年間の MAPE（%）")
    ax.set_title("図2 学習し直す回数を増やすと、外れ方はどれだけ減るか"); ax.legend(fontsize=8.5); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(FIG / "fig2_retrain_count.png", dpi=150); plt.close()

    # 図3：モデルの古さ
    ages = ["固定（開始前に1回）", "固定・1年前に学習したまま", "固定・2年前に学習したまま", "固定・3年前に学習したまま"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.3), gridspec_kw={"width_ratios": [1, 1.6]})
    vals = [100 * ((P[c] - a).abs() / a).mean() for c in ages]
    axs[0].bar(range(4), vals, color=["#1a73e8", "#7baaf7", "#aecbfa", "#d2e3fc"])
    for i, v in enumerate(vals): axs[0].text(i, v + .03, f"{v:.2f}%", ha="center", fontsize=9)
    axs[0].set_xticks(range(4), ["直前", "1年前", "2年前", "3年前"]); axs[0].set_xlabel("学習した時点（運用開始から見て）"); axs[0].set_ylabel("1年間の MAPE（%）")
    for i, c in enumerate(ages):
        axs[1].plot(x, mb[c], marker="o", ms=3.5, color=["#1a73e8", "#7baaf7", "#a0b8e0", "#c5cfe0"][i], lw=1.6, label=["直前", "1年前", "2年前", "3年前"][i])
    axs[1].axhline(0, color="k", lw=.8); axs[1].set_xticks(x, labs, fontsize=8); axs[1].set_ylabel("ずれの平均（予測−実績、%）")
    axs[1].legend(fontsize=8, title="学習した時点", title_fontsize=8); axs[1].grid(alpha=.3)
    fig.suptitle("図3 古いモデルを使い続けると、どう外れるか（東京）"); fig.tight_layout(); fig.savefig(FIG / "fig3_model_age.png", dpi=150); plt.close()

    # 図4：日ごとの外れ方と、監視ルールが学習し直した日
    fig, axs = plt.subplots(2, 1, figsize=(9.5, 5.6), sharex=True)
    r14 = dm["固定（開始前に1回）"].rolling(14, min_periods=1).mean()
    b = pd.DataFrame({c: 100 * ((P[c] - a) / a).groupby(day).mean() for c in ["固定（開始前に1回）", "監視ルールで"]})
    axs[0].plot(dm.index, dm["固定（開始前に1回）"], color="#d93025", alpha=.3, lw=.8)
    axs[0].plot(dm.index, r14, color="#d93025", lw=1.8, label="固定：直近14日の平均")
    axs[0].plot(dm.index, dm["監視ルールで"].rolling(14, min_periods=1).mean(), color="#9334e6", lw=1.6, label="監視ルール：直近14日の平均")
    axs[0].axhline(2.0, color="#555", ls="--", lw=.8); axs[0].set_ylabel("日ごとの MAPE（%）"); axs[0].legend(fontsize=8)
    axs[1].plot(b.index, b["固定（開始前に1回）"].rolling(7, min_periods=1).mean(), color="#d93025", lw=1.6, label="固定：直近7日のずれ")
    axs[1].plot(b.index, b["監視ルールで"].rolling(7, min_periods=1).mean(), color="#9334e6", lw=1.4, label="監視ルール：直近7日のずれ")
    axs[1].axhline(0, color="k", lw=.8); axs[1].axhspan(-1, 1, color="#eee"); axs[1].set_ylabel("ずれ（予測−実績、%）"); axs[1].legend(fontsize=8)
    for t in meta["_trigger_dates"][1:]:
        for ax in axs: ax.axvline(pd.Timestamp(t), color="#9334e6", lw=.8, ls=":")
    axs[0].set_title("図4 毎日の外れ方と、監視ルールが学習し直した日（点線）")
    fig.tight_layout(); fig.savefig(FIG / "fig4_daily_monitor.png", dpi=150); plt.close()

    # 図5：ピークの95%上限に収まった割合（月別）
    cm = cov.drop("1年")
    fig, ax = plt.subplots(figsize=(9, 4.3))
    for c, col in zip(["1年分で1つの幅", "季節ごとの幅", "直近90日で毎日更新"], ["#5f6368", "#f29900", "#1a73e8"]):
        ax.plot(range(len(cm)), cm[c + "_収まった"], marker="o", ms=4, color=col, lw=1.7, label=f"{c}（1年で{cov.loc['1年', c + '_収まった']:.1f}%、平均の上乗せ{wid[c]:.1f}%）")
    ax.axhline(95, color="k", ls="--", lw=.8); ax.set_xticks(range(len(cm)), [f"{p.year % 100}/{p.month}" for p in cm.index])
    ax.set_ylabel("上限に収まった日の割合（%）"); ax.set_ylim(50, 102); ax.legend(fontsize=8.5); ax.grid(alpha=.3)
    ax.set_title("図5 翌日ピークの「95%の上限」は、月ごとにどれだけ収まったか（東京・毎月の再学習）")
    fig.tight_layout(); fig.savefig(FIG / "fig5_peak_upper.png", dpi=150); plt.close()
    print("figs done")

    # 図6：頑健性（固定との差、ブロック・ブートストラップの95%区間）
    def diffs(P, pairs):
        a = P["actual"]; day = P.index.normalize()
        dmx = pd.DataFrame({c: 100 * ((P[c] - a).abs() / a).groupby(day).mean() for c in P.columns[1:]})
        wk = np.arange(len(dmx)) // 7; out = []
        rng = np.random.default_rng(42)
        for lab, c, base in pairs:
            if c not in dmx or base not in dmx: continue
            diff = (dmx[c] - dmx[base]).values
            blocks = [diff[wk == w] for w in np.unique(wk)]
            bs = [np.mean(np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])) for _ in range(2000)]
            out.append((lab, diff.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)))
        return out
    F = "固定（開始前に1回）"
    rows = []
    sets = [("東京・基本", "main"), ("関西", "kansai"), ("東京・1年前の期間", "prev")]
    for sl, nm in sets:
        try:
            Q, _ = load(nm)
        except FileNotFoundError:
            continue
        for lab, c in [("毎月", "毎月"), ("毎週", "毎週"), ("監視ルール", "監視ルールで"), ("1年前のモデルのまま", "固定・1年前に学習したまま"), ("2年前のモデルのまま", "固定・2年前に学習したまま")]:
            for r in diffs(Q, [(lab, c, F)]):
                rows.append({"設定": sl, "比べたもの": r[0], "固定との差": r[1], "下": r[2], "上": r[3]})
    for r in diffs(P, [("毎月（気温に誤差）", "毎月（気温に誤差）", "固定（気温に誤差）"), ("線形回帰を毎日", "線形回帰・毎日", "線形回帰・固定"),
                       ("毎月・直近3年だけ", "毎月・直近3年だけで学習", F)]):
        rows.append({"設定": "東京・別の条件", "比べたもの": r[0], "固定との差": r[1], "下": r[2], "上": r[3]})
    RB = pd.DataFrame(rows); RB.to_csv(RES / "robustness_diff.csv", index=False); print(RB.round(3).to_string())
    fig, ax = plt.subplots(figsize=(9, 6.2))
    cols6 = {"東京・基本": "#1a73e8", "関西": "#188038", "東京・1年前の期間": "#f29900", "東京・別の条件": "#5f6368"}
    yl = []
    for i, r in RB.iloc[::-1].reset_index(drop=True).iterrows():
        ax.errorbar(r["固定との差"], i, xerr=[[r["固定との差"] - r["下"]], [r["上"] - r["固定との差"]]], fmt="o", color=cols6[r["設定"]], capsize=3)
        yl.append(f"{r['設定']}｜{r['比べたもの']}")
    ax.set_yticks(range(len(yl)), yl, fontsize=8.5); ax.axvline(0, color="k", lw=.8)
    ax.set_xlabel("1年間の MAPE の差（ポイント、マイナスなら固定より良い）")
    ax.set_title("図6 再学習の効果は、地域・期間・条件を変えても小さいか（基準：開始前に1回学習して固定）", fontsize=10)
    ax.grid(alpha=.3, axis="x"); fig.tight_layout(); fig.savefig(FIG / "fig6_robustness.png", dpi=150); plt.close()
    print("fig6 done")
