"""data/raw の JSON を月次の表 data/monthly.csv にまとめる（オフライン）。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

def load(name):
    j = json.loads((RAW / name).read_text(encoding="utf-8"))
    out = {}
    for r in j["RESULTSET"]:
        d = r["VALUES"]["SURVEY_DATES"]; v = r["VALUES"]["VALUES"]
        s = pd.Series(v, index=[str(x) for x in d], dtype="float64")
        out[r["SERIES_CODE"]] = (r["NAME_OF_TIME_SERIES_J"], s)
    return out

def to_month(s):
    """週次（YYYYMMDD）は月内平均、月次（YYYYMM）はそのまま。"""
    idx = s.index
    if len(idx[0]) == 8:
        m = pd.Series(s.values, index=[i[:6] for i in idx]).dropna()
        return m.groupby(level=0, sort=True).mean()
    return s.dropna()

# 名前は系列名（見出しの文字）で確かめてから付ける
NAMES = {
    "ordinary": ("普通預金", ["DLDR120", "DLDR120N", "DLDR121N"]),
    "td3m": ("３百万円未満/３か月", ["DLDR43TL33M", "DLDR43TL33MN", "DLDR43TL63MN"]),
    "td1y": ("３百万円未満/１年", ["DLDR43TL31Y", "DLDR43TL31YN", "DLDR43TL61YN"]),
    "td5y": ("３百万円未満/５年", ["DLDR43TL35Y", "DLDR43TL35YN", "DLDR43TL65YN"]),
    "td1y_large": ("１千万円以上/１年", ["DLDR43TL11Y", "DLDR43TL11YN", "DLDR43TL41YN"]),
}
NEW = {"new_td_all": ("総合/(1)総合", "DLDRK_DLDR442DB"), "new_td_small": ("総合/(4)預入金額3百万円未満", "DLDRK_DLDR442DBKT"),
       "new_td_large": ("総合/(2)預入金額1千万円以上", "DLDRK_DLDR442DBFT"), "new_td_small_1y": ("1年以上2年未満/(4)預入金額3百万円未満", "DLDRK_DLDR442DBKT5")}

def main():
    allser = {}
    for f in sorted(RAW.glob("*.json")):
        allser.update(load(f.name))
    cols = {}
    call = allser
    assert "無担保コールレート" in call["STRACLUCON"][0] and "月平均" in call["STRACLUCON"][0]
    assert "月末" in call["STRECLUCON"][0]
    cols["call_avg"] = to_month(call["STRACLUCON"][1])
    cols["call_end"] = to_month(call["STRECLUCON"][1])
    for k, (label, codes) in NAMES.items():
        parts = []
        for c in codes:
            nm, s = allser[c]
            assert label in nm.replace("　", "").replace(" ", "").replace("預入金額", "") or label in nm, (k, c, nm)
            parts.append(to_month(s))
        joined = pd.concat(parts)
        assert not joined.index.duplicated().any(), k
        cols[k] = joined
    for k, (label, c) in NEW.items():
        nm, s = allser[c]
        assert nm == label, (k, nm)
        cols[k] = to_month(s)
    df = pd.DataFrame(cols).sort_index()
    df.index.name = "ym"
    df = df.loc["199310":]
    seg = pd.Series("2022/4以降（月次）", index=df.index)
    seg[df.index < "202204"] = "2007/10〜2022/3（週次）"
    seg[df.index < "200710"] = "〜2007/9（週次）"
    df["segment"] = seg
    df.round(5).to_csv(ROOT / "data" / "monthly.csv", encoding="utf-8")
    print(df.shape, df.index[0], df.index[-1])

if __name__ == "__main__":
    main()
