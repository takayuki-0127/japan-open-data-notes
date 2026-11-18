"""data/raw の Excel から、県×年度の「倉庫」（使途別の再掲）と「運輸業用建築物」（用途別）を抜き出す。
出力：data/pref_year.csv（code, pref, region, fy, kind, n_bldg, floor_m2, cost_man_yen）"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "chakko_yoto_pref_fy_000040451302.xls"
OUT = ROOT / "data" / "pref_year.csv"

PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
REGION = {}
for i, p in enumerate(PREFS, 1):
    REGION[p] = ("北海道" if i == 1 else "東北" if i <= 7 else "関東" if i <= 14 else "中部" if i <= 23 else
                 "近畿" if i <= 30 else "中国" if i <= 35 else "四国" if i <= 39 else "九州・沖縄")

ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}


def fy_of(sheet):
    s = unicodedata.normalize("NFKC", sheet).replace(" ", "")
    m = re.match(r"(昭和|平成|令和)(元|\d+)年度", s)
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return ERA[m.group(1)] + n


def norm(x):
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(x)))


def main():
    x = pd.ExcelFile(RAW)
    rows = []
    for sh in x.sheet_names:
        fy = fy_of(sh)
        d = pd.read_excel(x, sheet_name=sh, header=None)
        # 列：0=名前、1=総計のむね、2=総計の床面積、3=総計の工事費予定額
        pref = None
        for _, r in d.iterrows():
            lab = norm(r[0]) if pd.notna(r[0]) else ""
            if not lab:
                continue
            cand = lab if lab in PREFS else re.sub(r"(都|府|県)$", "", lab)
            if cand in PREFS:
                pref = cand
                continue
            if "全国計" in lab:
                pref = "全国"
                continue
            if pref is None:
                continue
            kind = None
            if re.sub(r"^[0-9]", "", lab) == "倉庫":
                kind = "倉庫"
            elif lab == "運輸業用建築物":
                kind = "運輸業用建築物"
            if kind:
                v = [pd.to_numeric(r[c], errors="coerce") for c in (1, 2, 3)]
                rows.append({"pref": pref, "fy": fy, "sheet": norm(sh), "kind": kind,
                             "n_bldg": v[0], "floor_m2": v[1], "cost_man_yen": v[2]})
    df = pd.DataFrame(rows)
    # 令和6年度の2シートなど、同じ年度の値を足す
    df = df.groupby(["pref", "fy", "kind"], as_index=False, sort=True)[["n_bldg", "floor_m2", "cost_man_yen"]].sum(min_count=1)
    nsheet = pd.DataFrame(rows).groupby(["fy"])["sheet"].nunique()
    code = {p: f"{i:02d}" for i, p in enumerate(PREFS, 1)}
    code["全国"] = "00"
    df["code"] = df["pref"].map(code)
    df["region"] = df["pref"].map(REGION).fillna("全国")
    df = df[["code", "pref", "region", "fy", "kind", "n_bldg", "floor_m2", "cost_man_yen"]].sort_values(["kind", "code", "fy"])
    # 確かめ：どの年度も47都道府県がそろう（全国計の行には内訳がないので、全国は県の合計で作る）
    df = df[df.code != "00"]
    for k in df["kind"].unique():
        cnt = df[df.kind == k].groupby("fy").size()
        assert (cnt == 47).all(), (k, cnt[cnt != 47])
    df.to_csv(OUT, index=False, encoding="utf-8")
    print(df.groupby("kind")["fy"].agg(["min", "max", "nunique"]))
    print("sheets per fy>1:", nsheet[nsheet > 1].to_dict())


if __name__ == "__main__":
    main()
