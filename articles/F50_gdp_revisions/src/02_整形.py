"""各公表回の CSV から GDP の前期比（実質・名目）と前年同期比（実質）を取り出し、
公表回 × 対象四半期 の表（ビンテージ表）にする"""
import json
import pandas as pd
from common import RAW, DATA, release_id, release_info, parse_series

d = json.load(open(RAW / "f50_qe_releases.json", encoding="utf-8"))
# 1回目の取得で CSV の名前の形が違って取れなかった3回分（qe133_2・qe201_2r・qe241_2 の訂正版）
extra = json.load(open(RAW / "f50_qe_extra.json", encoding="utf-8"))
got = {e["menu"] for e in extra}
d = [r for r in d if r["menu"] not in got] + extra
info, tabs = [], {"jk": {}, "mk": {}, "jg": {}}
for r in d:
    rid = release_id(r["menu"])
    if rid is None:
        continue
    inf = release_info(rid)
    info.append(inf)
    for k in tabs:
        if r.get(k):
            try:
                tabs[k][rid] = parse_series(r[k])
            except Exception as e:
                print("skip", rid, k, e)
info = pd.DataFrame(info)
# 訂正版（r）がある回は、訂正版だけを使う
fixed = {x[:-1] for x in info.rid if x.endswith("r")}
info = info[~info.rid.isin(fixed)].copy()
for k in tabs:
    for x in fixed:
        tabs[k].pop(x, None)
# 公表の順：対象四半期 → 1次 → 2次 → 再公表
info["order"] = info["ref"].astype(str) + info["stage"].astype(str) + info["reissue"].astype(int).astype(str)
info = info.sort_values("order").reset_index(drop=True)
info["ref"] = info["ref"].astype(str)
info.to_csv(DATA / "releases.csv", index=False)
for k, dd in tabs.items():
    v = pd.DataFrame(dd).T
    v.columns = v.columns.astype(str)
    v = v.reindex([x for x in info.rid if x in v.index])
    v.to_csv(DATA / f"vintages_{k}.csv")
    print(k, v.shape, "対象四半期", v.columns.min(), "〜", v.columns.max())
