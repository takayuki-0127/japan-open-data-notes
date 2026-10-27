"""03 分析（実データ）：4つの見方で、景気の山・谷をどれだけ早く・どれだけ間違えずに見つけられるか
- 転換点：内閣府の景気基準日付（山・谷）
- サイン：その見方が「山のあとにマイナス」「谷のあとにプラス」に k か月続いた月（基本 k=2）
- 遅れ：転換点から何か月後にサインが出たか（転換点の月から24か月後までで探す。転換点より前から続いていたサインは、転換点の月から数える）
- 空振り：転換点から6か月以上離れた月に、局面と逆向きのサインが k か月続いた回数（10年あたり）
- 局面の一致：拡張期にプラス、後退期にマイナスだった月の割合
- 何か月前の動きを映しているか：中心化12か月移動平均（2×12）の前月比との相互相関が最大になるずれ"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, IND, SERIES, detect, false_alarms, cycle_table, phase_frame, change

K_MAIN = 2


def tp_list(ind):
    """その系列でサインを判定できる転換点（前6か月から後24か月までデータがあるもの）"""
    c = cycle_table()
    first, last = ind.dropna().index.min(), ind.dropna().index.max()
    ok = (c.date - pd.DateOffset(months=6) >= first) & (c.date + pd.DateOffset(months=12) <= last)
    return c[ok]


def run(ind_all, levels, ks=(1, 2, 3)):
    lag_rows, fa_rows, agree_rows, xc_rows, flip_rows, prof_rows = [], [], [], [], [], []
    for name, (kind, sign) in SERIES.items():
        d = ind_all[ind_all.series == name].set_index("date")[IND]
        d = d[d.index >= d["前年比"].first_valid_index()]       # 4つの見方がそろう期間に限る
        tps = tp_list(d["前年比"])
        ph = phase_frame(d.index)
        for k in ks:
            for _, tp in tps.iterrows():
                direction = -1 if tp.type == "peak" else 1
                for i in IND:
                    lag_rows.append({"series": name, "type": tp.type, "date": tp.date.strftime("%Y-%m"), "k": k,
                                     "見方": i, "遅れ": detect(d[i], tp.date, direction, k=k)})
            for i in IND:
                n, yrs = false_alarms(d[i], ph, k=k)
                fa_rows.append({"series": name, "k": k, "見方": i, "空振り": n, "年数": yrs, "10年あたり": n / yrs * 10})
        for i in IND:
            x = pd.concat([np.sign(d[i]).rename("s"), ph], axis=1).dropna()
            agree_rows.append({"series": name, "見方": i, "局面の一致率": (x.s == x.phase).mean() * 100,
                               "拡張期の一致率": (x[x.phase == 1].s == 1).mean() * 100,
                               "後退期の一致率": (x[x.phase == -1].s == -1).mean() * 100})
            s = np.sign(d[i].dropna())
            flip_rows.append({"series": name, "見方": i, "符号が変わった回数（年あたり）": (s.diff().abs() > 0).sum() / (len(s) / 12)})
        # 中心化移動平均（2×12）の前月比：あとから分かる「その月の本当の動き」の近似
        lv = levels[levels.series == name].set_index("date")["sa"]
        tr = lv.rolling(12, center=True).mean().rolling(2).mean().shift(-1)
        tg = change(tr, 1, kind) * sign
        for i in IND:
            best, cors = None, {}
            for h in range(-12, 1):     # 見方(t) と 本当の動き(t+h) の相関（過去の側だけを見る）
                c = pd.concat([d[i], tg.shift(-h)], axis=1).dropna().corr().iloc[0, 1]
                cors[h] = c
            h = max(cors, key=cors.get)
            xc_rows.append({"series": name, "見方": i, "最大の相関": cors[h], "ずれ（か月）": h,
                            "何か月前の動きか": -h, "同じ月との相関": cors[0]})
            for hh, cc in cors.items():
                prof_rows.append({"series": name, "見方": i, "h": hh, "相関": cc})
    return (pd.DataFrame(lag_rows), pd.DataFrame(fa_rows), pd.DataFrame(agree_rows),
            pd.DataFrame(xc_rows), pd.DataFrame(flip_rows), pd.DataFrame(prof_rows))


def summarize(lags, fa, k=K_MAIN):
    l = lags[lags.k == k]
    g = l.groupby("見方")["遅れ"]
    s = pd.DataFrame({"遅れの中央値": g.median(), "遅れの平均": g.mean(), "見逃し": l.assign(m=l["遅れ"].isna()).groupby("見方").m.sum(),
                      "判定した転換点": g.size()})
    for t in ["peak", "trough"]:
        s[f"遅れの中央値（{'山' if t == 'peak' else '谷'}）"] = l[l.type == t].groupby("見方")["遅れ"].median()
    f = fa[fa.k == k].groupby("見方").agg(空振り=("空振り", "sum"), 年数=("年数", "sum"))
    s["空振り（10年あたり）"] = f["空振り"] / f["年数"] * 10
    return s.reindex(IND)


if __name__ == "__main__":
    ind = pd.read_csv(DATA / "indicators.csv", parse_dates=["date"])
    levels = pd.read_csv(DATA / "levels.csv", parse_dates=["date"])
    lags, fa, agree, xc, flips, prof = run(ind, levels)
    prof.to_csv(RES / "cross_correlation_profile.csv", index=False)
    lags.to_csv(RES / "detection_lags.csv", index=False)
    fa.to_csv(RES / "false_alarms.csv", index=False)
    agree.to_csv(RES / "phase_agreement.csv", index=False)
    xc.to_csv(RES / "cross_correlation.csv", index=False)
    flips.to_csv(RES / "sign_flips.csv", index=False)
    summ = {k: summarize(lags, fa, k) for k in (1, 2, 3)}
    for k, s in summ.items():
        s.to_csv(RES / f"summary_k{k}.csv")
        print(f"--- k={k}\n", s.round(2))
    by_series = lags[lags.k == K_MAIN].groupby(["series", "見方"])["遅れ"].median().unstack().reindex(columns=IND)
    by_series.to_csv(RES / "lag_by_series_k2.csv")
    print(by_series)
    print(agree.pivot(index="series", columns="見方", values="局面の一致率")[IND].round(1))
    print(xc.pivot(index="series", columns="見方", values="何か月前の動きか")[IND])
    print(xc.pivot(index="series", columns="見方", values="最大の相関")[IND].round(2))
    print(flips.pivot(index="series", columns="見方", values="符号が変わった回数（年あたり）")[IND].round(1))
