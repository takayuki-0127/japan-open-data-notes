"""F243 02 整形：家計調査の品目パネルに区分の変更の印をつけ、商業動態統計の全店・既存店の前年同月比をそろえる。"""
import numpy as np, pandas as pd, os
B = os.path.join(os.path.dirname(__file__), "..")
k = pd.read_csv(f"{B}/data/raw/kakei_items_panel_f113.csv").sort_values(["code", "year"])
k["dlq"] = k.groupby("code")["q"].transform(lambda s: np.log(s).diff())
k["dlp"] = k.groupby("code")["price"].transform(lambda s: np.log(s).diff())
# 区分の変更らしき年：数量が1年で3倍以上・3分の1以下に動き、価格が逆向きに大きく動いた年
k["break"] = ((k["dlq"].abs() > np.log(3)) | ((k["dlq"].abs() > np.log(1.8)) & (k["dlp"] * k["dlq"] < 0) & (k["dlp"].abs() > np.log(1.5)))).astype(int)
fr = pd.read_csv(f"{B}/data/raw/item_fresh_flag_f234.csv")  # 生鮮かどうか（F234 で付けた印）
k = k.merge(fr, on="code", how="left")
k.to_csv(f"{B}/data/kakei_items.csv", index=False)
m = pd.read_csv(f"{B}/data/raw/meti_dept_super_national.csv")
s = m[m["指標"] == "販売額"].pivot(index="ym", columns="業態", values="値")
e = m[m["指標"] == "既存店"].pivot(index="ym", columns="業態", values="値")
s.index = pd.PeriodIndex(s.index, freq="M"); e.index = pd.PeriodIndex(e.index, freq="M")
rows = []
for t in ["スーパー", "百貨店"]:
    yoy_all = (s[t] / s[t].shift(12) - 1) * 100
    yoy_ex = e[t] - 100
    df = pd.DataFrame({"業態": t, "全店": yoy_all, "既存店": yoy_ex}).dropna()
    df["差（店舗網）"] = df["全店"] - df["既存店"]
    rows.append(df)
r = pd.concat(rows).reset_index().rename(columns={"index": "ym"})
r["ym"] = r["ym"].astype(str)
r.to_csv(f"{B}/data/meti_yoy_all_vs_existing.csv", index=False)
print(k.shape, int(k["break"].sum()), r.shape, r.ym.min(), r.ym.max())
