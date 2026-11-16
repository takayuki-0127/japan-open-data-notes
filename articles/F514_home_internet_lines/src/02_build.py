"""通信利用動向調査の CSV（2019〜2025年）を、年×属性×回線の長い表（data/lines.csv）にする。
FTTH などの契約数（四半期）は data/bb_contracts.csv にする。"""
import csv, io, pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
COLMAP = {"ブロードバンド回線": "bb", "固定系ブロードバンド回線": "fixed", "ＤＳＬ回線": "dsl", "ケーブルテレビ回線": "catv",
          "光回線（ＦＴＴＨ回線）": "ftth", "固定無線回線（ＦＷＡ）": "fwa", "携帯電話回線": "mobile", "ＬＴＥ・ＢＷＡ回線": "lte",
          "５Ｇ回線": "g5", "ホームルーター": "home_router", "インターネット回線を契約していない": "no_contract",
          "自宅でインターネット回線を契約していない": "no_contract", "無回答": "no_answer"}
GROUPS = ["世帯全体", "世帯主年齢", "世帯人員", "世帯類型", "世帯年収", "都市区分", "地方"]


def norm(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", s)) if s else s


def main():
    recs = []
    for f in sorted(RAW.glob("tsushin_*_lines.csv")):
        y = int(re.search(r"(\d{4})", f.name).group(1))
        rows = list(csv.reader(io.StringIO(f.read_bytes().decode("cp932"))))
        hdr = next(r for r in rows if len(r) > 3 and r[2] == "集計世帯数")
        idx = {COLMAP[h.replace("\n", "")]: j for j, h in enumerate(hdr) if h.replace("\n", "") in COLMAP}
        for r in rows:
            if not r or r[0] not in GROUPS:
                continue
            for k, j in idx.items():
                v = r[j].strip()
                val = None if v in ("-", "") else float(v)
                if v == "-":
                    val = 0.0
                recs.append((y, r[0], norm(r[1]), k, val, int(r[2]), int(r[3])))
    d = pd.DataFrame(recs, columns=["year", "group", "category", "line", "pct", "n_raw", "n_weighted"])
    d = d.sort_values(["year", "group", "category", "line"]).reset_index(drop=True)
    d.to_csv(ROOT / "data" / "lines.csv", index=False)

    b = pd.read_excel(RAW / "gt010103.xls", sheet_name=None, header=None)
    out = []
    for sheet in ["FTTH", "DSL", "CATV", "BWA"]:
        x = b[sheet]
        labels = [norm(str(v)) for v in x.iloc[3].tolist()]
        tot = x.iloc[4].tolist()
        for lab, v in zip(labels, tot):
            m = re.match(r"R(\d+)\.(\d+)月末", lab)
            if m and pd.notna(v):
                out.append((sheet, f"{2018 + int(m.group(1))}-{int(m.group(2)):02d}", float(v)))
    pd.DataFrame(out, columns=["service", "date", "contracts"]).to_csv(ROOT / "data" / "bb_contracts.csv", index=False)


if __name__ == "__main__":
    main()
