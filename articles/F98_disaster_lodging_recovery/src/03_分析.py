"""03 分析：事例ごとのイベントスタディ（対照県との差・プラセボの帯）と、宿泊者数が戻るまでの月数"""
import json
import numpy as np
import pandas as pd
from common import *

Y = {s: load(s) for s in ["japanese", "total"]}
P = pd.read_csv(DATA / "panel.csv", parse_dates=["date"]).pivot(index="date", columns="pref", values="japanese")


def run(ev, series="japanese", pre=PRE, h=H, how="mean", drop_adj=True, extra_drop=(), tr=None, draws=400, seas="ev"):
    y = Y[series]
    t0, lo, hi = window(ev, pre, h)
    tr = tr or ev["tr"]
    dn = donors(ev, y.columns, pre, h, drop_adj, extra_drop)
    seas = ev.get("seas") if seas == "ev" else seas
    e = effect(y, tr, dn, t0, lo, hi, how, seas)
    pl = placebo(y, len(tr), dn, t0, lo, hi, how, draws, seas=seas)
    band = pd.DataFrame({"lo": pl.quantile(0.05, axis=1), "hi": pl.quantile(0.95, axis=1)})
    return e, band, dn, t0


def rec_all(e, band):
    r = {f"thr{int(t*100)}": recovery(e, t) for t in [0.03, 0.05, 0.10]}
    r["band"] = recovery(e, band=band["lo"])
    return r


def lost(ev, e, t0, upto):
    """失われた延べ宿泊者数（目安）：実績 ×（1/exp(差) − 1）を、差がマイナスの月だけ k=0..upto まで足す"""
    s = 0.0
    for k in range(0, upto + 1):
        if k not in e.index or e[k] >= 0:
            continue
        d = t0 + pd.DateOffset(months=k)
        act = P.loc[d, ev["tr"]].sum()
        s += act * (np.exp(-e[k]) - 1)
    return s


out, rows, rec, main = {}, [], [], {}
for key, ev in EVENTS.items():
    pre, h = (12, 23) if key == "E4" else (PRE, H)
    e, band, dn, t0 = run(ev, pre=pre, h=h)
    main[key] = (e, band)
    for k in e.index:
        rows.append(dict(event=key, name=ev["name"], k=k, effect=e[k], lo=band.lo[k], hi=band.hi[k]))
    r = rec_all(e, band)
    post = e[e.index >= 0]
    rec.append(dict(event=key, name=ev["name"], start=ev["start"], tr="・".join(p[2:] for p in ev["tr"]), n_donors=len(dn),
                    pre=pre, h=int(post.index.max()), first=post.iloc[0], trough=post.min(), trough_k=int(post.idxmin()),
                    mean_0_5=post.loc[0:5].mean(), mean_6_11=post.loc[6:11].mean(), mean_12_=post.loc[12:].mean(),
                    pre_sd=e[e.index < 0].std(), lost=lost(ev, e, t0, int(post.index.max())), **r))
    # 県ごと
    for p in ev["tr"]:
        ep, bp, _, _ = run(ev, pre=pre, h=h, tr=[p])
        for k in ep.index:
            rows.append(dict(event=key, name=ev["name"] + "／" + p[2:], k=k, effect=ep[k], lo=bp.lo[k], hi=bp.hi[k]))
        rp = rec_all(ep, bp)
        rec.append(dict(event=key, name=ev["name"] + "／" + p[2:], start=ev["start"], tr=p[2:], n_donors=len(dn), pre=pre,
                        h=int(ep.index.max()), first=ep[0], trough=ep[ep.index >= 0].min(), trough_k=int(ep[ep.index >= 0].idxmin()),
                        mean_0_5=ep.loc[0:5].mean(), mean_6_11=ep.loc[6:11].mean(), mean_12_=ep.loc[12:].mean(),
                        pre_sd=ep[ep.index < 0].std(), lost=lost(dict(tr=[p]), ep, t0, int(ep.index.max())), **rp))
eff = pd.DataFrame(rows); eff.to_csv(RES / "effects.csv", index=False)
rec = pd.DataFrame(rec); rec.to_csv(RES / "recovery.csv", index=False)

# 熊本地震だけ、コロナ前まで長く（k=0..44）
e1, b1, _, _ = run(EVENTS["E1"], h=44)
pd.DataFrame({"effect": e1, "lo": b1.lo, "hi": b1.hi}).to_csv(RES / "E1_long.csv", index_label="k")

# 3事例（コロナ前）を重ねる：k ごとの平均と、プラセボ（事例ごとに対照から同じ数の県を選ぶ）の平均の帯
st = pd.concat([main[k][0].loc[-PRE:H] for k in ["E1", "E2", "E3"]], axis=1)
rng = np.random.default_rng(SEED)
pls = []
for key in ["E1", "E2", "E3"]:
    ev = EVENTS[key]; y = Y["japanese"]; t0, lo, hi = window(ev)
    dn = donors(ev, y.columns)
    pls.append(placebo(y, len(ev["tr"]), dn, t0, lo, hi, draws=400, seed=SEED + int(key[1])).loc[-PRE:H])
pm = sum(p.iloc[:, rng.integers(0, p.shape[1], 400)].set_axis(range(400), axis=1).reindex(st.index) for p in pls) / 3
stk = pd.DataFrame({"effect": st.mean(axis=1), "n": st.notna().sum(axis=1), "lo": pm.quantile(0.05, axis=1), "hi": pm.quantile(0.95, axis=1)})
stk.to_csv(RES / "stacked.csv", index_label="k")

# 頑健性：回復までの月数（5%基準）と、事後0〜5か月の平均の差
rob = []
def add(label, key, **kw):
    ev = kw.pop("ev", EVENTS.get(key) or EXTRA.get(key))
    if key == "E4":
        kw.setdefault("pre", 12); kw.setdefault("h", 23)
    if kw.get("how") == "scm":
        kw["draws"] = 150
    e, band, dn, _ = run(ev, **kw)
    rob.append(dict(setting=label, event=key, name=ev["name"], n_donors=len(dn), mean_0_5=e.loc[0:5].mean(), trough=e[e.index >= 0].min(),
                    rec5=recovery(e, 0.05), rec3=recovery(e, 0.03), rec10=recovery(e, 0.10), recband=recovery(e, band=band["lo"]),
                    h=int(e.index.max())))
for key in ["E1", "E2", "E3", "E4"]:
    add("基本（日本人・対照の平均・事前24か月）", key)
    add("対照：合成コントロール", key, how="scm")
    add("対照：隣の県も対照に入れる", key, drop_adj=False)
    add("対照：東京・大阪・京都を除く", key, extra_drop=("13東京都", "27大阪府", "26京都府"))
    add("対照：東北3県を除く", key, extra_drop=("03岩手県", "04宮城県", "07福島県"))
    add("系列：総数（外国人を含む）", key, series="total")
    if key == "E4":
        add("季節：2023年の同じ月を基準（事前の差は0になる）", key, seas=None)
    else:
        add("事前12か月", key, pre=12)
        add("事前36か月", key, pre=36)
add("基本（日本人・対照の平均・事前24か月）", "E5")
add("系列：総数（外国人を含む）", "E5", series="total")
rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(rec.round(3).to_string())
print(stk.loc[-3:H].round(3).to_string())
print(pd.Series(e1).loc[0:44:3].round(3).to_string())
print(rob.round(3).to_string())
