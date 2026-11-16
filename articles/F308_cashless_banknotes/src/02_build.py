"""日本銀行の JSON と家計消費状況調査の Excel から、分析用の表を作る（オフライン）。
出力：data/boj_monthly.csv（年月×系列）、data/emoney_annual.csv（年×指標、二人以上の世帯・全国）"""
import glob, json, pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
rows = []
for f in sorted(glob.glob(str(RAW / "boj_*.json"))):
    j = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    for r in j["RESULTSET"]:
        for dte, val in zip(r["VALUES"]["SURVEY_DATES"], r["VALUES"]["VALUES"]):
            if val is None:
                continue
            s = str(dte)
            rows.append(dict(series=r["SERIES_CODE"], year=int(s[:4]), month=int(s[4:6]), value=float(val)))
b = pd.DataFrame(rows).pivot_table(index=["year", "month"], columns="series", values="value").reset_index().sort_values(["year", "month"])
b.to_csv(DATA / "boj_monthly.csv", index=False)

LABELS = {"電子マネーを持っている世帯員がいる": "hold_share", "電子マネーを利用した世帯員がいる": "use_share",
          "電子マネーを利用した1世帯当たり平均利用金額": "use_amount"}
recs = []
for f in sorted(glob.glob(str(RAW / "kakei_shohi_emoney_*"))):
    y = int(re.search(r"_(\d{4})\.", f).group(1))
    x = pd.read_excel(f, sheet_name=None, header=None)
    v = x[[k for k in x if "二人" in k][0]]
    got = {}
    for i in range(v.shape[0]):
        cells = [str(c).strip().replace("１", "1").replace(" ", "").replace("\u3000", "") for c in v.iloc[i, :]]
        for j, c in enumerate(cells):
            key = next((k for k in LABELS if c == k or (c.startswith(k) and "いない" not in c and not c.startswith("〔"))), None)
            if key and LABELS[key] not in got:
                c = key
                nums = [pd.to_numeric(z, errors="coerce") for z in cells[j + 1:]]
                nums = [z for z in nums if pd.notna(z)]
                got[LABELS[c]] = float(nums[0])
    assert set(got) == set(LABELS.values()), (y, got)
    recs.append(dict(year=y, **got))
e = pd.DataFrame(recs).sort_values("year")
e.to_csv(DATA / "emoney_annual.csv", index=False)
print(b.tail(2)); print(e.to_string())
