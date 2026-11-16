"""32地点の「年ごとの値（風）」の HTML から、年平均風速・10m/s以上の日数と、表の切れ目（赤い線）を読む。"""
import os, re
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
OUT = os.path.join(HERE, "..", "data")
Y0, Y1 = 1961, 2025

st = pd.read_csv(os.path.join(RAW, "stations.csv"))


def cell_value(txt):
    """値と、使えるか（「]」と空・記号は使わない。「)」は準正常値として使う）。"""
    t = txt.replace("　", " ").strip()
    if t.endswith("]") or t == "":
        return np.nan
    t = t.rstrip(")").strip()
    return float(t) if re.fullmatch(r"-?\d+(\.\d+)?", t) else np.nan


rows = []
for _, s in st.iterrows():
    html = open(os.path.join(RAW, f"jma_a3_{s.block_no}.html"), encoding="utf-8").read()
    for tr in re.findall(r'<tr class="mtx2"[^>]*>(.*?)</tr>', html, flags=re.S):
        tds = re.findall(r"<td([^>]*)>(.*?)</td>", tr, flags=re.S)
        if len(tds) < 10:
            continue
        ytxt = re.sub(r"<[^>]+>", "", tds[0][1]).strip()
        if not re.fullmatch(r"\d{4}", ytxt):
            continue
        y = int(ytxt)
        cells = [(attr, re.sub(r"<[^>]+>", "", v)) for attr, v in tds[1:]]
        mean_attr, mean_txt = cells[0]
        d10_attr, d10_txt = cells[-4]
        rows.append({"station": s.station, "block_no": s.block_no, "group": s.group, "year": y,
                     "wind_mean": cell_value(mean_txt), "break_mean": int("data_1t" in mean_attr),
                     "days_ge10": cell_value(d10_txt), "break_d10": int("data_1t" in d10_attr)})
d = pd.DataFrame(rows).sort_values(["block_no", "year"]).reset_index(drop=True)


# 赤い線（その年の前に切れ目）で区間番号をつける。表の全年で数え、あとで期間を切る。
d["seg_mean"] = d.groupby("block_no")["break_mean"].cumsum()
d["seg_d10"] = d.groupby("block_no")["break_d10"].cumsum()
d = d[(d.year >= Y0) & (d.year <= Y1)].reset_index(drop=True)
d.to_csv(os.path.join(OUT, "annual_wind.csv"), index=False, float_format="%.2f")
print(d.shape, d.station.nunique(), "stations")
