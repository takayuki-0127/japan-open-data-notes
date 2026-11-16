"""問い直し（結果を見てから足した）：全体の旅館の割合は下がったのに、旅館が下がった国・地域は20のうち7だけだった。
訪日客の居住地の構成（全体の列の「居住地」の構成比）を重みにして、2019→2025年の全体の変化を
「国・地域ごとの旅館の割合の変化」と「訪日客の構成の変化」に分ける（シフトシェア）。居住地と国籍は同じ名前の区分を対応させる。"""
import gzip, io, json, pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
R = ROOT / "results"; RAW = ROOT / "data" / "raw"
n = lambda s: re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s))) if isinstance(s, str) else ""
W = pd.read_csv(R / "lodging_by_nation_year.csv")
NAT = sorted([c for c in W.nation.unique() if c not in ("全体",)])


def residence_weights(y):
    x = pd.ExcelFile(io.BytesIO(gzip.open(RAW / f"inbound_{y}.xls.gz").read()), engine="xlrd")
    v = pd.read_excel(x, header=None, sheet_name="表1-1")
    hr = next(i for i in range(12) if any(n(c) == "調査項目" for c in v.iloc[i]))
    j0 = next(j for j, c in enumerate(v.iloc[hr]) if n(c).startswith("全国籍"))
    out, on = {}, False
    for i in range(hr + 1, len(v)):
        labs = [n(c) for c in v.iloc[i, :j0] if n(c)]
        if any(l == "居住地" for l in labs):
            on = True
        if any(l == "滞在日数" for l in labs):
            break
        if on and labs and labs[-1] in NAT and labs[-1] not in out:
            out[labs[-1]] = float(v.iloc[i, j0 + 1])
    return pd.Series(out)


w19, w25 = residence_weights(2019), residence_weights(2025)
w19, w25 = w19 / w19.sum(), w25 / w25.sum()
ry = W.pivot(index="nation", columns="year", values="ryokan")
s19, s25 = ry.loc[w19.index, 2019], ry.loc[w25.index, 2025]
mix = float(((w25 - w19) * (s19 + s25) / 2).sum()); within = float(((s25 - s19) * (w19 + w25) / 2).sum())
t = pd.DataFrame({"weight_2019": w19 * 100, "weight_2025": w25 * 100, "ryokan_2019": s19, "ryokan_2025": s25})
t["within"] = (s25 - s19) * (w19 + w25) / 2; t["mix"] = (w25 - w19) * (s19 + s25) / 2
t.to_csv(R / "requestion_ryokan_shift_share.csv", float_format="%.4f")
out = {"weighted_2019": round(float((w19 * s19).sum()), 2), "weighted_2025": round(float((w25 * s25).sum()), 2),
       "change": round(mix + within, 2), "within": round(within, 2), "mix": round(mix, 2),
       "within_ea": round(float(t.loc[["韓国", "台湾", "香港", "中国"], "within"].sum()), 2),
       "within_china": round(float(t.loc["中国", "within"]), 2),
       "weight_china": {"2019": round(float(w19["中国"] * 100), 1), "2025": round(float(w25["中国"] * 100), 1)},
       "weight_ea": {"2019": round(float(w19[["韓国", "台湾", "香港", "中国"]].sum() * 100), 1), "2025": round(float(w25[["韓国", "台湾", "香港", "中国"]].sum() * 100), 1)}}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(out, ensure_ascii=False, indent=1)); print(t.round(2).to_string())
