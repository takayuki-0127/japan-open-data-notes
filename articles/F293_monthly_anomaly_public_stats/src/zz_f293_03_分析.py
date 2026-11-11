"""F293 03 分析：本物の公的統計の月の系列に、チェック（R・M1・M2・M3）をかける。

1. 汚れのない月に、それぞれのチェックがどれだけ鳴るか（誤報）。鳴った月を出来事のカレンダーで仕分ける。
2. 正解の分かる汚れ（E1〜E9）を1か月に入れて、見つかる割合を測る。
チェックは毎月、その月より前のデータだけを使う（M2・M3 の基準と揺れの大きさ）。
"""
import json, pathlib, sys
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
OUT = BASE / "results"
OUT.mkdir(exist_ok=True)

Z = 4.0          # M2・M3 のしきい値（計画どおり）
M1T = 0.2        # 前年同月比のしきい値（対数）
WIN = 36         # 揺れの大きさ（MAD）を測る窓
FLOOR = 0.002    # 揺れの大きさの下限（計画になかった。CPI の動かない品目で 0 になるため）
REPS = {"S1": 200, "S2": 5, "S3": 200}
ERRS = ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9"]
ERRNAME = {"E1": "10倍", "E2": "10分の1", "E3": "1000倍", "E4": "0", "E5": "前月の値のまま",
           "E6": "別の系列の値", "E7": "+15%", "E8": "−15%", "E9": "+5%"}
COVID = (202003, 202109)


def ym_add(ym, k):
    y, m = divmod(ym, 100)
    n = y * 12 + (m - 1) + k
    return (n // 12) * 100 + n % 12 + 1


# ---------- 出来事のカレンダー（計画で決めたもの） ----------
GENERAL = [(201403, 201405), (201909, 201911), COVID]
ITEM_RULES = [  # (キーワード, [期間])
    (("携帯電話", "通信料（携帯"), [(202103, 202110)]),
    (("保育料", "幼稚園"), [(201910, 201911)]),
    (("授業料",), [(202004, 202005)]),
    (("宿泊料",), [(202007, 202312)]),
    (("電気代", "都市ガス代"), [(202301, 202406), (202408, 202411), (202501, 202505)]),
    (("ガソリン", "灯油"), [(202201, 202512)]),
    (("うるち米", "もち米"), [(202406, 202609)]),
    (("たばこ",), [(201810, 201810), (202010, 202010), (202110, 202110)]),
    (("ビール", "発泡酒", "清酒", "ワイン", "チューハイ", "焼酎", "ウイスキー", "酒"),
     [(202010, 202010), (202310, 202310)]),
]
S3_EXTRA = [(201801, 201801), (202501, 202501)]


def event_months(src, sid):
    rng = list(GENERAL)
    name = sid.split("|")[0]
    for keys, per in ITEM_RULES:
        if src in ("S2", "S3") and any(k in name for k in keys):
            rng += per
    if src == "S3":
        rng += S3_EXTRA
    s = set()
    for a, b in rng:  # 前後1か月まで
        m = ym_add(a, -1)
        while m <= ym_add(b, 1):
            s.add(m)
            m = ym_add(m, 1)
    return s


# ---------- チェックの部品（その月より前だけを使う） ----------
def mad_scale(v, win):
    out = np.full(len(v), np.nan)
    for t in range(len(v)):
        w = v[max(0, t - win):t]
        w = w[np.isfinite(w)]
        if len(w) >= win:
            out[t] = 1.4826 * np.median(np.abs(w - np.median(w)))
    return out


def parts(x, win=WIN):
    y = np.log(x)
    n = len(y)
    sh = lambda a, k: np.r_[np.full(k, np.nan), a[:-k]]
    yoy = y - sh(y, 12)
    g3 = (sh(yoy, 1) + sh(yoy, 2) + sh(yoy, 3)) / 3
    pred2 = sh(y, 12) + g3
    e2 = y - pred2
    sc2 = np.maximum(mad_scale(e2, win), FLOOR)
    d = y - sh(y, 1)
    s3 = d - sh(d, 12)
    sc3 = np.maximum(mad_scale(s3, win), FLOOR)
    base3 = sh(y, 1) + sh(d, 12)  # これに対するずれが s3
    return dict(y=y, pred2=pred2, sc2=sc2, base3=base3, sc3=sc3, y12=sh(y, 12), x=x, xprev=sh(x, 1))


def judge(P, t, xv, z=Z, m1=None):
    """月 t の値が xv だったときの各チェックの判定。"""
    m1 = M1T if m1 is None else m1
    r = {}
    r["R_le0"] = (not np.isfinite(xv)) or xv <= 0
    r["R_stale"] = np.isfinite(P["xprev"][t]) and xv == P["xprev"][t]
    if r["R_le0"]:
        r.update(M1=True, M2=True, M3=True)
        return r
    yv = np.log(xv)
    r["M1"] = abs(yv - P["y12"][t]) > m1
    r["M2"] = abs((yv - P["pred2"][t]) / P["sc2"][t]) > z
    r["M3"] = abs((yv - P["base3"][t]) / P["sc3"][t]) > z
    return r


def combos(r):
    R = r["R_le0"] or r["R_stale"]
    return {"R_stale": r["R_stale"], "R": R, "R_nostale": r["R_le0"], "M1": r["M1"], "M2": r["M2"], "M3": r["M3"],
            "R∪M2": R or r["M2"], "R(停止なし)∪M2": r["R_le0"] or r["M2"]}


def run(seed=0, z=Z, win=WIN, excl_covid=False, matched=False, verbose=True):
    df = pd.read_csv(BASE / "data" / "series_long.csv")
    rng = np.random.default_rng(seed)
    clean_rows, det_rows = [], []
    series = {k: g.sort_values("ym") for k, g in df.groupby(["src", "sid"])}
    by_src = {}
    for (src, sid), g in series.items():
        by_src.setdefault(src, []).append(sid)
    for (src, sid), g in series.items():
        x = g["x"].to_numpy(float)
        ym = g["ym"].to_numpy(int)
        P = parts(x, win)
        ok = np.isfinite(P["pred2"]) & np.isfinite(P["sc2"]) & np.isfinite(P["sc3"])
        ev = np.where(ok)[0]
        if excl_covid:
            ev = np.array([t for t in ev if not (COVID[0] <= ym[t] <= COVID[1])])
        evm = event_months(src, sid)
        zz = z
        if matched:  # 誤報が年0.5回になるしきい値（系列ごと）
            zs = np.abs((P["y"][ev] - P["pred2"][ev]) / P["sc2"][ev])
            zz = float(np.quantile(zs, 1 - 0.5 / 12))
        for t in ev:
            r = combos(judge(P, t, x[t], zz))
            clean_rows.append({"src": src, "sid": sid, "ym": ym[t], "event": ym[t] in evm,
                               "covid": COVID[0] <= ym[t] <= COVID[1],
                               "z2": (P["y"][t] - P["pred2"][t]) / P["sc2"][t], **r})
        # 汚れを入れる
        others = [s for s in by_src[src] if s != sid]
        for e in ERRS:
            for k in range(REPS[src]):
                t = int(rng.choice(ev))
                v = x[t]
                if e == "E1": v = v * 10
                elif e == "E2": v = v / 10
                elif e == "E3": v = v * 1000
                elif e == "E4": v = 0.0
                elif e == "E5": v = x[t - 1]
                elif e == "E6":
                    o = series[(src, others[int(rng.integers(len(others)))])]
                    v = float(o.loc[o.ym == ym[t], "x"].iloc[0])
                elif e == "E7": v = v * 1.15
                elif e == "E8": v = v * 0.85
                elif e == "E9": v = v * 1.05
                r = combos(judge(P, t, v, zz))
                det_rows.append({"src": src, "sid": sid, "err": e, "ym": ym[t], "same": v == x[t], **r})
    return pd.DataFrame(clean_rows), pd.DataFrame(det_rows)


METH = ["R_stale", "R", "R_nostale", "M1", "M2", "M3", "R∪M2", "R(停止なし)∪M2"]

if __name__ == "__main__":
    clean, det = run(0)
    clean.to_csv(OUT / "B_clean_flags.csv.gz", index=False, compression="gzip", float_format="%.4g")
    # A 見つかる割合
    A = det.groupby(["src", "err"])[METH].mean().reset_index()
    A["n"] = det.groupby(["src", "err"]).size().values
    A.to_csv(OUT / "A_detection.csv", index=False, float_format="%.4f")
    # 誤報（系列×年あたり）
    fa = clean.groupby("src")[METH].mean() * 12
    fa["series"] = clean.groupby("src")["sid"].nunique()
    fa["months"] = clean.groupby("src").size()
    fa.to_csv(OUT / "B_false_alarm_per_series_year.csv", float_format="%.4f")
    # H 判定
    big = A[A.err.isin(["E1", "E2", "E3", "E4"])].groupby("src")["R∪M2"].min()
    e7 = A[A.err == "E7"].set_index("src")["R∪M2"]
    stale_clean_s2 = clean.loc[clean.src == "S2", "R_stale"].mean()
    m2 = clean[clean.M2]
    h4_share = m2["event"].mean()
    h4_by = m2.groupby("src")["event"].agg(["mean", "size"])
    rate_cov = clean.loc[clean.covid, "M2"].mean()
    rate_oth = clean.loc[~clean.covid, "M2"].mean()
    res = {
        "settings": {"Z": Z, "M1": M1T, "WIN": WIN, "FLOOR": FLOOR, "REPS": REPS,
                     "eval_start": clean.groupby("src")["ym"].min().to_dict(),
                     "eval_end": clean.groupby("src")["ym"].max().to_dict(),
                     "series": clean.groupby("src")["sid"].nunique().to_dict()},
        "H1_big_min_rate_R_M2": big.to_dict(), "H1": bool((big >= 0.99).all()),
        "H2_E7": e7.to_dict(), "H2_gap_S2_minus_S3": float(e7["S2"] - e7["S3"]),
        "H2": bool(e7["S2"] - e7["S3"] >= 0.30),
        "H3_stale_share_clean_S2": float(stale_clean_s2), "H3": bool(stale_clean_s2 >= 0.10),
        "H4_event_share_M2_flags": float(h4_share), "H4_n_flags": int(len(m2)),
        "H4_by_src": {k: {"share": float(v["mean"]), "n": int(v["size"])} for k, v in h4_by.iterrows()},
        "H4": bool(h4_share >= 0.5),
        "H5_rate_covid": float(rate_cov), "H5_rate_other": float(rate_oth),
        "H5_ratio": float(rate_cov / rate_oth) if rate_oth > 0 else None,
        "H5": bool(rate_oth > 0 and rate_cov / rate_oth >= 3),
        "false_alarm_per_series_year": fa[METH].round(4).to_dict(orient="index"),
        "stale_clean_share_by_src": clean.groupby("src")["R_stale"].mean().round(4).to_dict(),
        "E5_same_value_share": det[det.err == "E5"].groupby("src")["same"].mean().round(4).to_dict(),
        # レビューで足した：E5 を、入れた月の値が前月と違った月だけで数えた見つかる割合
        "E5_rate_changed_months_R(停止なし)∪M2": det[(det.err == "E5") & ~det.same].groupby("src")["R(停止なし)∪M2"].mean().round(4).to_dict(),
        # レビューで足した：H4 の基準の割合（汚れのない月のうち、もともと出来事の月の割合）と、鳴った月の割合との比
        "H4_base_event_share_clean": clean.groupby("src")["event"].mean().round(4).to_dict(),
        "H4_base_event_share_clean_all": round(float(clean["event"].mean()), 4),
        "H4_lift_by_src": (h4_by["mean"] / clean.groupby("src")["event"].mean()).round(3).to_dict(),
        "H4_lift_all": round(float(h4_share / clean["event"].mean()), 3),
        "H4_noncovid_S2": {"flag_event_share": round(float(clean[(clean.src == "S2") & ~clean.covid & clean.M2]["event"].mean()), 4),
                            "base_event_share": round(float(clean[(clean.src == "S2") & ~clean.covid]["event"].mean()), 4)},
    }
    json.dump(res, open(OUT / "main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k.startswith("H")}, ensure_ascii=False, indent=1))
    print(A.pivot(index="err", columns="src", values="R∪M2").round(3))
    print(fa.round(3))
