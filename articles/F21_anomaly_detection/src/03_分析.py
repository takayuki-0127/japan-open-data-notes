"""03 分析：STL 残差の z スコア → 系列ごとの異常、Isolation Forest → 月ごとの異常、PELT → 変化点、出来事年表との答え合わせ、頑健性"""
from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
from detect import stl_robust_z, flag, isolation_scores, change_points

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
THR = 4.0

# 出来事の年表（答え合わせ用）。expect は「この出来事なら動くはずの系列」
EVENTS = [
    ("2008-10", "2009-03", "リーマン・ショック後の生産の急減", "景気", ["景気:鉱工業生産", "景気:生産財出荷", "景気:投資財出荷", "景気:輸出数量", "景気:耐久消費財出荷"]),
    ("2010-04", "2010-04", "高校授業料の実質無償化", "制度", ["物価:授業料等"]),
    ("2010-09", "2010-10", "たばこ税の大幅な引き上げ（駆け込みと値上げ）", "制度", ["物価:たばこ", "家計:たばこ"]),
    ("2011-03", "2011-04", "東日本大震災", "災害", ["景気:鉱工業生産", "景気:生産財出荷", "景気:耐久消費財出荷", "景気:消費者態度指数", "景気:輸出数量"]),
    ("2014-03", "2014-04", "消費税8%（駆け込みと反動）", "制度", ["家計:家事用耐久財", "家計:冷暖房用器具", "家計:教養娯楽用耐久財", "家計:自動車等購入", "景気:耐久消費財出荷", "景気:小売販売額（前年比）"]),
    ("2018-01", "2018-01", "家計調査の家計簿の改正", "統計の変更", [k for k in []]),
    ("2019-09", "2019-10", "消費税10%・幼児教育の無償化", "制度", ["家計:家事用耐久財", "家計:冷暖房用器具", "家計:教養娯楽用耐久財", "景気:耐久消費財出荷", "景気:小売販売額（前年比）", "物価:補習教育", "物価:授業料等"]),
    ("2020-03", "2020-06", "新型コロナの感染拡大と緊急事態宣言", "感染症", ["家計:一般外食", "家計:宿泊料", "家計:パック旅行費", "景気:鉱工業生産", "景気:輸出数量", "景気:消費者態度指数", "景気:新規求人数", "景気:労働投入量"]),
    ("2020-04", "2020-04", "高等教育の修学支援（授業料減免）", "制度", ["物価:授業料等"]),
    ("2020-08", "2021-01", "Go To トラベル（割引の開始と停止）", "制度", ["物価:教養娯楽サービス", "家計:宿泊料", "家計:パック旅行費"]),
    ("2021-04", "2021-04", "携帯電話の通信料の値下げ", "制度", ["物価:通信"]),
    ("2022-10", "2022-10", "全国旅行支援の開始", "制度", ["物価:教養娯楽サービス"]),
    ("2023-02", "2023-02", "電気・ガス代の負担軽減策の開始", "制度", ["物価:電気代", "物価:ガス代"]),
    ("2024-05", "2024-06", "電気・ガス代の負担軽減策の縮小・終了", "制度", ["物価:電気代", "物価:ガス代"]),
]
# 2018-01 の家計簿の改正は、家計調査のすべての系列が対象
EVENTS[5] = (*EVENTS[5][:4], None)


def months(a, b, pad=1):
    s, e = pd.Timestamp(a) - pd.DateOffset(months=pad), pd.Timestamp(b) + pd.DateOffset(months=pad)
    return pd.date_range(s, e, freq="MS")


def build_z(ch, seasonal=13, robust=True):
    return pd.DataFrame({c: stl_robust_z(ch[c], seasonal=seasonal, robust=robust) for c in ch.columns})


def evaluate(F, pad=1):
    """F: 月×系列の True/False。出来事ごとに「期待した系列のどれかに印が付いたか」（再現率）と、印のうち出来事の窓に入る割合。"""
    rows, in_any = [], pd.DataFrame(False, index=F.index, columns=F.columns)
    for a, b, lab, cat, exp in EVENTS:
        win = months(a, b, pad).intersection(F.index)
        cols = [c for c in F.columns if c.startswith("家計:")] if exp is None else [c for c in exp if c in F.columns]
        hit = F.loc[win, cols]
        found = hit.any().any()
        rows.append(dict(start=a, end=b, event=lab, category=cat, detected=bool(found),
                         n_series_flagged=int(hit.any().sum()), n_expected=len(cols),
                         flagged=";".join(sorted(hit.columns[hit.any()].str.split(":").str[1]))))
        in_any.loc[win, cols] = True
    ev = pd.DataFrame(rows)
    nflag = int(F.values.sum())
    explained = int((F & in_any).values.sum())
    # 「何かの出来事の窓（どの系列でもよい）」に入る印
    allwin = pd.DatetimeIndex(sorted(set().union(*[months(a, b, pad) for a, b, *_ in EVENTS]))).intersection(F.index)
    in_window_any = int(F.loc[allwin].values.sum())
    return ev, dict(recall=ev.detected.mean(), n_flags=nflag, explained_by_expected=explained,
                    share_explained=explained / max(nflag, 1), share_in_event_months=in_window_any / max(nflag, 1),
                    event_months_share=len(allwin) / len(F.index))


def main():
    ch = pd.read_csv(ROOT / "data" / "changes.csv", parse_dates=["month"], index_col="month")
    Z = build_z(ch)
    Z.to_csv(RES / "z_scores.csv", float_format="%.3f")
    F = flag(Z, THR)
    ev, summ = evaluate(F)
    ev.to_csv(RES / "events_check.csv", index=False)

    # 印の一覧（大きい順）
    st = Z.stack().rename("z").reset_index().rename(columns={"level_1": "series"})
    st = st[st.z.abs() > THR].assign(absz=lambda d: d.z.abs()).sort_values("absz", ascending=False)
    st.to_csv(RES / "flags_stl_thr4.csv", index=False, float_format="%.2f")

    # 月ごと：印の付いた系列の数と、Isolation Forest のスコア
    breadth = F.sum(axis=1)
    iso = isolation_scores(Z, seed=0)
    iso_seeds = pd.concat([isolation_scores(Z, seed=s) for s in range(5)], axis=1)
    monthly = pd.DataFrame({"n_flagged": breadth, "iso_score": iso, "iso_rank": iso.rank(ascending=False).astype(int)})
    ev_months = set().union(*[months(a, b, 1) for a, b, *_ in EVENTS])
    monthly["in_event_window"] = monthly.index.isin(list(ev_months))
    monthly.to_csv(RES / "monthly_scores.csv", float_format="%.4f")
    top = monthly.sort_values("iso_score", ascending=False).head(15).copy()
    # 上位の月で、z が大きかった系列（上位3つ）
    top["top_series"] = [";".join(f"{c.split(':')[1]}({Z.loc[m, c]:+.1f})" for c in Z.loc[m].abs().sort_values(ascending=False).index[:3]) for m in top.index]
    top.to_csv(RES / "top_months_isolation.csv", float_format="%.4f")
    seed_rank_corr = iso_seeds.corr(method="spearman").values[np.triu_indices(5, 1)]

    def topk_precision(score, k):
        t = score.sort_values(ascending=False).head(k).index
        return float(np.mean([m in ev_months for m in t]))

    # 変化点（季節を除いた水準）
    lv = {}
    raw_cpi = pd.read_csv(ROOT / "data" / "raw" / "cpi_chuubunrui.csv", header=None, dtype=str)
    head = raw_cpi.iloc[0].tolist(); body = raw_cpi[raw_cpi[0].str.fullmatch(r"\d{6}", na=False)]
    idx = pd.to_datetime(body[0], format="%Y%m")
    for name in ["通信", "授業料等", "電気代", "たばこ"]:
        lv[f"物価:{name}"] = np.log(pd.Series(pd.to_numeric(body[head.index(name)]).values, index=idx)).loc["2005":"2026-08"] * 100
    ci = pd.read_csv(ROOT / "data" / "raw" / "ci_monthly_levels.csv", parse_dates=["month"], index_col="month")
    lv["景気:完全失業率"] = ci["完全失業率"].loc["2005":"2026-08"]
    cps = {}
    for k, s in lv.items():
        # 物価の制度系列は季節性がほぼないので季節調整なし。失業率は季節調整済みの値だが念のため STL を通す
        bk, sa = change_points(s, deseason=k.startswith("景気"), pen_mult=4.0 if k.startswith("物価") else 20.0)
        cps[k] = [d.strftime("%Y-%m") for d in bk]
        sa.rename(k).to_frame().to_csv(RES / f"level_sa_{k.split(':')[1]}.csv", float_format="%.4f")
    json.dump(cps, open(RES / "change_points.json", "w"), ensure_ascii=False, indent=1)

    # 閾値と検出数・再現率（トレードオフ）
    trade = []
    for thr in [2.5, 3, 3.5, 4, 5, 6, 8]:
        e2, s2 = evaluate(flag(Z, thr))
        trade.append(dict(thr=thr, n_flags=s2["n_flags"], flags_per_series_year=s2["n_flags"] / Z.shape[1] / (len(Z) / 12),
                          recall=s2["recall"], share_explained=s2["share_explained"], share_in_event_months=s2["share_in_event_months"]))
    trade = pd.DataFrame(trade); trade.to_csv(RES / "threshold_tradeoff.csv", index=False, float_format="%.4f")

    # 頑健性
    rob = []
    def add(name, Zx, F_=None):
        F_ = flag(Zx, THR) if F_ is None else F_
        e2, s2 = evaluate(F_)
        rob.append(dict(setting=name, n_flags=s2["n_flags"], recall=s2["recall"], share_explained=s2["share_explained"],
                        share_in_event_months=s2["share_in_event_months"],
                        iso_top15_in_event=topk_precision(isolation_scores(Zx), 15)))
    add("基本（STL seasonal=13・robust・閾値4）", Z)
    add("STL seasonal=7", build_z(ch, seasonal=7))
    add("STL seasonal=25", build_z(ch, seasonal=25))
    add("STL robust=False", build_z(ch, robust=False))
    zplain = ch.apply(lambda x: (x - x.median()) / (1.4826 * (x - x.median()).abs().median()))
    add("STL なし（変化をそのまま頑健z）", zplain)
    for src, lab in [("物価:", "物価だけ"), ("景気:", "景気動向指数の系列だけ"), ("家計:", "家計調査だけ")]:
        Zs = Z[[c for c in Z.columns if c.startswith(src)]]
        add(lab, Zs)
    rng = np.random.default_rng(0)
    for i in range(3):
        cols = rng.choice(Z.columns, size=len(Z.columns) // 2, replace=False)
        add(f"系列を半分だけ無作為に（{i+1}回目）", Z[cols])
    rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")

    # 偶然の基準：同じ数の印を月にランダムに置いたときの「出来事の窓に入る割合」
    p_base = len(set(ev_months).intersection(Z.index)) / len(Z.index)

    out = dict(n_series=Z.shape[1], n_months=Z.shape[0], period=f"{Z.index[0]:%Y-%m}〜{Z.index[-1]:%Y-%m}",
               thr=THR, **{k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in summ.items()},
               random_baseline_share_in_event_months=p_base,
               iso_top15_in_event=topk_precision(iso, 15), iso_top30_in_event=topk_precision(iso, 30),
               breadth_top15_in_event=topk_precision(breadth + iso * 1e-6, 15),
               iso_seed_rank_corr_min=float(seed_rank_corr.min()),
               change_points=cps)
    json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps({k: v for k, v in out.items() if k != "change_points"}, ensure_ascii=False, indent=1, default=float))
    print(ev[["start", "event", "detected", "n_series_flagged", "n_expected", "flagged"]].to_string())
    print(top[["n_flagged", "iso_score", "in_event_window", "top_series"]].to_string())
    print(trade.to_string()); print(rob.to_string()); print(cps)


if __name__ == "__main__":
    main()
