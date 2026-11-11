"""F293 05 頑健性と問い直し。

頑健性（計画の5つ）：しきい値、MAD の窓、誤報を年0.5回にそろえたしきい値、コロナの期間を外す、乱数の種。
問い直し（結果を見た後に足した）：出来事のカレンダーで説明できない CPI の鳴りは、何が鳴らしているのか。
"""
import importlib.util, json, pathlib
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("a", BASE / "src" / "zz_f293_03_分析.py")
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)
OUT = BASE / "results"


def summarize(clean, det, label):
    rows = []
    for src in ["S1", "S2", "S3"]:
        c = clean[clean.src == src]; d = det[det.src == src]
        rate = lambda e, m="R(停止なし)∪M2": d.loc[d.err == e, m].mean()
        rows.append({"条件": label, "src": src,
                     "誤報M2_系列年": c["M2"].mean() * 12,
                     "誤報M1_系列年": c["M1"].mean() * 12,
                     "鳴った月の出来事の割合": c.loc[c.M2, "event"].mean() if c.M2.any() else np.nan,
                     "E1-E4最小": min(rate(e) for e in ["E1", "E2", "E3", "E4"]),
                     "E6": rate("E6"), "E7": rate("E7"), "E8": rate("E8"), "E9": rate("E9"),
                     "E7_M1": rate("E7", "M1")})
    return rows


rows = []
c0 = pd.read_csv(OUT / "B_clean_flags.csv.gz")
cases = [("基本（z4・M1 0.2・窓36・種0）", dict()),
         ("z3", dict(z=3.0)), ("z5", dict(z=5.0)),
         ("窓24", dict(win=24)), ("窓60", dict(win=60)),
         ("誤報を年0.5回にそろえる", dict(matched=True)),
         ("コロナの期間を外す", dict(excl_covid=True)),
         ("種1", dict(seed=1)), ("種2", dict(seed=2))]
store = {}
for lab, kw in cases:
    cl, de = a.run(**kw)
    store[lab] = (cl, de)
    rows += summarize(cl, de, lab)
# M1 のしきい値
for t in (0.1, 0.3):
    a.M1T = t
    cl, de = a.run()
    for r in summarize(cl, de, f"M1 {t}"):
        rows.append({k: r[k] for k in ["条件", "src", "誤報M1_系列年", "E7_M1"]})
a.M1T = 0.2
R = pd.DataFrame(rows)
R.to_csv(OUT / "C_robustness.csv", index=False, float_format="%.4f")

# H の判定が条件で変わるか
hj = []
for lab, (cl, de) in store.items():
    A = de.groupby(["src", "err"])["R∪M2"].mean()
    e7 = de[de.err == "E7"].groupby("src")["R∪M2"].mean()
    m2 = cl[cl.M2]
    cov = cl.loc[cl.covid, "M2"].mean(); oth = cl.loc[~cl.covid, "M2"].mean()
    hj.append({"条件": lab,
               "H1": bool(A[A.index.get_level_values(1).isin(["E1", "E2", "E3", "E4"])].min() >= 0.99),
               "H2差": round(float(e7["S2"] - e7["S3"]), 3),
               "H3停止の割合S2": round(float(cl.loc[cl.src == "S2", "R_stale"].mean()), 3),
               "H4出来事の割合": round(float(m2["event"].mean()), 3),
               "H5比": round(float(cov / oth), 2) if np.isfinite(cov) and oth > 0 else None})
pd.DataFrame(hj).to_csv(OUT / "C_hypotheses_by_condition.csv", index=False)

# レビューで足した：誤報をそろえる条件の中身（系列ごとのしきい値と、実際の鳴る回数、S1 の汚れごとの見つかる割合）
# 注意：このしきい値は評価する期間全体（その月より後の月とコロナの月を含む）の分位点から決めているので、先読みがある
df_all = pd.read_csv(BASE / "data" / "series_long.csv")
thr = []
for (src, sid), g in df_all.groupby(["src", "sid"]):
    g = g.sort_values("ym"); x = g["x"].to_numpy(float)
    P = a.parts(x); ok = np.isfinite(P["pred2"]) & np.isfinite(P["sc2"]) & np.isfinite(P["sc3"])
    zs = np.abs((P["y"][ok] - P["pred2"][ok]) / P["sc2"][ok])
    thr.append({"src": src, "sid": sid, "しきい値z": float(np.quantile(zs, 1 - 0.5 / 12))})
thr = pd.DataFrame(thr)
clm, dem = store["誤報を年0.5回にそろえる"]
thr = thr.merge((clm.groupby(["src", "sid"])["M2"].mean() * 12).rename("鳴る回数_年").reset_index(), on=["src", "sid"])
thr[thr.src != "S2"].to_csv(OUT / "C_matched_thresholds_S1S3.csv", index=False, float_format="%.4f")
md = dem.groupby(["src", "err"])[["R∪M2", "R(停止なし)∪M2", "M2"]].mean().reset_index()
md.to_csv(OUT / "C_matched_detection.csv", index=False, float_format="%.4f")
matched_info = {"しきい値z_中央値": thr.groupby("src")["しきい値z"].median().round(3).to_dict(),
                "実際の鳴る回数_年": (clm.groupby("src")["M2"].mean() * 12).round(3).to_dict()}

# ---------- 問い直し ----------
c = c0
s2 = c[c.src == "S2"].copy()
s2["mm"] = s2.ym % 100
nf = s2[s2.M2 & ~s2.event]
share_apr_oct = float(nf.mm.isin([4, 10]).mean())
# 品目ごとの「前月と同じ値」の割合で5つに分ける
item = s2.groupby("sid").agg(stale=("R_stale", "mean"), m2=("M2", "mean"),
                             m2_ne=("M2", lambda v: v[~s2.loc[v.index, "event"]].mean()))
item["q"] = pd.qcut(item.stale.rank(method="first"), 5, labels=["1 よく動く", "2", "3", "4", "5 ほとんど動かない"])
qtab = item.groupby("q", observed=True).agg(品目=("stale", "size"), 前月と同じ値の割合=("stale", "mean"),
                                           M2誤報_年=("m2", lambda v: v.mean() * 12),
                                           出来事以外_年=("m2_ne", lambda v: v.mean() * 12))
qtab.to_csv(OUT / "D_reask_by_stale.csv", float_format="%.4f")
# 鳴った月の前月比の大きさ（出来事以外）
def chg(row):
    return row
y = pd.read_csv(BASE / "data" / "series_long.csv")
y = y[y.src == "S2"].sort_values(["sid", "ym"])
y["chg"] = y.groupby("sid")["x"].pct_change()
nf2 = nf.merge(y[["sid", "ym", "chg"]], on=["sid", "ym"], how="left")
# 1つの本当の段差が、何回の鳴りになるか（同じ系列で直前2か月か、10〜14か月前にも鳴っていたか）
fl = s2[s2.M2][["sid", "ym", "event"]].copy()
fl["n"] = fl["ym"] // 100 * 12 + fl["ym"] % 100
keyset = {(r.sid, r.n) for r in fl.itertuples()}
fl["続き"] = [any((r.sid, r.n - k) in keyset for k in (1, 2)) for r in fl.itertuples()]
fl["1年後の折り返し"] = [(not c) and any((r.sid, r.n - k) in keyset for k in range(10, 15)) for r, c in zip(fl.itertuples(), fl["続き"])]
fl["はじめの1回"] = ~fl["続き"] & ~fl["1年後の折り返し"]
echo = {k: float(fl.loc[~fl.event, k].mean()) for k in ["はじめの1回", "続き", "1年後の折り返し"]}
echo_all = {k: float(fl[k].mean()) for k in ["はじめの1回", "続き", "1年後の折り返し"]}
first_only_rate = float(fl.loc[fl["はじめの1回"]].shape[0] / s2.shape[0] * 12)
first_only_ne = float(fl.loc[fl["はじめの1回"] & ~fl.event].shape[0] / s2.shape[0] * 12)
# 直し方の1つ：揺れの下限を 1% にする／4月・10月だけは「動いた月の前月比」で見る
a.FLOOR = 0.01
cl1, de1 = a.run()
a.FLOOR = 0.002
fix = {"下限1%_誤報M2_S2": float(cl1.loc[cl1.src == "S2", "M2"].mean() * 12),
       "下限1%_E7_S2": float(de1[(de1.src == "S2") & (de1.err == "E7")]["R(停止なし)∪M2"].mean()),
       "下限1%_E9_S2": float(de1[(de1.src == "S2") & (de1.err == "E9")]["R(停止なし)∪M2"].mean()),
       "下限1%_出来事の割合_S2": float(cl1.loc[(cl1.src == "S2") & cl1.M2, "event"].mean())}
reask = {"S2出来事以外の鳴り": int(len(nf)), "うち4月・10月の割合": share_apr_oct,
         "4月・10月の期待値": 2 / 12,
         "出来事以外の鳴りの前月比_中央値の絶対値": float(nf2.chg.abs().median()),
         "出来事以外の鳴り_値上げの向きの割合": float((nf2.chg > 0).mean()),
         "出来事以外の鳴り_年別": nf.groupby(nf.ym // 100).size().to_dict(),
         "S2月あたりの誤報_年別": (s2.groupby(s2.ym // 100)["M2"].mean() * 12).round(3).to_dict(),
         "出来事以外の鳴りの内訳": echo, "全部の鳴りの内訳": echo_all,
         "はじめの1回だけ数えた誤報_年": first_only_rate, "はじめの1回だけ_出来事以外_年": first_only_ne,
         **fix}
# レビューで足した：出来事のカレンダーを計画の言葉どおりに当てた場合（携帯電話機を外し、酒の語を計画の例に限る）
rules0 = a.ITEM_RULES
a.ITEM_RULES = [(("通信料（携帯",), r[1]) if "携帯電話" in r[0] else
                ((("ビール", "発泡酒", "清酒", "ワイン", "チューハイ"), r[1]) if "酒" in r[0] else r) for r in rules0]
cs = c0.copy()
evs = {(s_, i_): a.event_months(s_, i_) for s_, i_ in cs[["src", "sid"]].drop_duplicates().itertuples(index=False)}
cs["event2"] = [ym in evs[(s_, i_)] for s_, i_, ym in cs[["src", "sid", "ym"]].itertuples(index=False)]
a.ITEM_RULES = rules0
strict = {"出来事の割合_鳴った月": cs.loc[cs.M2].groupby("src")["event2"].mean().round(4).to_dict(),
          "出来事の割合_鳴った月_全体": round(float(cs.loc[cs.M2, "event2"].mean()), 4),
          "出来事の割合_汚れのない月": cs.groupby("src")["event2"].mean().round(4).to_dict()}
reask["レビュー_誤報そろえ"] = matched_info
reask["レビュー_計画どおりのカレンダー"] = strict
json.dump(reask, open(OUT / "D_reask.json", "w"), ensure_ascii=False, indent=1, default=float)
print(R.round(3).to_string())
print(pd.DataFrame(hj).to_string())
print(qtab.round(3)); print(json.dumps(reask, ensure_ascii=False, indent=1, default=float))
